"""Run the complex NDA set (eval/complex_ndas.py) through the real pipeline.

python -m eval.run_complex                 # code only (no model)
python -m eval.run_complex --providers groq,gemini --runs 2
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

from docx import Document

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

try:
    from dotenv import load_dotenv

    load_dotenv(HERE.parent / ".env")
except Exception:
    pass

from eval.complex_ndas import (  # noqa: E402
    COMPLEX,
    COMPLEX_BLIND2,
    build,
    original_paragraphs,
    visible_paragraphs,
)
from eval.ndas import FIRM, RULES  # noqa: E402
from eval.run_eval import read_output  # noqa: E402


def norm(s):
    return re.sub(
        r"\s+", " ", (s or "").replace("“", '"').replace("”", '"').replace("’", "'")
    ).strip()


def locate(paras, check):
    hits = [k for k, (o, a, t) in enumerate(paras) if norm(check["find"]) in norm(o)]
    if not hits:
        return None
    if check.get("last"):
        return hits[-1]
    return hits[min(check.get("nth", 0), len(hits) - 1)]


def run_check(paras, check, nda):
    k = locate(paras, check)
    if k is None:
        return False, "paragraph not found in output"
    o, a, t = paras[k]
    if check["expect"] == "keep":
        # unchanged = what a reader sees is exactly what they saw in the input
        visible = {norm(x) for x in visible_paragraphs(nda)}
        ok = norm(a) in visible and norm(o) in {
            norm(x) for x in original_paragraphs(nda)
        }
        return ok, "unchanged" if ok else f"changed: {a[:160]}"
    texts = [a] + (
        [paras[k + 1][1]] if check.get("or_next") and k + 1 < len(paras) else []
    )
    joined = " ".join(texts)
    tracked = t or (check.get("or_next") and k + 1 < len(paras) and paras[k + 1][2])
    problems = []
    if norm(o) == norm(a) and not check.get("or_next"):
        problems.append("not changed")
    if not tracked:
        problems.append("not tracked")
    for s in check.get("all_of", []):
        if norm(s).lower() not in norm(joined).lower():
            problems.append(f"missing '{s}'")
    if check.get("any_of") and not any(
        norm(s).lower() in norm(joined).lower() for s in check["any_of"]
    ):
        problems.append(f"none of {check['any_of']}")
    order = check.get("order")
    if order and not (0 <= joined.find(order[0]) < joined.find(order[1])):
        problems.append(f"'{order[0]}' should come before '{order[1]}'")
    if check["rule"] == "sign" and "___" in a:
        problems.append("blank line not removed")
    for s in check.get("absent", []):
        if norm(s).lower() in norm(a).lower():
            problems.append(f"still contains '{s}'")
    return not problems, (
        "ok" if not problems else "; ".join(problems) + f" | got: {a[:200]}"
    )


def untracked_edits(nda, paras):
    src = {norm(x) for x in original_paragraphs(nda)}
    return [o[:90] for o, a, t in paras if o.strip() and norm(o) not in src]


def lo_check(path: Path):
    soffice = shutil.which("soffice")
    if not soffice:
        return None
    out = path.parent / "lo"
    out.mkdir(exist_ok=True)
    subprocess.run(
        [
            soffice,
            "--headless",
            "--norestore",
            "--convert-to",
            "odt",
            "--outdir",
            str(out),
            str(path),
        ],
        capture_output=True,
        timeout=180,
    )
    odt = out / (path.stem + ".odt")
    if not odt.exists():
        return {"opens": False}
    x = zipfile.ZipFile(odt).read("content.xml").decode()
    return {
        "opens": True,
        "insertions": x.count("<text:insertion"),
        "deletions": x.count("<text:deletion"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--providers", default="rule-based")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--only", default="")
    ap.add_argument("--set", default="all", choices=["all", "round1", "blind2"])
    args = ap.parse_args()
    import logging

    logging.basicConfig(level=logging.ERROR)
    import app.services.ai_redlining as ai

    out_dir = HERE / "results" / ("complex-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for prov in [p.strip() for p in args.providers.split(",")]:
        os.environ["LLM_PROVIDER_ORDER"] = "none" if prov == "rule-based" else prov
        for run in range(1, args.runs + 1):
            for nda in {
                "round1": COMPLEX,
                "blind2": COMPLEX_BLIND2,
                "all": COMPLEX + COMPLEX_BLIND2,
            }[args.set]:
                if args.only and nda["id"] not in args.only.split(","):
                    continue
                src = out_dir / f"{nda['id']}.docx"
                if not src.exists():
                    build(nda, src)
                work = out_dir / f"{nda['id']}__{prov}__{run}.docx"
                work.write_bytes(src.read_bytes())
                svc = ai.AIRedliningService()
                t0 = time.perf_counter()
                res = ai.DocumentProcessor(svc).process_document(
                    str(work), RULES, FIRM, None
                )
                secs = time.perf_counter() - t0
                row = {
                    "provider": prov,
                    "nda": nda["id"],
                    "run": run,
                    "seconds": round(secs, 2),
                    "success": res.get("success"),
                    "error": res.get("error"),
                    "analysis": res.get("ai_analysis"),
                }
                if res.get("success"):
                    keep = out_dir / f"OUT_{work.name}"
                    keep.write_bytes(Path(res["output_path"]).read_bytes())
                    paras, xml = read_output(keep)
                    Document(str(keep))
                    row["xml"] = xml
                    row["checks"] = []
                    for c in nda["checks"]:
                        ok, note = run_check(paras, c, nda)
                        row["checks"].append(
                            {
                                **{k: c[k] for k in ("rule", "find", "expect")},
                                "pass": ok,
                                "note": note,
                            }
                        )
                    row["untracked"] = untracked_edits(nda, paras)
                    row["libreoffice"] = lo_check(keep)
                rows.append(row)
                n_ok = sum(c["pass"] for c in row.get("checks", []))
                print(
                    f"{prov:10s} {nda['id']:40s} {n_ok}/{len(nda['checks'])} checks  {secs:5.2f}s  untracked={len(row.get('untracked', []))}"
                )
    (out_dir / "results.json").write_text(json.dumps(rows, indent=2, default=str))

    lines = [
        "# Complex NDA evaluation",
        "",
        f"Run {datetime.now():%Y-%m-%d %H:%M}.",
        "",
        "| Provider | Document | Checks passed | Untracked edits | Invalid IDs | Opens in LibreOffice | Time |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        if not r.get("success"):
            lines.append(
                f"| {r['provider']} | {r['nda']} | ERROR: {r['error']} | | | | |"
            )
            continue
        n_ok = sum(c["pass"] for c in r["checks"])
        lo = r["libreoffice"]
        lo_s = "n/a" if lo is None else ("yes" if lo["opens"] else "NO")
        bad = r["xml"]["ids_non_numeric"] + r["xml"]["ids_duplicate"]
        lines.append(
            f"| {r['provider']} | {r['nda']} | {n_ok}/{len(r['checks'])} | {len(r['untracked'])} | {bad} | {lo_s} | {r['seconds']}s |"
        )
    by_rule = {}
    for r in rows:
        for c in r.get("checks", []):
            k = (r["provider"], c["rule"])
            by_rule.setdefault(k, [0, 0])
            by_rule[k][0] += c["pass"]
            by_rule[k][1] += 1
    lines += ["", "| Provider | Rule | Passed |", "|---|---|---|"]
    for (p, rule), (a, b) in sorted(by_rule.items()):
        lines.append(f"| {p} | {rule} | {a}/{b} |")
    lines += ["", "## Failed checks", ""]
    for r in rows:
        for c in r.get("checks", []):
            if not c["pass"]:
                lines.append(
                    f"- **{r['provider']} / {r['nda']}** [{c['rule']}, expect {c['expect']}] `{c['find']}`: {c['note']}"
                )
        for u in r.get("untracked", []):
            lines.append(f"- **{r['provider']} / {r['nda']}** untracked edit: {u}")
    (out_dir / "report.md").write_text("\n".join(lines))
    print(f"\nReport: {out_dir / 'report.md'}")


if __name__ == "__main__":
    main()
