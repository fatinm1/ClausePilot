"""Write edits into a .docx as real Word tracked changes.

Every edit is expressed as (paragraph, old text, new text). The difference is
computed word by word and written as <w:del>/<w:ins> runs that Word's
Accept/Reject understands. Unchanged words keep their original runs and
formatting; inserted words copy the formatting of the text next to them.
"""

from __future__ import annotations

import copy
import difflib
import logging
import re
from datetime import UTC, datetime

from docx.document import Document as DocumentObject
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

logger = logging.getLogger(__name__)

AUTHOR = "ClausePilot"
W_T, W_R, W_DEL, W_INS = qn("w:t"), qn("w:r"), qn("w:del"), qn("w:ins")
W_DELTEXT, W_RPR, W_PPR = qn("w:delText"), qn("w:rPr"), qn("w:pPr")
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


# --------------------------------------------------------------------------- helpers
class ChangeIds:
    """Numeric, unique w:id values, starting above any already in the file."""

    def __init__(self, doc: DocumentObject):
        top = 0
        for el in doc.element.body.iter():
            v = el.get(qn("w:id"))
            if v and v.isdigit():
                top = max(top, int(v))
        self.next = top + 1
        self.date = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    def take(self) -> str:
        v = str(self.next)
        self.next += 1
        return v


def body_paragraphs(doc: DocumentObject) -> list[Paragraph]:
    """All paragraphs in reading order. Tables are read column by column, so a
    two-column signature table reads as one block per party."""
    out: list[Paragraph] = []

    def walk(container_el, parent):
        for child in container_el.iterchildren():
            if child.tag == qn("w:p"):
                out.append(Paragraph(child, parent))
            elif child.tag == qn("w:tbl"):
                rows = list(child.iterchildren(qn("w:tr")))
                grid = [list(r.iterchildren(qn("w:tc"))) for r in rows]
                ncols = max((len(r) for r in grid), default=0)

                def cell_text(tc):
                    return "".join(t.text or "" for t in tc.iter(W_T)).strip()

                first_col = [cell_text(r[0]) for r in grid if r and cell_text(r[0])]
                label_table = (
                    ncols == 2
                    and len(first_col) >= 2
                    and sum(1 for t in first_col if t.endswith(":") and len(t) < 30)
                    >= len(first_col) - 1
                )
                if label_table:  # "Name:" | "______" pairs read across
                    for r in grid:
                        for c in r:
                            walk(c, parent)
                else:  # side-by-side blocks read down each column
                    for c in range(ncols):
                        for r in grid:
                            if c < len(r):
                                walk(r[c], parent)
            elif child.tag == qn("w:sdt"):
                content = child.find(qn("w:sdtContent"))
                if content is not None:
                    walk(content, parent)

    walk(doc.element.body, doc._body)
    return out


def _run_text(r) -> str:
    out = []
    for child in r:
        if child.tag == W_T:
            out.append(child.text or "")
        elif child.tag == qn("w:tab"):
            out.append("\t")
        elif child.tag in (qn("w:br"), qn("w:cr")):
            out.append("\n")
    return "".join(out)


def _visible_runs(p_el):
    """Runs whose text a reader sees: direct runs, runs in hyperlinks and in
    existing insertions. Runs inside existing deletions are skipped."""
    runs = []
    for el in p_el.iter(W_R):
        if any(a.tag == W_DEL for a in el.iterancestors()):
            continue
        parent = el.getparent()
        if parent is p_el or parent.tag in (qn("w:hyperlink"), W_INS, qn("w:smartTag")):
            runs.append(el)
    return runs


def paragraph_text(p: Paragraph) -> str:
    return "".join(_run_text(r) for r in _visible_runs(p._p))


def _segments(p_el):
    segs, pos = [], 0
    for r in _visible_runs(p_el):
        t = _run_text(r)
        segs.append((r, pos, pos + len(t)))
        pos += len(t)
    return segs


