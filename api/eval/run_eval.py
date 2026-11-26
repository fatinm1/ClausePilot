"""End-to-end evaluation of ClausePilot's redlining across LLM providers.

For every provider (plus the rule-based baseline) and every synthetic NDA in
eval/ndas.py, this runs the real pipeline (DocumentProcessor.process_document:
prompt -> LLM -> parse -> apply tracked changes -> firm details -> save .docx),
then opens the output and scores it.

Usage (from the api/ folder, with provider keys in the environment or api/.env):
    python -m eval.run_eval                      # every provider that has a key, 2 runs each
    python -m eval.run_eval --providers groq,rule-based --runs 3
    python -m eval.run_eval --pause 20           # seconds between LLM calls (free-tier limits)

Writes eval/results/<timestamp>/report.md, results.json and every output .docx.
"""

import argparse
import json
import logging
import os
import re
import statistics
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

from docx import Document
from lxml import etree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

try:
    from dotenv import load_dotenv

    load_dotenv(HERE.parent / ".env")
except Exception:
    pass

from eval.ndas import BLIND, FIRM, HOLDOUT, NDAS, RULES, flat_paragraphs  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
RULE_KEYS = ["term", "reps", "retain", "sign"]
RULE_LABEL = {
    "term": "Term capped",
    "reps": "Representatives widened",
    "retain": "Retention carve-out",
    "sign": "Signature block",
}


# --------------------------------------------------------------------------- docs
def build_docx(nda: dict, path: Path):
    doc = Document()
    for item in nda["paragraphs"]:
        if isinstance(item, tuple):
            p = doc.add_paragraph()
            p.add_run(item[0]).bold = True
            p.add_run(item[1])
        elif isinstance(item, dict):
            rows = item["table"]
            t = doc.add_table(rows=len(rows), cols=len(rows[0]))
            for r, row in enumerate(rows):
                for c, text in enumerate(row):
                    t.cell(r, c).text = text
        else:
            doc.add_paragraph(item)
    doc.save(path)


def read_output(path: Path):
    """Return per-paragraph (original, accepted, has_tracked) plus XML stats."""
    with zipfile.ZipFile(path) as z:
        root = etree.fromstring(z.read("word/document.xml"))
    paras = []
    for p in root.iter(W + "p"):
        original, accepted, tracked = [], [], False
        for node in p.iter():
            if node.tag == W + "t":
                in_ins = any(a.tag == W + "ins" for a in node.iterancestors())
                accepted.append(node.text or "")
                if in_ins:
                    tracked = True
                else:
                    original.append(node.text or "")
            elif node.tag == W + "delText":
                original.append(node.text or "")
                tracked = True
        paras.append(("".join(original), "".join(accepted), tracked))
    ids = [el.get(W + "id") for el in root.iter(W + "ins", W + "del")]
    return paras, {
        "ins": len(root.findall(f".//{W}ins")),
        "del": len(root.findall(f".//{W}del")),
        "ids_total": len(ids),
        "ids_non_numeric": sum(1 for i in ids if not (i or "").isdigit()),
        "ids_duplicate": len(ids) - len(set(ids)),
    }


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def find_para(paras, prefix):
    for o, a, t in paras:
        if norm(o).startswith(norm(prefix)) or norm(a).startswith(norm(prefix)):
            return o, a, t
    return None


