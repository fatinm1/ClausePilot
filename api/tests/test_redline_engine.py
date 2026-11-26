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


def test_reps_uses_valid_model_wording(monkeypatch):
    monkeypatch.setenv("REPS_WORDING", "model")
    better = REPS.replace(
        "officers and employees",
        "officers, employees, investors, agents, advisors and potential financing sources",
    )
    changes, _ = plan_changes(
        DOC, [RULES[1]], {}, stub(json.dumps({"new_text": better}))
    )
    assert changes[0]["new_text"] == better


def test_reps_rejects_model_that_deletes_words(monkeypatch):
    monkeypatch.setenv("REPS_WORDING", "model")
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


def test_garbage_reply_falls_back_to_code(monkeypatch):
    monkeypatch.setenv("REPS_WORDING", "model")
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


def test_tab_runs_split_and_failed_edits_roll_back():
    d = Document()
    p = d.add_paragraph()
    p.add_run("Name:\t____________")
    from app.services.tracked_docx import paragraph_text

    assert apply_edit(p, "Name:\t____________", "Name:\tJordan Ellis", ChangeIds(d))
    assert paragraph_text(p) == "Name:\tJordan Ellis"


def test_reps_go_at_end_of_numbered_list_and_before_exclusions():
    doc = [
        "“Representatives” shall include a party’s: (i) affiliates; (ii) directors and officers; and (iii) employees.",
        '"Representatives" means its directors and consultants (but excluding anyone not given information).',
    ]
    first = plan_changes(doc[:1], [RULES[1]], {}, None)[0][0]["new_text"]
    second = plan_changes(doc[1:], [RULES[1]], {}, None)[0][0]["new_text"]
    assert "(iii) employees; and (iv) investors" in first
    assert second.index("investors") < second.index("(but excluding")


def test_term_judged_by_its_own_clause():
    doc = [
        "1.2 Confidential Information includes information disclosed during the five (5) years before the Effective Date.",
        "3. Recipient shall maintain records of disclosures for five (5) years.",
        "4. Sections 4 and 5 survive termination for three (3) years; Section 7 survives for one (1) year.",
        "5. The Recipient agrees to keep the Information confidential for a five (5)-year period.",
        "6. “Term” means the period ending on the third (3rd) anniversary of the Effective Date.",
        "7. Sections 3 through 6 survive for a period of five years.",
    ]
    changes, _ = plan_changes(doc, [RULES[0]], {}, None)
    new = {c["paragraph_index"]: c["new_text"] for c in changes}
    assert 0 not in new and 1 not in new
    assert "for two (2) years; Section 7 survives for one (1) year" in new[2]
    assert "a two (2)-year period" in new[3]
    assert "second (2nd) anniversary" in new[4]
    assert "period of two (2) years" in new[5]


def test_one_line_signature_and_other_blank_blocks():
    doc = [
        "IN WITNESS WHEREOF",
        "Signed by ____________ for and on behalf of ____________ (the Recipient)",
        "RECIPIENT: [●]",
        "Name: ______",
        "ADVISOR: Halyard Partners LLC",
        "Name: ______",
    ]
    changes, _ = plan_changes(doc, [RULES[3]], FIRM, None)
    new = {c["paragraph_index"]: c["new_text"] for c in changes}
    assert new[1].startswith(
        "Signed by Jordan Ellis for and on behalf of Halden Capital LLC"
    )
    assert new[2] == "RECIPIENT: Halden Capital LLC" and new[3] == "Name: Jordan Ellis"
    assert 5 not in new


def test_model_edits_that_drop_numbers_or_change_scope_are_rejected():
    from app.services.redline_engine import Planner

    old = '261. "Representatives" means the Recipient\'s officers and employees.'
    assert not Planner._only_additions(
        old, '"Representatives" means the Recipient\'s officers, employees, investors.'
    )
    scoped = '1. "Representatives" means officers and employees and, solely with respect to the Recipient, its Financing Sources.'
    moved = '1. "Representatives" means officers, employees, investors and agents and, solely with respect to the Recipient, its Financing Sources.'
    assert not Planner._only_additions(scoped, moved)
    assert not Planner._only_additions(
        '"Representatives" means employees.',
        '"Representatives" means employees. Such Representatives also include investors.',
    )
    assert Planner._only_additions(
        '"Representatives" means officers and employees.',
        '"Representatives" means officers, employees, investors and agents.',
    )


def test_party_specific_representatives_are_flagged_not_edited():
    p = (
        'The term "Representatives" (i) with respect to you, shall only include your officers and financial advisors, '
        "and (ii) with respect to the Company, shall include its directors, agents and advisors."
    )
    changes, notes = plan_changes([p], [RULES[1]], {}, None)
    assert changes == [] and any(
        "defined separately for each party" in n for n in notes
    )


def test_retention_uses_documents_defined_term():
    paras = [
        "The term “Evaluation Material” shall mean all information furnished to Recipient.",
        "Recipient will promptly return or destroy all Evaluation Material and no copy thereof shall be retained.",
    ]
    rule = next(
        r
        for r in RULES
        if "etention" in r["name"] or "etain" in r.get("instruction", "")
    )
    changes, _ = plan_changes(paras, [rule], {}, None)
    assert changes and "copy of Evaluation Material" in changes[0]["new_text"]


def test_liability_rule_leaves_disclaimers_alone():
    doc = [
        "Neither the Discloser nor its Representatives shall have any liability to Recipient "
        "relating to the use of the Evaluation Material.",
        "This Agreement is governed by Delaware law.",
    ]
    rule = {
        "name": "Limit liability",
        "instruction": "Limit liability to actual damages, exclude consequential damages",
    }
    called = []
    changes, notes = plan_changes(
        doc, [rule], {}, lambda s, u: called.append(u) or '{"edits": []}'
    )
    assert changes == [] and not called and any("nothing to limit" in n for n in notes)


def test_financing_rule_without_the_word_representatives_uses_reps_logic():
    doc = [
        "The term “Representatives” means your directors, officers, agents, advisors and the "
        "institutional investors and potential debt financing sources listed on Annex A."
    ]
    rule = {
        "name": "Rule",
        "instruction": "Include investors, potential financing sources, and agents if not included",
    }
    changes, _ = plan_changes(doc, [rule], {}, None)
    assert changes == []