def _is_simple(r) -> bool:
    return (
        all(c.tag in (W_RPR, W_T) for c in r) and sum(1 for c in r if c.tag == W_T) <= 1
    )


def _set_text(r, text: str):
    t = r.find(W_T)
    if t is None:
        t = r.makeelement(W_T, {})
        r.append(t)
    t.text = text
    t.set(XML_SPACE, "preserve")


def _split_at(p_el, pos: int) -> bool:
    """Ensure a run boundary at character offset pos. Returns False if a
    complex run (tabs, images) would need splitting."""
    for r, a, b in _segments(p_el):
        if a < pos < b:
            if not _is_simple(r):
                return False
            text = _run_text(r)
            right = copy.deepcopy(r)
            _set_text(r, text[: pos - a])
            _set_text(right, text[pos - a :])
            r.addnext(right)
            return True
    return True


def _wrap(r, tag: str, ids: ChangeIds):
    w = r.makeelement(
        tag, {qn("w:id"): ids.take(), qn("w:author"): AUTHOR, qn("w:date"): ids.date}
    )
    r.addprevious(w)
    w.append(r)
    if tag == W_DEL:
        for t in r.findall(W_T):
            t.tag = W_DELTEXT
            t.set(XML_SPACE, "preserve")
    return w


def _delete_range(p_el, a: int, b: int, ids: ChangeIds) -> bool:
    if a >= b:
        return True
    if not (_split_at(p_el, a) and _split_at(p_el, b)):
        return False
    for r, s, e in _segments(p_el):
        if s >= a and e <= b and e > s:
            _wrap(r, W_DEL, ids)
    return True


def _insert_at(p_el, pos: int, text: str, ids: ChangeIds) -> bool:
    if not text:
        return True
    if not _split_at(p_el, pos):
        return False
    segs = _segments(p_el)
    before = [r for r, s, e in segs if e <= pos and e > s]
    after = [r for r, s, e in segs if s >= pos and e > s]
    model = before[-1] if before else (after[0] if after else None)
    new_r = p_el.makeelement(W_R, {})
    if model is not None and model.find(W_RPR) is not None:
        new_r.append(copy.deepcopy(model.find(W_RPR)))
    t = new_r.makeelement(W_T, {})
    t.text = text
    t.set(XML_SPACE, "preserve")
    new_r.append(t)
    ins = p_el.makeelement(
        W_INS, {qn("w:id"): ids.take(), qn("w:author"): AUTHOR, qn("w:date"): ids.date}
    )
    ins.append(new_r)
    if before:
        anchor = before[-1]
        # if the anchor run sits inside a wrapper (hyperlink/ins), insert after the wrapper
        while anchor.getparent() is not p_el:
            anchor = anchor.getparent()
        anchor.addnext(ins)
    elif after:
        anchor = after[0]
        while anchor.getparent() is not p_el:
            anchor = anchor.getparent()
        anchor.addprevious(ins)
    else:
        ppr = p_el.find(W_PPR)
        if ppr is not None:
            ppr.addnext(ins)
        else:
            p_el.insert(0, ins)
    return True


TOKEN = re.compile(r"\s+|[A-Za-z0-9’'\-]+|[^\sA-Za-z0-9]")


def _tokens(s: str) -> list[str]:
    return TOKEN.findall(s)