# --------------------------------------------------------------------------- scoring
def score(nda: dict, paras) -> dict:
    exp = nda["expect"]
    res = {}

    # Term
    p = find_para(paras, nda["term_para"])
    if not p:
        res["term"] = (False, "term paragraph missing from output")
    else:
        o, a, t = p
        capped = bool(
            re.search(
                r"two \(2\) years|\b2 years\b|twenty-four \(24\) months|24 months",
                a,
                re.I,
            )
        )
        old_gone = norm(nda["term_old"]) not in norm(a) or exp["term"] == "keep"
        if exp["term"] == "keep":
            ok = norm(o) == norm(a)
            res["term"] = (
                ok,
                "unchanged" if ok else f"changed although already compliant: {a[:140]}",
            )
        else:
            ok = capped and old_gone and t
            why = []
            if not capped:
                why.append("no two-year period in clause")
            if not old_gone:
                why.append(f"'{nda['term_old']}' still present")
            if capped and old_gone and not t:
                why.append("changed without tracked changes")
            res["term"] = (ok, "capped at two years" if ok else "; ".join(why))

    # Representatives
    p = find_para(paras, nda["reps_para"])
    if not p:
        res["reps"] = (False, "Representatives paragraph missing")
    else:
        o, a, t = p
        if exp["reps"] == "keep":
            ok = norm(o) == norm(a)
            res["reps"] = (
                ok,
                "unchanged" if ok else f"changed although complete: {a[:140]}",
            )
        else:
            have = {
                w: (w in a.lower())
                for w in ["investor", "agent", "advisor", "financing"]
            }
            ok = all(have.values()) and t
            missing = [w for w, v in have.items() if not v]
            res["reps"] = (
                ok,
                (
                    "all four categories present"
                    if ok
                    else f"missing: {', '.join(missing) or 'tracking'}"
                ),
            )

    # Retention
    all_acc = " ".join(a for _, a, _ in paras)
    retention_hits = len(re.findall(r"retention polic", all_acc, re.I))
    if exp["retain"] == "keep":
        rp = find_para(paras, nda["return_para"])
        unchanged = rp is not None and norm(rp[0]) == norm(rp[1])
        ok = retention_hits <= 1 and unchanged
        res["retain"] = (
            ok,
            "left alone" if ok else "carve-out added although one already exists",
        )
    else:
        ok = retention_hits >= 1 and re.search(r"retain", all_acc, re.I) is not None
        res["retain"] = (
            bool(ok),
            "carve-out inserted" if ok else "no retention carve-out in output",
        )

    # Signature
    sig_text = " ".join(a for _, a, _ in paras[-nda.get("sign_len", 8) - 2 :])
    have = {
        "firm": FIRM["name"].lower() in sig_text.lower(),
        "signer": FIRM["signerName"].lower() in sig_text.lower(),
        "title": FIRM["signerTitle"].lower() in sig_text.lower(),
    }
    lines = nda.get(
        "discloser_lines", ["By: Avery Castellanos", "Title: Chief Executive Officer"]
    )
    discloser_intact = all(any(norm(a) == norm(x) for _, a, _ in paras) for x in lines)
    ok = all(have.values()) and discloser_intact
    why = [k for k, v in have.items() if not v]
    if not discloser_intact:
        why.append("Discloser's signer overwritten")
    res["sign"] = (
        ok,
        "firm, signer and title filled" if ok else "missing/wrong: " + ", ".join(why),
    )
    return res


def collateral(nda: dict, paras) -> dict:
    """Paragraphs no rule should touch: count edits (tracked or silent)."""
    targets = [nda["term_para"], nda["reps_para"], nda["return_para"]]
    src = flat_paragraphs(nda)
    sig_start = len(src) - nda.get("sign_len", 8)
    touched, silent = [], []
    out_by_orig = {norm(o): (o, a, t) for o, a, t in paras}
    for i, text in enumerate(src):
        if i >= sig_start or any(norm(text).startswith(norm(x)) for x in targets):
            continue
        hit = out_by_orig.get(norm(text))
        if hit is None:
            # original text no longer reconstructable = silent (untracked) edit or deletion
            silent.append(text[:80])
            continue
        o, a, t = hit
        if norm(o) != norm(a):
            touched.append(text[:80])
    # silent edits anywhere: output original text differs from every input paragraph
    src_norm = {norm(s) for s in src}
    untracked = [
        o[:80] for o, a, t in paras if o.strip() and norm(o) not in src_norm and not t
    ]
    return {
        "unrelated_edited": touched,
        "unrelated_missing": silent,
        "untracked_edits": untracked,
    }


