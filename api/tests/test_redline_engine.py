"""Unit tests for the redline planner and the tracked-changes writer.

Run from api/:  python -m pytest tests -q
"""

import json
import zipfile

from docx import Document

from app.services.redline_engine import plan_changes
from app.services.tracked_docx import ChangeIds, apply_edit, word_ops
from eval.ndas import FIRM, RULES

REPS = '2. Representatives. "Representatives" means a party\'s affiliates, directors, officers and employees.'
DOC = [
    "NDA",
    REPS,
    "9. Governing Law. This Agreement is governed by the laws of Delaware.",
]


def stub(*replies):
    calls = []

    def llm(messages):
        calls.append(messages)
        return replies[min(len(calls) - 1, len(replies) - 1)]

    llm.calls = calls
    return llm


def test_reps_uses_valid_model_wording():
    better = REPS.replace(
        "officers and employees",
        "officers, employees, investors, agents, advisors and potential financing sources",
    )
    changes, _ = plan_changes(
        DOC, [RULES[1]], {}, stub(json.dumps({"new_text": better}))
    )
    assert changes[0]["new_text"] == better


def test_reps_rejects_model_that_deletes_words():
    bad = '2. Representatives. "Representatives" means investors, agents, advisors and potential financing sources.'
    changes, _ = plan_changes(DOC, [RULES[1]], {}, stub(json.dumps({"new_text": bad})))
    new = changes[0]["new_text"]
    assert "affiliates, directors, officers" in new and "financing sources" in new


def test_generic_rule_retries_after_bad_quote():
    rule = {"name": "Governing law", "instruction": "Governing law must be Maryland."}
    wrong = {
        "edits": [
            {
                "paragraph": 2,
                "current_text": "laws of the State of Delaware",
                "new_text": "laws of Maryland",
            }
        ]
    }
    right = {
        "edits": [
            {
                "paragraph": 2,
                "current_text": "laws of Delaware",
                "new_text": "laws of Maryland",
            }
        ]
    }
    llm = stub(json.dumps(wrong), json.dumps(right))
    changes, _ = plan_changes(DOC, [rule], {}, llm)
    assert len(llm.calls) == 2
    assert changes[0]["new_text"].endswith("laws of Maryland.")


def test_garbage_reply_falls_back_to_code():
    changes, _ = plan_changes(
        DOC, [RULES[1]], {}, stub("I think you should add investors.")
    )
    assert "financing sources" in changes[0]["new_text"]


def test_compliant_document_is_left_alone():
    doc = [
        '1. "Representatives" means affiliates, directors, investors, agents, advisors and potential financing sources.',
        "2. Term. These obligations continue for two (2) years.",
        "3. Return. Recipient will return or destroy all information, but may retain copies under its retention policy.",
    ]
    changes, _ = plan_changes(doc, RULES[:3], {}, None)
    assert changes == []


def test_non_solicit_and_notice_periods_not_capped():
    doc = [
        "5. Non-Solicitation. For thirty-six (36) months the Recipient will not solicit employees.",
        "6. Term. Either party may terminate on ninety (90) days' notice; obligations survive for five (5) years.",
    ]
    changes, _ = plan_changes(doc, [RULES[0]], {}, None)
    assert len(changes) == 1 and "survive for two (2) years" in changes[0]["new_text"]
    assert "ninety (90) days" in changes[0]["new_text"]


def test_word_ops_marks_phrases_not_letters():
    ops = word_ops("for five (5) years", "for two (2) years")
    assert ops == [(4, 12, "two (2)")]


def test_writer_produces_numeric_ids_and_keeps_formatting(tmp_path):
    d = Document()
    p = d.add_paragraph()
    p.add_run("4. Term.").bold = True
    p.add_run(" Obligations survive for five (5) years.")
    assert apply_edit(
        p, p.text, "4. Term. Obligations survive for two (2) years.", ChangeIds(d)
    )
    f = tmp_path / "o.docx"
    d.save(f)
    xml = zipfile.ZipFile(f).read("word/document.xml").decode()
    assert "<w:del " in xml and "<w:ins " in xml and "<w:b/>" in xml
    import re

    assert all(i.isdigit() for i in re.findall(r'<w:(?:ins|del) w:id="([^"]+)"', xml))


def test_signature_fills_recipient_only():
    doc = [
        "IN WITNESS WHEREOF",
        "DISCLOSER: Acme",
        "By: Pat Lee",
        "Title: CEO",
        "RECIPIENT:",
        "By: ______",
        "Title: ______",
    ]
    changes, _ = plan_changes(doc, [RULES[3]], FIRM, None)
    new = {c["paragraph_index"]: c["new_text"] for c in changes}
    assert (
        2 not in new
        and new[5] == "By: Jordan Ellis"
        and new[6] == "Title: Managing Partner"
    )
    assert new[4] == "RECIPIENT: Halden Capital LLC"