def _weighted_opcodes(a, b):
    """LCS where matching a long word counts more than matching a space or
    'and', so the diff keeps real words and changes connectors instead."""

    def w(t):
        return 0.1 if not t.strip() or len(t) == 1 else float(len(t))

    n, m = len(a), len(b)
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        row, nxt = dp[i], dp[i + 1]
        ai = a[i]
        for j in range(m - 1, -1, -1):
            best = nxt[j] if nxt[j] > row[j + 1] else row[j + 1]
            if ai == b[j]:
                cand = nxt[j + 1] + w(ai)
                if cand > best:
                    best = cand
            row[j] = best
    # walk forward, emitting opcodes
    codes, i, j = [], 0, 0
    ci, cj = 0, 0

    def flush(i_end, j_end):
        if i_end > ci or j_end > cj:
            tag = (
                "replace"
                if i_end > ci and j_end > cj
                else ("delete" if i_end > ci else "insert")
            )
            codes.append((tag, ci, i_end, cj, j_end))

    while i < n and j < m:
        if a[i] == b[j] and abs(dp[i][j] - (dp[i + 1][j + 1] + w(a[i]))) < 1e-9:
            flush(i, j)
            if codes and codes[-1][0] == "equal":
                t, i1, _, j1, _ = codes.pop()
                codes.append(("equal", i1, i + 1, j1, j + 1))
            else:
                codes.append(("equal", i, i + 1, j, j + 1))
            i, j = i + 1, j + 1
            ci, cj = i, j
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    i, j = n, m
    flush(i, j)
    return codes


def _opcodes(a, b, reverse=False):
    if len(a) * len(b) <= 300_000:
        return _weighted_opcodes(a, b)
    if not reverse:
        return difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    n, m = len(a), len(b)
    ops = difflib.SequenceMatcher(None, a[::-1], b[::-1], autojunk=False).get_opcodes()
    return [(t, n - i2, n - i1, m - j2, m - j1) for t, i1, i2, j1, j2 in reversed(ops)]


def word_ops(old: str, new: str):
    """Word-level diff as a lawyer would mark it: list of (start, end, replacement)
    on old's offsets. Prefers the alignment that deletes the fewest words, and
    merges edits separated only by a space or punctuation into one."""
    a, b = _tokens(old), _tokens(new)
    offs = [0]
    for tok in a:
        offs.append(offs[-1] + len(tok))

    best = None
    for rev in (False, True):
        codes = _opcodes(a, b, rev)
        deleted = sum(
            len(t)
            for tag, i1, i2, _, _ in codes
            if tag in ("delete", "replace")
            for t in a[i1:i2]
            if t.strip()
        )
        key = (deleted, sum(1 for c in codes if c[0] != "equal"))
        if best is None or key < best[0]:
            best = (key, codes)
    codes = best[1]

    # merge edits whose gap is only whitespace/punctuation (e.g. "five (5)" -> "two (2)")
    segs = [[i1, i2, j1, j2, tag != "equal"] for tag, i1, i2, j1, j2 in codes]
    k = 1
    while k < len(segs) - 1:
        prev, gap, nxt = segs[k - 1], segs[k], segs[k + 1]
        small = len("".join(a[gap[0] : gap[1]])) <= 3 and not re.search(
            r"[A-Za-z0-9]", "".join(a[gap[0] : gap[1]])
        )
        if prev[4] and nxt[4] and not gap[4] and small:
            segs[k - 1 : k + 2] = [[prev[0], nxt[1], prev[2], nxt[3], True]]
        else:
            k += 1
    # keep parentheses balanced inside a change: "five (5)" not "five (5"
    for k, s in enumerate(segs):
        if not s[4] or k + 1 >= len(segs) or segs[k + 1][4]:
            continue
        old_seg, nxt = "".join(a[s[0] : s[1]]), segs[k + 1]
        if (
            old_seg.count("(") > old_seg.count(")")
            and nxt[1] > nxt[0]
            and a[nxt[0]] == ")"
            and b[nxt[2]] == ")"
        ):
            s[1] += 1
            s[3] += 1
            nxt[0] += 1
            nxt[2] += 1
    return [
        (offs[i1], offs[i2], "".join(b[j1:j2]))
        for i1, i2, j1, j2, changed in segs
        if changed
    ]


# --------------------------------------------------------------------------- matching
QUOTES = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", " ": " "})