# --------------------------------------------------------------------------- running
def run_one(provider: str, nda: dict, workdir: Path, run_idx: int):
    import app.services.ai_redlining as ai

    if provider == "rule-based":
        os.environ["LLM_PROVIDER_ORDER"] = "none"
    else:
        os.environ["LLM_PROVIDER_ORDER"] = provider

    svc = ai.AIRedliningService()
    stats = {
        "llm_calls": 0,
        "llm_seconds": 0.0,
        "tokens_in": 0,
        "tokens_out": 0,
        "fell_back": False,
        "llm_error": None,
    }

    orig_complete = svc._complete

    def timed_complete(messages, **kw):
        t0 = time.perf_counter()
        stats["llm_calls"] += 1
        try:
            name, resp = orig_complete(messages, **kw)
            u = getattr(resp, "usage", None)
            if u:
                stats["tokens_in"] += getattr(u, "prompt_tokens", 0) or 0
                stats["tokens_out"] += getattr(u, "completion_tokens", 0) or 0
            return name, resp
        except Exception as e:
            stats["llm_error"] = str(e)[:300]
            raise
        finally:
            stats["llm_seconds"] += time.perf_counter() - t0

    svc._complete = timed_complete
    captured = {}
    orig_plan = svc.plan_changes

    def capture(*a, **k):
        r = orig_plan(*a, **k)
        captured["changes"], captured["notes"] = r
        return r

    svc.plan_changes = capture

    src = workdir / f"{nda['id']}.docx"
    if not src.exists():
        build_docx(nda, src)
    run_src = workdir / f"{nda['id']}__{provider}__run{run_idx}.docx"
    run_src.write_bytes(src.read_bytes())

    t0 = time.perf_counter()
    result = ai.DocumentProcessor(svc).process_document(str(run_src), RULES, FIRM, None)
    total = time.perf_counter() - t0

    row = {
        "provider": provider,
        "model": svc.model if provider != "rule-based" else "code only",
        "nda": nda["id"],
        "run": run_idx,
        "success": bool(result.get("success")),
        "error": result.get("error"),
        "modifications": result.get("modifications_applied"),
        "seconds_total": round(total, 2),
        **{k: (round(v, 2) if isinstance(v, float) else v) for k, v in stats.items()},
    }
    if not row["success"]:
        return row

    out = Path(result["output_path"])
    keep = workdir / f"OUT_{nda['id']}__{provider}__run{run_idx}.docx"
    keep.write_bytes(out.read_bytes())
    paras, xml = read_output(keep)
    try:
        Document(str(keep))
        row["opens"] = True
    except Exception as e:
        row["opens"] = False
        row["open_error"] = str(e)[:200]
    s = score(nda, paras)
    row["checks"] = {k: {"pass": bool(v[0]), "note": v[1]} for k, v in s.items()}
    row["score"] = sum(1 for v in s.values() if v[0])
    row["xml"] = xml
    row["collateral"] = collateral(nda, paras)
    row["output_file"] = keep.name

    mods = captured.get("changes") or []
    row["notes"] = captured.get("notes") or []
    row["fell_back"] = bool(stats["llm_error"])
    sim, applied, matched, needs_match = simulate(nda, mods)
    ms = score(nda, sim)
    row["proposed"] = {
        "count": len(mods),
        "exact_match": f"{matched}/{needs_match}",
        "exact_match_rate": (matched / needs_match) if needs_match else None,
        "checks": {k: {"pass": bool(v[0]), "note": v[1]} for k, v in ms.items()},
        "score": sum(1 for v in ms.values() if v[0]),
        "collateral": collateral(nda, sim),
        "mods": mods,
    }
    return row


def simulate(nda: dict, mods):
    """Apply the model's instructions to plain paragraph text, the way a
    perfect pipeline would, to score the model separately from the .docx writer."""
    orig = flat_paragraphs(nda)
    acc = list(orig)
    tracked = [False] * len(orig)
    applied = matched = needs = 0
    for m in mods:
        t = (m.get("type") or "").upper()
        cur, new = m.get("current_text") or "", m.get("new_text") or ""
        if t in ("TEXT_REPLACE", "TEXT_DELETE"):
            needs += 1
            for i, ptxt in enumerate(acc):
                if cur and cur in ptxt:
                    acc[i] = ptxt.replace(cur, "" if t == "TEXT_DELETE" else new, 1)
                    tracked[i] = True
                    matched += 1
                    applied += 1
                    break
        elif t in ("TEXT_INSERT", "CLAUSE_ADD") and new:
            hint = (m.get("location_hint") or "").lower()
            idx = len(acc) - 9
            for i, ptxt in enumerate(acc):
                if hint and hint[:25] in ptxt.lower():
                    idx = i
                    break
            acc.insert(idx + 1, new)
            orig.insert(idx + 1, "")
            tracked.insert(idx + 1, True)
            applied += 1
    paras = list(zip(orig, acc, tracked, strict=True))
    return paras, applied, matched, needs


def pct(n, d):
    return f"{(100 * n / d):.0f}%" if d else "–"


def p95(xs):
    if not xs:
        return 0
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(0.95 * (len(xs) - 1))))]


