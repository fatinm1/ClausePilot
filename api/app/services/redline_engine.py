"""Plan NDA redlines: code for the mechanical rules, focused LLM calls for judgment.

plan_changes() takes the document as a list of paragraph strings and returns a
list of changes in the format the rest of the app already uses:

    {"type": "TEXT_REPLACE", "current_text": <whole paragraph>,
     "new_text": <whole paragraph after the edit>, "reason": ..., "rule": ...,
     "section": ..., "paragraph_index": i}

current_text is always a whole paragraph, so changes can be reviewed, applied
in any subset, and matched back to the .docx reliably. tracked_docx turns each
one into a minimal word-level tracked change.

How each rule kind is handled:
  term            code finds duration phrases in term/survival clauses and caps them
  representatives LLM proposes the minimal addition; code validates; code fallback
  retention       code appends the carve-out after the return/destroy clause
  signature       code fills blank fields in the recipient's signature block
  anything else   one LLM call per rule with only the relevant paragraphs, JSON
                  output, exact-match validation and one corrective retry
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

LLM = Callable[[list[dict[str, str]]], str]  # messages -> response text

NUM_WORDS = {
    w: i
    for i, w in enumerate(
        "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
        "fifteen sixteen seventeen eighteen nineteen twenty".split()
    )
}
NUM_WORDS.update(
    {
        "twenty-four": 24,
        "thirty": 30,
        "thirty-six": 36,
        "forty-eight": 48,
        "sixty": 60,
        "seventy-two": 72,
    }
)
ORDINALS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
}
ORDINAL_OF = {v: k for k, v in ORDINALS.items()}
_WORDS = "|".join(sorted(NUM_WORDS, key=len, reverse=True))
DURATION = re.compile(
    r"\b(?:(?P<word>[A-Za-z]+(?:-[A-Za-z]+)?)\s*\((?P<num1>\d+)\)|(?P<num2>\d+)|(?P<word2>"
    + _WORDS
    + r"))"
    r"(?P<sep>\s*-\s*|\s*)(?P<unit>years?|months?)\b",
    re.I,
)
ANNIVERSARY = re.compile(
    r"\b(?P<ord>"
    + "|".join(ORDINALS)
    + r")\s*(?:\((?P<n1>\d+)(?:st|nd|rd|th)\)\s*)?anniversary"
    r"|\b(?P<n2>\d+)(?:st|nd|rd|th)\s+anniversary",
    re.I,
)
# A duration counts as the agreement's or the confidentiality obligations' term only if
# its own clause says so and says nothing that marks it as some other kind of period.
TERM_POSITIVE = re.compile(
    r"surviv|remain in (?:full force and )?effect|in effect|terminat|expir|continu|\blast\b|confidentiality period|"
    r"obligations?|confidential for|keep[^.;]{0,60}confidential|\bterm\b|anniversary|ending on",
    re.I,
)
TERM_NEGATIVE = re.compile(
    r"\bbefore\b|prior to|\brecords?\b|maintain|preserve|audit|solicit|standstill|\bhire|non-?compete|"
    r"acquire|securities|notice|\bwithin\b|litigation|legal hold|\bexceed|renew|warrant|insurance|"
    r"not contact|disclosed during",
    re.I,
)
PERPETUAL_ADVERB = re.compile(r"\b(?:in perpetuity|perpetually|indefinitely)\b", re.I)
PERPETUAL = re.compile(r"in perpetuity|perpetual(?:ly)?|indefinite(?:ly)?", re.I)
REPS_DEF = re.compile(r"[\"“]Representatives[\"”]")
RETURN_HINTS = re.compile(r"\breturn\b|\bdestroy|\bdestruction", re.I)
RETAIN_EXISTS = re.compile(
    r"\b(?:retain|keep|maintain)(?:ed|s|ing)?\b[^.]{0,120}"
    r"(?:retention|backup|back-up|archiv|law|regulat|polic|cop(?:y|ies))"
    r"|retention polic|archiv\w*[^.]{0,60}(?:back-?up|cop(?:y|ies)|purpose)",
    re.I,
)
DEFAULT_CARVE_OUT = (
    "Notwithstanding the foregoing, Recipient may retain an electronic copy of Confidential "
    "Information if required under Recipient's document retention policy, provided that such "
    "retained materials remain subject to the confidentiality obligations set forth herein."
)
NO_LIABILITY = re.compile(
    r"(?:shall|will)\s+(?:not\s+)?have\s+(?:any|no)\s+liability|shall\s+not\s+be\s+liable"
    r"|without\s+liability|no\s+liability\s+(?:whatsoever|of any kind)",
    re.I,
)
REP_CATEGORIES = [
    ("investors", r"investor"),
    ("agents", r"\bagents?\b"),
    ("advisors", r"advis[oe]r"),
    ("potential financing sources", r"financing"),
]
FIELD = re.compile(
    r"^\s*(?P<label>name of company[^:]{0,40}|for and on behalf of|on behalf of|company|for|recipient|receiving party|by|name|"
    r"printed name|print name|signer|title|position|its|signature|signed|date|counterparty|discloser|disclosing party)"
    r"\s*:\s*(?P<value>.*?)\s*$",
    re.I,
)
BLANK = re.compile(r"^[\s_.\-–—]*$|^\[[^\]]*\]$|^\(?name to be provided\)?$", re.I)
BLANK_LINE = re.compile(r"\s*[_.\-–—]{3,}\s*")
PARTY_LABELS = (
    "recipient",
    "receiving party",
    "counterparty",
    "discloser",
    "disclosing party",
)
COMPANY_LABELS = (
    "company",
    "for",
    "recipient",
    "receiving party",
    "counterparty",
    "for and on behalf of",
    "on behalf of",
    "entity",
    "name of entity",
    "entity name",
    "company name",
    "organization",
    "organisation",
    "firm",
    "party",
)
GENERIC_FIELD = re.compile(
    r"^\s*(?P<label>[A-Za-z][A-Za-z .'’/]{0,30}?)\s*:\s*(?P<value>.*?)\s*$"
)
RECIPIENT_WORDS = re.compile(
    r"recipient|receiving|undersigned|counterparty|accepted and agreed|agreed and accepted|acknowledged",
    re.I,
)
PLACEHOLDER_PARTY = re.compile(
    r"\[(?:RECIPIENT|COUNTERPARTY|RECEIVING PARTY|INVESTOR|BUYER)(?:['’]S)?(?: NAME)?\]",
    re.I,
)
PLACEHOLDERS = {
    "[FIRM_NAME]": "name",
    "[FIRM_ADDRESS]": "address",
    "[FIRM_CITY]": "city",
    "[FIRM_STATE]": "state",
    "[FIRM_ZIP]": "zipCode",
    "[SIGNER_NAME]": "signerName",
    "[SIGNER_TITLE]": "signerTitle",
}


# --------------------------------------------------------------------------- utils
def months_of(m: re.Match) -> int | None:
    n = m.group("num1") or m.group("num2")
    if n is None and m.group("word2"):
        n = NUM_WORDS.get(m.group("word2").lower())
    if n is None:
        return None
    n = int(n)
    return n * 12 if m.group("unit").lower().startswith("year") else n


def sentence_around(text: str, start: int, end: int) -> str:
    """The clause containing text[start:end], split on sentence and semicolon breaks."""
    left = max(text.rfind(". ", 0, start), text.rfind(";", 0, start))
    rights = [i for i in (text.find(". ", end), text.find(";", end)) if i >= 0]
    return text[left + 1 : min(rights) if rights else len(text)]


def is_term_duration(text: str, start: int, end: int) -> bool:
    s = sentence_around(text, start, end)
    return (
        bool(TERM_POSITIVE.search(s))
        and not TERM_NEGATIVE.search(s)
        and not re.search(r"trade secret", s, re.I)
    )


NUMBER_WORDS = dict(
    enumerate(
        "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
        "fifteen sixteen seventeen eighteen nineteen twenty".split()
    )
)
NUMBER_WORDS.update({24: "twenty-four", 30: "thirty", 36: "thirty-six"})


def cap_from_instruction(text: str) -> tuple[int, str]:
    m = DURATION.search(text or "")
    if not m:
        return 24, "two (2) years"
    months = months_of(m) or 24
    phrase = m.group(0)
    # contracts write durations as "two (2) years"; turn a bare "2 years" into that form
    bare = re.fullmatch(r"(\d{1,2})[\s-]+(years?|months?)", phrase.strip(), re.I)
    if bare and int(bare.group(1)) in NUMBER_WORDS:
        n = int(bare.group(1))
        unit = bare.group(2).lower().rstrip("s") + ("s" if n != 1 else "")
        phrase = f"{NUMBER_WORDS[n]} ({n}) {unit}"
    return months, phrase


def classify(rule: dict) -> str:
    text = " ".join(
        str(rule.get(k, "")) for k in ("name", "category", "instruction")
    ).lower()
    if re.search(r"signature|signer|sign(?:ing)? block|firm details", text):
        return "signature"
    if "representative" in text or re.search(r"investors?\b|financing sources?", text):
        return "representatives"
    if re.search(r"\bretain\b|retention|archiv", text):
        return "retention"
    if re.search(
        r"\bterm\b|duration|surviv|confidentiality period|perpetu", text
    ) and re.search(r"year|month|perpetu", text):
        return "term"
    if re.search(r"liabilit|damages", text):
        return "liability"
    return "generic"


def _json_from(text: str) -> Any:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=-1)
    if start < 0:
        raise ValueError("no JSON in response")
    return json.loads(text[start:])


def _keywords(text: str) -> set[str]:
    stop = set(
        "the a an and or of to in for on with by any all its is are be shall may that this "
        "such as if from at not no each other party parties agreement recipient discloser "
        "information confidential include includes including add replace ensure".split()
    )
    return {w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in stop}


def _next_label(lab: str) -> str:
    romans = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"]
    if lab in romans and lab != "x":
        return romans[romans.index(lab) + 1]
    if len(lab) == 1 and lab.isalpha():
        return chr(ord(lab) + 1)
    return lab


# --------------------------------------------------------------------------- planner
class Planner:
    def __init__(self, paragraphs: list[str], firm: dict[str, str], llm: LLM | None):
        self.orig = list(paragraphs)
        self.cur = list(paragraphs)
        self.firm = {k: (v or "").strip() for k, v in (firm or {}).items()}
        self.llm = llm
        self.reasons: dict[int, list[tuple[str, str]]] = {}
        self.notes: list[str] = []

    # -- bookkeeping
    def edit(self, i: int, new_text: str, rule: str, reason: str):
        if new_text == self.cur[i]:
            return
        self.cur[i] = new_text
        self.reasons.setdefault(i, []).append((rule, reason))

    def changes(self) -> list[dict[str, Any]]:
        out = []
        for i in sorted(self.reasons):
            if self.cur[i] == self.orig[i]:
                continue
            rules = list(dict.fromkeys(r for r, _ in self.reasons[i]))
            out.append(
                {
                    "type": "TEXT_REPLACE",
                    "current_text": self.orig[i],
                    "new_text": self.cur[i],
                    "reason": " ".join(
                        dict.fromkeys(why for _, why in self.reasons[i])
                    ),
                    "rule": ", ".join(rules),
                    "section": rules[0],
                    "paragraph_index": i,
                }
            )
        return out

    # -- llm plumbing
    def ask(self, system: str, user: str) -> Any | None:
        if not self.llm:
            return None
        msgs = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        for attempt in range(2):
            try:
                return _json_from(self.llm(msgs))
            except Exception as e:
                logger.warning(
                    f"LLM returned unusable output ({e}); attempt {attempt + 1}"
                )
                msgs.append(
                    {"role": "user", "content": "Reply with valid JSON only, no prose."}
                )
        return None

    # -- rules
    def run(self, rules: list[dict]):
        kinds = [(classify(r), r) for r in rules]
        for kind, rule in kinds:
            try:
                getattr(self, f"rule_{kind}")(rule)
            except Exception as e:
                logger.exception(f"Rule '{rule.get('name')}' failed: {e}")
                self.notes.append(f"{rule.get('name')}: {e}")
        self.fill_placeholders()
        if self.firm and not any(k == "signature" for k, _ in kinds):
            self.rule_signature({"name": "Signature block"})

    def rule_term(self, rule):
        name = rule.get("name") or "Term"
        cap_months, cap_phrase = cap_from_instruction(rule.get("instruction", ""))
        cap_years = cap_months // 12 if cap_months % 12 == 0 else None
        unresolved = []
        for i, p in enumerate(self.cur):
            new = p
            # "survive indefinitely" / "in perpetuity" (trade secrets excepted)
            for m in reversed(list(PERPETUAL_ADVERB.finditer(new))):
                if is_term_duration(new, m.start(), m.end()):
                    new = new[: m.start()] + "for " + cap_phrase + new[m.end() :]
            # "ending on the third (3rd) anniversary"
            for m in reversed(list(ANNIVERSARY.finditer(new))):
                n = ORDINALS.get((m.group("ord") or "").lower()) or int(
                    m.group("n1") or m.group("n2") or 0
                )
                if (
                    n
                    and cap_years
                    and n > cap_years
                    and is_term_duration(new, m.start(), m.end())
                ):
                    word = ORDINAL_OF.get(cap_years, str(cap_years))
                    suffix = {1: "st", 2: "nd", 3: "rd"}.get(cap_years, "th")
                    new = (
                        new[: m.start()]
                        + f"{word} ({cap_years}{suffix}) anniversary"
                        + new[m.end() :]
                    )
            # "five (5) years", "36 months", "five years", "a five (5)-year period"
            cap_m = DURATION.search(cap_phrase)
            for m in reversed(list(DURATION.finditer(new))):
                mo = months_of(m)
                if mo and mo > cap_months and is_term_duration(new, m.start(), m.end()):
                    repl = cap_phrase
                    if "-" in m.group("sep") and cap_m:
                        # keep the adjective form: "a two (2)-year period"
                        repl = (
                            cap_phrase[: cap_m.start("sep")]
                            + "-"
                            + cap_m.group("unit").rstrip("s")
                        )
                    new = new[: m.start()] + repl + new[m.end() :]
            if new != p:
                self.edit(
                    i, new, name, f"Confidentiality period capped at {cap_phrase}."
                )
            elif PERPETUAL.search(p) and is_term_duration(p, 0, len(p)):
                unresolved.append(i)
        # Perpetual wording code could not rewrite safely ("perpetual obligations"): ask the model.
        if unresolved:
            self.llm_edit(rule, unresolved[:3])

    def rule_representatives(self, rule):
        name = rule.get("name") or "Representatives"
        idx = [i for i, p in enumerate(self.cur) if REPS_DEF.search(p)]
        if not idx:
            idx = [
                i
                for i, p in enumerate(self.cur)
                if re.search(r"\brepresentatives\b", p, re.I)
                and re.search(r"means|include|collectively", p, re.I)
            ]
        if not idx:
            self.notes.append(f"{name}: no definition of Representatives found")
            return
        i = idx[0]
        p = self.cur[i]
        # one definition per party ("(i) with respect to you ... (ii) with respect to
        # the Company"): which branch is ours depends on who is reviewing, so flag it
        if (
            len(
                re.findall(
                    r"\((?:i|ii|iii|a|b|c)\)\s*(?:with respect to|in the case of|as to)\b",
                    p,
                    re.I,
                )
            )
            >= 2
        ):
            self.notes.append(
                f"{name}: Representatives is defined separately for each party; "
                "review that definition by hand"
            )
            return
        missing = [
            label for label, pat in REP_CATEGORIES if not re.search(pat, p, re.I)
        ]
        if not missing:
            return
        reason = "Representatives widened to include " + ", ".join(missing) + "."
        use_model = os.getenv("REPS_WORDING", "code").lower() == "model"
        proposal = (
            None
            if not use_model
            else self.ask(
                "You edit NDA clauses. Make the smallest possible edit. Return JSON only.",
                "Clause:\n"
                + p
                + '\n\nAdd these categories to the definition of "Representatives" in this clause, '
                f"as categories of the party's own Representatives: {', '.join(missing)}.\n"
                "Rules: keep every existing word; only add words; keep the clause's own style "
                '(for example "its"); do not change anything outside the definition.\n'
                'Return {"new_text": "<the whole clause after your edit>"}',
            )
        )
        new = (proposal or {}).get("new_text", "") if isinstance(proposal, dict) else ""
        if (
            new
            and self._only_additions(p, new)
            and all(re.search(pat, new, re.I) for _, pat in REP_CATEGORIES)
        ):
            self.edit(i, new, name, reason)
            return
        self.edit(i, self._insert_reps(p, missing), name, reason)

    @staticmethod
    def _only_additions(old: str, new: str) -> bool:
        """A model edit to a definition may only add words. Rejects anything that
        removes letters or numbers (apart from a connecting 'and'/'or'), adds a new
        sentence, or moves new categories ahead of a scoping phrase such as
        'solely with respect to the Recipient'."""
        from .tracked_docx import word_ops

        for a, b, _ in word_ops(old, new):
            removed = old[a:b]
            if re.search(r"[A-Za-z0-9]", removed) and removed.strip(
                " ,;"
            ).lower() not in ("and", "or", ""):
                return False
        if new.count(". ") > old.count(". "):
            return False
        scope = re.search(
            r"solely (?:with respect to|in the case of)|in the case of|with respect to the recipient",
            old,
            re.I,
        )
        if scope:
            first_new = min(
                (
                    m.start()
                    for m in re.finditer(r"investor|financing|agent", new, re.I)
                ),
                default=None,
            )
            new_scope = re.search(re.escape(scope.group(0)), new, re.I)
            if (
                first_new is not None
                and new_scope
                and first_new < new_scope.start()
                and not re.search(r"investor|agent", old[: scope.start()], re.I)
            ):
                return False
        return len(new) > len(old)

    @staticmethod
    def _insert_reps(p: str, missing: list[str]) -> str:
        pron = (
            "your"
            if re.search(r"\byour\b", p, re.I)
            else (
                "their"
                if re.search(r"\btheir\b", p) and not re.search(r"\bits\b", p)
                else "its"
            )
        )
        listed = (
            ", ".join(missing[:-1]) + " and " + missing[-1]
            if len(missing) > 1
            else missing[0]
        )
        addition = f", and {pron} {listed}"
        m = REPS_DEF.search(p)
        if m:
            # "a, b and c (collectively, "Representatives")" / "a, b and c ("Representatives")"
            paren = p.rfind("(", max(0, m.start() - 20), m.start() + 1)
            if paren >= 0 and p[paren : m.start()].strip("( ").lower() in (
                "",
                "collectively,",
                "collectively",
                "together,",
                "its",
                "the",
            ):
                pos = paren
                while pos > 0 and p[pos - 1] == " ":
                    pos -= 1
                return p[:pos] + addition + p[pos:]
        start = m.end() if m else 0
        # enumerated list "(i) a; (ii) b; and (iii) c." -> "(i) a; (ii) b; (iii) c; and (iv) new."
        roman = list(re.finditer(r"\((?P<n>[ivx]+|[a-h])\)\s", p[start:]))
        if len(roman) >= 2:
            last = roman[-1]
            lab = last.group("n")
            nxt = _next_label(lab)
            seg_start = start + last.start()
            end_m = re.search(r"[.;]|$", p[seg_start:])
            end = seg_start + end_m.start()
            before = p[:seg_start]
            before = re.sub(r";\s*and\s*$", "; ", before)
            before = re.sub(r",\s*and\s*$", ", ", before)
            sep = ";" if ";" in p[start:seg_start] else ","
            return before + p[seg_start:end] + f"{sep} and ({nxt}) {listed}" + p[end:]
        tail = p[start:]
        stops = [
            tail.find(s)
            for s in (
                " (but ",
                " (other than",
                " (excluding",
                " (except",
                " (collectively",
                ", including",
                ", in each case",
                ", each of whom",
                ", provided",
                "; ",
                " who ",
                " that ",
                ".",
            )
        ]
        stops = [s for s in stops if s > 0]
        pos = start + (min(stops) if stops else len(tail))
        return p[:pos] + addition + p[pos:]

    def rule_retention(self, rule):
        name = rule.get("name") or "Retention"
        q = re.search(
            r"['\"“‘](Notwithstanding.+?)['\"”’](?:\s|\.|$)",
            rule.get("instruction", ""),
            re.S,
        )
        carve = q.group(1).strip() if q else DEFAULT_CARVE_OUT
        if not carve.endswith("."):
            carve += "."
        candidates = [
            i
            for i, p in enumerate(self.cur)
            if RETURN_HINTS.search(p)
            and re.search(
                r"confidential|evaluation material|materials|information", p, re.I
            )
        ]
        if not candidates:
            self.notes.append(f"{name}: no return-or-destroy clause found")
            return
        if any(RETAIN_EXISTS.search(self.cur[i]) for i in candidates) or any(
            RETAIN_EXISTS.search(p) for p in self.cur
        ):
            return
        # prefer the paragraph that talks about returning *and* destroying
        carve = self._adapt_party(carve)
        i = max(
            candidates,
            key=lambda k: (
                bool(re.search(r"return", self.cur[k], re.I))
                + bool(re.search(r"destr", self.cur[k], re.I)),
                -k,
            ),
        )
        p = self.cur[i].rstrip()
        sep = "" if p.endswith((".", ";")) else "."
        self.edit(
            i,
            p + sep + " " + carve,
            name,
            "Added a retention carve-out after the return-or-destroy obligation.",
        )

    def _adapt_party(self, text: str) -> str:
        """Use the document's own name for the receiving party in standard wording."""
        doc = " ".join(self.cur)
        # use the document's own defined term for the protected information
        if not re.search(r"[\"“]Confidential Information[\"”]", doc):
            m = re.search(
                r"[\"“]((?:Evaluation|Proprietary|Confidential|Disclosed)"
                r" (?:Material|Materials|Information))[\"”]",
                doc,
            )
            if m:
                text = text.replace("Confidential Information", m.group(1))
        if re.search(r"\bRecipient\b", doc):
            return text
        if re.search(r"\bReceiving Party\b", doc):
            name = "the Receiving Party"
        elif re.search(r"\byou\b", doc, re.I):
            text = re.sub(r"\bRecipient's\b", "your", text)
            return re.sub(r"\bRecipient\b", "you", text)
        else:
            return text
        text = re.sub(
            r"(^|\.\s+)Recipient\b",
            lambda m: m.group(1) + name[0].upper() + name[1:],
            text,
        )
        text = re.sub(r"\bRecipient's\b", name + "'s", text)
        return re.sub(r"\bRecipient\b", name, text)

    def rule_signature(self, rule):
        """Fill blank fields in the receiving party's signature block only."""
        name = rule.get("name") or "Signature block"
        firm, signer, title = (
            self.firm.get("name"),
            self.firm.get("signerName"),
            self.firm.get("signerTitle"),
        )
        if not (firm or signer or title):
            return
        why = "Filled the recipient's signature block from your firm details."
        witness = [
            i
            for i, p in enumerate(self.cur)
            if re.search(r"in witness|executed this agreement|signature page", p, re.I)
        ]
        start = witness[-1] if witness else max(0, len(self.cur) - 30)

        # 1. split the signature area into one block per party
        blocks, current = [], None
        for i in range(start, len(self.cur)):
            p = self.cur[i]
            if not p.strip() or BLANK_LINE.fullmatch(p):
                continue
            m = FIELD.match(p) or GENERIC_FIELD.match(p)
            label = m.group("label").lower().strip() if m else ""
            if m and not FIELD.match(p) and not BLANK.match(m.group("value") or "x"):
                m, label = (
                    None,
                    "",
                )  # "MARLOW: something" style line is a heading, not a blank field
            starts_block = (not m) or label in PARTY_LABELS
            if starts_block or current is None:
                current = {
                    "header": p,
                    "header_i": i if starts_block else None,
                    "fields": [],
                }
                blocks.append(current)
            if m and not (starts_block and label not in PARTY_LABELS):
                current["fields"].append((i, label, m.group("value")))

        # 2. decide which block belongs to the receiving party
        def says_recipient(b):
            return bool(RECIPIENT_WORDS.search(b["header"]))

        def says_other(b):
            return bool(re.search(r"disclos", b["header"], re.I))

        def blank_count(b):
            return sum(1 for _, _, v in b["fields"] if BLANK.match(v or ""))

        named = [b for b in blocks if says_recipient(b)]
        if named:
            targets = named
        else:
            # no block names the recipient: use the single block left blank, if there is exactly one
            open_blocks = [b for b in blocks if blank_count(b) and not says_other(b)]
            targets = open_blocks if len(open_blocks) == 1 else []
            if len(open_blocks) > 1:
                self.notes.append(
                    f"{name}: several blank signature blocks and none names the recipient; left for review"
                )

        # 3a. one-line signatures: "Signed by ____ for and on behalf of ____ (the Recipient)"
        for i in range(start, len(self.cur)):
            p = self.cur[i]
            if (
                FIELD.match(p)
                or GENERIC_FIELD.match(p)
                or not re.search(r"_{3,}", p)
                or not RECIPIENT_WORDS.search(p)
            ):
                continue
            new = p
            for m in reversed(list(re.finditer(r"_{3,}", p))):
                cue = p[max(0, m.start() - 30) : m.start()].lower()
                if re.search(r"on behalf of\s*$|\bfor\s*$|company\s*$|entity\s*$", cue):
                    value = firm
                elif re.search(r"(?:signed by|\bby|name)\s*:?\s*$", cue):
                    value = signer
                elif re.search(r"(?:title|position|capacity)\s*:?\s*$", cue):
                    value = title
                else:
                    value = None
                if value:
                    new = new[: m.start()] + value + new[m.end() :]
            if new != p:
                self.edit(i, new, name, why)

        # 3. fill blanks in the target block(s)
        for b in targets:
            labels = [lab for _, lab, _ in b["fields"]]
            has_name_line = any(
                lab in ("name", "printed name", "print name") for lab in labels
            )
            filled_company = False
            for i, lab, val in b["fields"]:
                if not BLANK.match(val or ""):
                    continue
                if lab in COMPANY_LABELS or lab.startswith("name of company"):
                    value = firm
                    filled_company = bool(firm)
                elif lab in (
                    "name",
                    "printed name",
                    "print name",
                    "signer",
                    "full name",
                    "name of signatory",
                ):
                    value = signer
                elif lab == "by":
                    value = (
                        None if has_name_line else signer
                    )  # "By:" is the signature line if "Name:" exists
                elif lab in ("title", "position", "its"):
                    value = title
                else:
                    value = None
                if not value:
                    continue
                p = self.cur[i]
                m = FIELD.match(p) or GENERIC_FIELD.match(p)
                vs, ve = m.span("value")
                nxt = i + 1
                if (
                    ve == vs
                    and nxt < len(self.cur)
                    and BLANK_LINE.fullmatch(self.cur[nxt])
                ):
                    self.edit(
                        nxt, value, name, why
                    )  # label/value table: fill the value cell
                    continue
                new = p[:vs] + value + p[ve:] if ve > vs else p.rstrip() + " " + value
                self.edit(i, new, name, why)
            hi = b["header_i"]
            if not firm or filled_company or hi is None:
                continue
            h = self.cur[hi]
            if PLACEHOLDER_PARTY.fullmatch(h.strip()):
                self.edit(hi, firm, name, why)  # "[RECIPIENT NAME]" heading
            elif re.match(
                r"^\s*(the )?(recipient|receiving party|counterparty)\s*:?\s*$", h, re.I
            ):
                h = h.rstrip()
                self.edit(
                    hi, h + ("" if h.endswith(":") else ":") + " " + firm, name, why
                )

    def fill_placeholders(self):
        for i, p in enumerate(self.cur):
            new = p
            for ph, key in PLACEHOLDERS.items():
                if ph in new and self.firm.get(key):
                    new = new.replace(ph, self.firm[key])
            if self.firm.get("name"):
                new = PLACEHOLDER_PARTY.sub(self.firm["name"], new)
            if new != p:
                self.edit(i, new, "Firm details", "Filled firm details.")

    # -- liability: never turn a disclaimer ("shall have no liability") into a damages cap,
    # which would give the other side a liability it had excluded
    def rule_liability(self, rule):
        idx = [
            i
            for i in self._relevant(rule)
            if re.search(r"liab|damages|indemn", self.cur[i], re.I)
            and not NO_LIABILITY.search(self.cur[i])
        ]
        if not idx:
            self.notes.append(
                f"{rule.get('name') or 'Rule'}: no clause makes the receiving party liable "
                "for damages; nothing to limit"
            )
            return
        self.llm_edit(
            rule,
            idx,
            extra=(
                "Only limit the receiving party's own liability. Never edit a clause so that "
                "the disclosing party becomes liable for something it was not liable for before."
            ),
        )

    def _relevant(self, rule) -> list[int]:
        kw = _keywords(" ".join(str(rule.get(k, "")) for k in ("name", "instruction")))
        scored = sorted(
            ((len(kw & _keywords(p)), i) for i, p in enumerate(self.cur) if p.strip()),
            reverse=True,
        )
        return sorted(i for s, i in scored[:6] if s > 0)

    # -- generic rules: one focused LLM call
    def rule_generic(self, rule):
        idx = self._relevant(rule)
        if not idx:
            self.notes.append(f"{rule.get('name')}: no relevant clause found")
            return
        self.llm_edit(rule, idx)

    def llm_edit(self, rule, idx: list[int], extra: str = ""):
        if not self.llm:
            self.notes.append(
                f"{rule.get('name')}: needs a language model; none configured"
            )
            return
        name = rule.get("name") or "Rule"
        listing = "\n".join(f"[{i}] {self.cur[i]}" for i in idx)
        system = (
            "You are a careful NDA reviewer making tracked-change edits for the receiving party. "
            "Make only the edits the rule requires, as small as possible. Copy text exactly. "
            "If the clauses already satisfy the rule, return no edits. Return JSON only."
            + (" " + extra if extra else "")
        )
        user = (
            f"Rule: {name}\nInstruction: {rule.get('instruction', '')}\n\n"
            f"Clauses (numbered by paragraph):\n{listing}\n\n"
            'Return {"edits": [{"paragraph": <number>, "current_text": "<exact text copied from that '
            'paragraph>", "new_text": "<replacement>", "reason": "<one short sentence>"}]}'
        )
        for _attempt in range(2):
            data = self.ask(system, user)
            edits = (data or {}).get("edits", []) if isinstance(data, dict) else []
            bad = []
            for e in edits:
                try:
                    i = int(e.get("paragraph"))
                except Exception:
                    bad.append(e)
                    continue
                cur, new = e.get("current_text") or "", e.get("new_text") or ""
                if i not in idx or not cur:
                    bad.append(e)
                    continue
                from .tracked_docx import find_span

                span = find_span(self.cur[i], cur)
                if not span:
                    bad.append(e)
                    continue
                p = self.cur[i]
                self.edit(
                    i,
                    p[: span[0]] + new + p[span[1] :],
                    name,
                    e.get("reason") or f"Applied rule: {name}.",
                )
            if not bad:
                return
            user += (
                "\n\nSome edits could not be applied because current_text was not copied exactly "
                f"from the numbered paragraph: {json.dumps(bad)[:800]}. Return only corrected edits."
            )


def plan_changes(
    paragraphs: list[str], rules: list[dict], firm: dict, llm: LLM | None = None
):
    planner = Planner(paragraphs, firm, llm)
    planner.run(rules or [])
    return planner.changes(), planner.notes