def _loose_pattern(s: str) -> re.Pattern:
    parts = []
    for tok in _tokens(s.translate(QUOTES)):
        if tok.isspace():
            parts.append(r"\s+")
        elif tok == '"':
            parts.append(r"[\"“”]")
        elif tok == "'":
            parts.append(r"['‘’]")
        else:
            parts.append(re.escape(tok).replace("'", "['‘’]"))
    return re.compile("".join(parts))


def find_span(text: str, needle: str) -> tuple[int, int] | None:
    if not needle:
        return None
    i = text.find(needle)
    if i >= 0:
        return i, i + len(needle)
    m = _loose_pattern(needle.strip()).search(text)
    return (m.start(), m.end()) if m else None


# --------------------------------------------------------------------------- public
def apply_edit(p: Paragraph, old: str, new: str, ids: ChangeIds) -> bool:
    """Turn old -> new inside paragraph p into tracked changes."""
    text = paragraph_text(p)
    span = find_span(text, old)
    if span is None:
        return False
    start, end = span
    actual_old = text[start:end]
    ops = word_ops(actual_old, new)
    if not ops:
        return True
    # apply right-to-left so earlier offsets stay valid
    for a, b, repl in sorted(ops, key=lambda o: o[0], reverse=True):
        ok = _insert_at(p._p, start + b, repl, ids) and _delete_range(
            p._p, start + a, start + b, ids
        )
        if not ok:
            logger.warning("Could not split a complex run; edit skipped")
            return False
    return True


def add_paragraph_after(p: Paragraph, text: str, ids: ChangeIds) -> Paragraph:
    """Insert a new tracked paragraph after p, copying p's paragraph style."""
    new_p = p._p.makeelement(qn("w:p"), {})
    ppr = p._p.find(W_PPR)
    new_ppr = copy.deepcopy(ppr) if ppr is not None else new_p.makeelement(W_PPR, {})
    rpr = new_ppr.find(W_RPR)
    if rpr is None:
        rpr = new_ppr.makeelement(W_RPR, {})
        new_ppr.append(rpr)
    rpr.append(
        rpr.makeelement(
            W_INS,
            {qn("w:id"): ids.take(), qn("w:author"): AUTHOR, qn("w:date"): ids.date},
        )
    )
    new_p.append(new_ppr)
    p._p.addnext(new_p)
    para = Paragraph(new_p, p._parent)
    _insert_at(new_p, 0, text, ids)
    return para


def enable_track_revisions(doc: DocumentObject):
    """Turn on Track Changes so the reviewer's own edits are tracked too."""
    try:
        s = doc.settings.element
        if s.find(qn("w:trackRevisions")) is None:
            s.append(s.makeelement(qn("w:trackRevisions"), {}))
    except Exception as e:  # settings part missing in some generated files
        logger.warning(f"Could not enable trackRevisions: {e}")


def apply_changes(
    doc: DocumentObject, changes: list[dict], ids: ChangeIds | None = None
):
    """Apply planner-style changes (whole-paragraph or substring current_text).
    Returns (applied, failed) lists."""
    ids = ids or ChangeIds(doc)
    paras = body_paragraphs(doc)
    applied, failed = [], []

    def norm(s):
        return re.sub(r"\s+", " ", (s or "").translate(QUOTES)).strip()

    for ch in changes:
        cur, new = ch.get("current_text") or "", ch.get("new_text")
        if new is None or not cur:
            failed.append(ch)
            continue
        target = None
        i = ch.get("paragraph_index")
        if (
            isinstance(i, int)
            and 0 <= i < len(paras)
            and find_span(paragraph_text(paras[i]), cur)
        ):
            target = paras[i]
        if target is None:
            texts = [(p, paragraph_text(p)) for p in paras]
            target = next((p for p, t in texts if norm(t) == norm(cur)), None) or next(
                (p for p, t in texts if find_span(t, cur)), None
            )
        if target is not None and apply_edit(target, cur, new, ids):
            applied.append(ch)
        else:
            failed.append(ch)
    return applied, failed