def report(rows, out_dir: Path, args):
    lines = [
        "# ClausePilot redlining evaluation",
        "",
        f"Run {datetime.now():%Y-%m-%d %H:%M}. {len({r['nda'] for r in rows})} synthetic NDAs x {args.runs} runs per provider, "
        f"4 rules each, real pipeline end to end. Pause between LLM calls: {args.pause}s.",
        "",
        "## Delivered document (what the pipeline actually wrote)",
        "",
        "| Provider | Model | Runs OK | Rule checks passed | Perfect docs | LLM errors | Collateral edits | Untracked edits | Invalid change IDs | p50 time | p95 time | Avg tokens in/out |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    providers = list(dict.fromkeys(r["provider"] for r in rows))
    for prov in providers:
        rs = [r for r in rows if r["provider"] == prov]
        ok = [r for r in rs if r["success"]]
        checks = sum(r.get("score", 0) for r in ok)
        perfect = sum(1 for r in ok if r.get("score") == 4)
        fb = sum(1 for r in rs if r.get("fell_back"))
        coll = sum(
            len(r["collateral"]["unrelated_edited"])
            + len(r["collateral"]["unrelated_missing"])
            for r in ok
        )
        untr = sum(len(r["collateral"]["untracked_edits"]) for r in ok)
        bad_ids = sum(
            r["xml"]["ids_non_numeric"] + r["xml"]["ids_duplicate"] for r in ok
        )
        times = [r["seconds_total"] for r in ok]
        tin = statistics.mean([r["tokens_in"] for r in ok]) if ok else 0
        tout = statistics.mean([r["tokens_out"] for r in ok]) if ok else 0
        model = rs[0]["model"]
        lines.append(
            f"| {prov} | {model} | {len(ok)}/{len(rs)} | {checks}/{4 * len(ok)} ({pct(checks, 4 * len(ok))}) | "
            f"{perfect}/{len(ok)} | {fb} | {coll} | {untr} | {bad_ids} | "
            f"{statistics.median(times) if times else 0:.1f}s | {p95(times):.1f}s | {tin:.0f} / {tout:.0f} |"
        )

    lines += [
        "",
        "## Model quality (what the model proposed, applied perfectly)",
        "",
        "Scores the model's JSON instructions on their own, by applying them to the plain text. "
        "This separates model quality from bugs in the .docx writer.",
        "",
        "| Provider | Rule checks passed | Perfect docs | Instructions that match the text exactly | Collateral edits |",
        "|---|---|---|---|---|",
    ]
    for prov in providers:
        ok = [
            r
            for r in rows
            if r["provider"] == prov and r["success"] and "proposed" in r
        ]
        checks = sum(r["proposed"]["score"] for r in ok)
        perfect = sum(1 for r in ok if r["proposed"]["score"] == 4)
        m = [int(x) for r in ok for x in r["proposed"]["exact_match"].split("/")]
        mt, nd = sum(m[0::2]), sum(m[1::2])
        coll = sum(len(r["proposed"]["collateral"]["unrelated_edited"]) for r in ok)
        lines.append(
            f"| {prov} | {checks}/{4 * len(ok)} ({pct(checks, 4 * len(ok))}) | {perfect}/{len(ok)} | {mt}/{nd} ({pct(mt, nd)}) | {coll} |"
        )
    lines += [
        "",
        "| Provider | " + " | ".join(RULE_LABEL[k] for k in RULE_KEYS) + " |",
        "|---|" + "---|" * len(RULE_KEYS),
    ]
    for prov in providers:
        ok = [
            r
            for r in rows
            if r["provider"] == prov and r["success"] and "proposed" in r
        ]
        cells = []
        for k in RULE_KEYS:
            n = sum(1 for r in ok if r["proposed"]["checks"][k]["pass"])
            cells.append(f"{n}/{len(ok)}")
        lines.append(f"| {prov} | " + " | ".join(cells) + " |")

    lines += [
        "",
        "## Delivered document: pass rate by rule",
        "",
        "| Provider | " + " | ".join(RULE_LABEL[k] for k in RULE_KEYS) + " |",
        "|---|" + "---|" * len(RULE_KEYS),
    ]
    for prov in providers:
        ok = [r for r in rows if r["provider"] == prov and r["success"]]
        cells = []
        for k in RULE_KEYS:
            n = sum(1 for r in ok if r["checks"][k]["pass"])
            cells.append(f"{n}/{len(ok)} ({pct(n, len(ok))})")
        lines.append(f"| {prov} | " + " | ".join(cells) + " |")

    ran = [n for n in NDAS + HOLDOUT + BLIND if any(r["nda"] == n["id"] for r in rows)]
    lines += [
        "",
        "## Pass rate by document",
        "",
        "| Provider | " + " | ".join(n["id"] for n in ran) + " |",
        "|---|" + "---|" * len(ran),
    ]
    for prov in providers:
        cells = []
        for n in ran:
            rs = [
                r
                for r in rows
                if r["provider"] == prov and r["nda"] == n["id"] and r["success"]
            ]
            got = sum(r["score"] for r in rs)
            cells.append(f"{got}/{4 * len(rs)}")
        lines.append(f"| {prov} | " + " | ".join(cells) + " |")

    lines += ["", "## Failures", ""]
    for r in rows:
        if not r["success"]:
            lines.append(
                f"- **{r['provider']} / {r['nda']} run {r['run']}**: pipeline error: {r['error']}"
            )
            continue
        fails = [
            f"{RULE_LABEL[k]}: {v['note']}"
            for k, v in r["checks"].items()
            if not v["pass"]
        ]
        extra = []
        if r.get("fell_back"):
            extra.append(f"an LLM call failed ({r.get('llm_error')})")
        if r.get("notes"):
            extra.append(f"planner notes: {r['notes']}")
        c = r["collateral"]
        if c["unrelated_edited"]:
            extra.append(f"edited unrelated clauses: {c['unrelated_edited']}")
        if c["unrelated_missing"]:
            extra.append(
                f"unrelated clauses altered without tracking or removed: {c['unrelated_missing']}"
            )
        if fails or extra:
            lines.append(
                f"- **{r['provider']} / {r['nda']} run {r['run']}** ({r['output_file']}): "
                + "; ".join(fails + extra)
            )
    lines += [
        "",
        "## How to read this",
        "",
        "- *Rule checks*: 4 per document. Term must read two years with the old period gone (or stay untouched in the compliant NDA); "
        "Representatives must list investors, agents, advisors and financing sources; a retention carve-out must exist (and not be duplicated); "
        "the Recipient's signature block must carry the firm, signer and title while the Discloser's signer stays intact.",
        "- *Collateral edits*: changes to clauses no rule asked about.",
        "- *Untracked edits*: text changed in the .docx without Word tracked-change markup (the reviewer would not see it).",
        "- *Invalid change IDs*: Word requires numeric, unique w:id values on insertions and deletions; bad IDs can make Word repair the file.",
        "- Times are the whole pipeline per document, including the LLM call.",
    ]
    (out_dir / "report.md").write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--providers",
        default="auto",
        help="comma list from groq,gemini,openrouter,openai,rule-based",
    )
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument(
        "--pause", type=float, default=3.0, help="seconds to wait between LLM calls"
    )
    ap.add_argument("--only", default="", help="comma list of NDA ids to run")
    ap.add_argument(
        "--set",
        default="all",
        choices=["all", "dev", "holdout", "blind"],
        help="which NDAs to run",
    )
    args = ap.parse_args()

    logging.basicConfig(level=logging.ERROR)
    import app.services.ai_redlining as ai

    if args.providers == "auto":
        provs = [
            p
            for p, cfg in ai.PROVIDERS.items()
            if (os.getenv(cfg[0]) or "").strip() not in ai.PLACEHOLDER_KEYS
        ]
        provs.append("rule-based")
    else:
        provs = [p.strip() for p in args.providers.split(",") if p.strip()]

    pool = {
        "dev": NDAS,
        "holdout": HOLDOUT,
        "blind": BLIND,
        "all": NDAS + HOLDOUT + BLIND,
    }[args.set]
    ndas = [n for n in pool if not args.only or n["id"] in args.only.split(",")]
    out_dir = HERE / "results" / datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)
    print(
        f"Providers: {provs}\nNDAs: {[n['id'] for n in ndas]}\nRuns: {args.runs}\nOutput: {out_dir}\n"
    )

    rows = []
    for prov in provs:
        for run_idx in range(1, args.runs + 1):
            for nda in ndas:
                row = run_one(prov, nda, out_dir, run_idx)
                rows.append(row)
                status = f"{row.get('score', 0)}/4" if row["success"] else "ERROR"
                fb = " (fell back to rules)" if row.get("fell_back") else ""
                print(
                    f"{prov:12s} run {run_idx}  {nda['id']:24s} {status:6s} {row['seconds_total']:6.1f}s{fb}"
                )
                if prov != "rule-based" and args.pause:
                    time.sleep(args.pause)
        (out_dir / "results.json").write_text(json.dumps(rows, indent=2, default=str))

    report(rows, out_dir, args)
    print(f"\nReport: {out_dir / 'report.md'}")


if __name__ == "__main__":
    main()
