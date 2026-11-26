"""Harder NDAs that look like real-world Word files.

Each document is a list of blocks:
  "text"                                   plain paragraph
  {"p": [seg, ...], "style": ..., "frag": True}
      seg: "text" | {"t": "text", "b": 1, "i": 1}
           | {"ins": "text"}  prior tracked insertion by the counterparty
           | {"del": "text"}  prior tracked deletion by the counterparty
      frag: split every segment into small runs, the way Word fragments text
  {"table": [[cell, ...], ...], "merge": [(row, col_from, col_to)]}

Each document lists explicit checks instead of one per rule:
  {"rule": name, "find": text in the ORIGINAL paragraph, "expect": "change"|"keep",
   "any_of": [...], "all_of": [...], "absent": [...]}
"find" matches the paragraph's original text (deleted text included, insertions excluded),
so a check still finds its paragraph after it has been redlined.
"""

import random

from docx import Document
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

FILLER = [
    "The parties shall cooperate in good faith to give effect to the intent of this Section.",
    "Any failure to enforce a provision of this Agreement is not a waiver of that provision or of the right to enforce it later.",
    "Headings are for convenience only and do not affect the interpretation of this Agreement.",
    "The word 'including' means 'including without limitation' wherever it appears in this Agreement.",
    "Each party shall bear its own costs incurred in connection with the negotiation of this Agreement.",
    "No party shall issue any press release concerning the Purpose without the prior written consent of the other party.",
    "References to a statute include that statute as amended or re-enacted from time to time.",
    "This Agreement does not create any agency, partnership or joint venture between the parties.",
]


# --------------------------------------------------------------------------- builder
_IDS = iter(range(5000, 10**6))


def _tracked(p, tag, text, rng):
    el = OxmlElement(tag)
    el.set(qn("w:id"), str(next(_IDS)))
    el.set(qn("w:author"), "Counterparty Counsel")
    el.set(qn("w:date"), "2026-10-01T10:00:00Z")
    r = OxmlElement("w:r")
    t = OxmlElement("w:delText" if tag == "w:del" else "w:t")
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    r.append(t)
    el.append(r)
    p._p.append(el)


def _add_segments(p, segs, frag, rng):
    for seg in segs:
        if isinstance(seg, str):
            seg = {"t": seg}
        if "ins" in seg:
            _tracked(p, "w:ins", seg["ins"], rng)
            continue
        if "del" in seg:
            _tracked(p, "w:del", seg["del"], rng)
            continue
        text = seg["t"]
        pieces = [text]
        if frag and len(text) > 6:
            cuts = sorted(
                rng.sample(
                    range(1, len(text)), k=min(len(text) - 1, max(1, len(text) // 9))
                )
            )
            pieces = [
                text[a:b] for a, b in zip([0] + cuts, cuts + [len(text)], strict=True)
            ]
        for piece in pieces:
            run = p.add_run(piece)
            run.bold = bool(seg.get("b"))
            run.italic = bool(seg.get("i"))


def build(nda: dict, path):
    rng = random.Random(nda["id"])
    doc = Document()
    for block in nda["blocks"]:
        if isinstance(block, str):
            doc.add_paragraph(block)
        elif "p" in block:
            p = doc.add_paragraph(style=block.get("style"))
            _add_segments(p, block["p"], block.get("frag"), rng)
        elif "table" in block:
            rows = block["table"]
            t = doc.add_table(rows=len(rows), cols=max(len(r) for r in rows))
            for r, row in enumerate(rows):
                for c, text in enumerate(row):
                    lines = text.split("\n")
                    cell = t.cell(r, c)
                    cell.text = lines[0]
                    for extra in lines[1:]:
                        cell.add_paragraph(extra)
            for r, c1, c2 in block.get("merge", []):
                t.cell(r, c1).merge(t.cell(r, c2))
        elif "pagebreak" in block:
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    doc.save(path)


def visible_paragraphs(nda: dict) -> list[str]:
    """Paragraph text as a reader sees it in the input (prior deletions hidden)."""
    out = []
    for block in nda["blocks"]:
        if isinstance(block, str):
            out.append(block)
        elif "p" in block:
            out.append(
                "".join(
                    s if isinstance(s, str) else s.get("t", s.get("ins", ""))
                    for s in block["p"]
                )
            )
        elif "table" in block:
            for row in block["table"]:
                for cell in row:
                    out.extend(cell.split("\n"))
    return out


def original_paragraphs(nda: dict) -> list[str]:
    """Paragraph text with prior deletions included and prior insertions excluded,
    matching how the scorer reads 'original' text from an output file."""
    out = []
    for block in nda["blocks"]:
        if isinstance(block, str):
            out.append(block)
        elif "p" in block:
            out.append(
                "".join(
                    s if isinstance(s, str) else s.get("t", s.get("del", ""))
                    for s in block["p"]
                )
            )
        elif "table" in block:
            for row in block["table"]:
                for cell in row:
                    out.extend(cell.split("\n"))
    return out


def filler(n, start, frag=True):
    return [
        {
            "p": [
                f"{start + i}. "
                + FILLER[i % len(FILLER)]
                + " "
                + FILLER[(i * 3 + 1) % len(FILLER)]
            ],
            "frag": frag,
        }
        for i in range(n)
    ]


# --------------------------------------------------------------------------- documents
CX1 = {
    "id": "CX1_long_defined_terms_prior_redlines",
    "description": (
        "~11 pages. Definitions article; 'Term' defined as an anniversary; survival in words only "
        "('five years'); a definition mentioning 'five (5) years before'; trade-secret survival; "
        "counterparty's earlier tracked changes; fragmented runs; notice block with blanks; "
        "signature table with tabs, a merged header row and a placeholder party name."
    ),
    "blocks": [
        {"p": [{"t": "MUTUAL NONDISCLOSURE AGREEMENT", "b": 1}]},
        {
            "p": [
                "This Mutual Nondisclosure Agreement (this “Agreement”) is entered into as of November 2, 2026 "
                "(the “Effective Date”) by and between Northwind Robotics, Inc., a Delaware corporation "
                "(“Northwind”), and [RECIPIENT NAME] (“Counterparty”). Each of Northwind and "
                "Counterparty is a “Party”."
            ],
            "frag": True,
        },
        {"p": [{"t": "ARTICLE 1. DEFINITIONS", "b": 1}]},
        {
            "p": [
                "1.1 “Affiliate” means any entity controlling, controlled by or under common control with a Party."
            ],
            "frag": True,
        },
        {
            "p": [
                "1.2 “Confidential Information” means all non-public information disclosed by or on behalf of a "
                "Party, including information disclosed during the five (5) years before the Effective Date in "
                "connection with the Purpose."
            ],
            "frag": True,
        },
        {
            "p": [
                "1.3 “Representatives” means, with respect to a Party, such Party’s Affiliates and its and their "
                "respective directors, officers, managers, employees, attorneys, accountants and consultants (but "
                "excluding any of the foregoing who are not actually provided Confidential Information)."
            ],
            "frag": True,
        },
        {
            "p": [
                "1.4 “Term” means the period beginning on the Effective Date and ending on the third (3rd) "
                "anniversary thereof."
            ],
            "frag": True,
        },
        {
            "p": [
                "1.5 “Purpose” means the evaluation of a potential commercial collaboration between the Parties."
            ]
        },
        {"p": [{"t": "ARTICLE 2. OBLIGATIONS", "b": 1}]},
        *filler(40, 201),
        {
            "p": [
                "2.41 Each Party shall notify the other Party ",
                {"del": "promptly"},
                {"ins": "within five (5) business days"},
                " after becoming aware of any unauthorized use or disclosure of Confidential Information.",
            ],
            "frag": False,
        },
        {"p": [{"t": "ARTICLE 5. RETURN OF CONFIDENTIAL INFORMATION", "b": 1}]},
        {
            "p": [
                "5.1 Upon the Disclosing Party’s written request, the Receiving Party shall, within fifteen (15) "
                "days, (a) return or destroy all Confidential Information; and (b) upon request, certify such return "
                "or destruction in writing."
            ],
            "frag": True,
        },
        {
            "p": [
                "5.2 Notwithstanding Section 5.1, the Receiving Party shall not be required to destroy Confidential "
                "Information that is subject to a legal hold until the hold is released."
            ],
            "frag": True,
        },
        *filler(40, 601),
        {"p": [{"t": "ARTICLE 7. TERM AND SURVIVAL", "b": 1}]},
        {
            "p": [
                "7.1 This Agreement shall remain in effect during the Term. Sections 3 through 6 survive any expiration "
                "or termination of this Agreement for a period of five years."
            ],
            "frag": True,
        },
        {
            "p": [
                "7.2 With respect to any trade secret, the obligations of this Agreement survive for so long as such "
                "information remains a trade secret under applicable law."
            ],
            "frag": True,
        },
        {"p": [{"t": "ARTICLE 10. NOTICES", "b": 1}]},
        "10.1 Notices must be in writing and sent to the addresses below.",
        "If to Northwind: 1 Harbor Way, Boston, MA 02110, Attention: General Counsel",
        "If to Counterparty:",
        "Attention: ____________________",
        "Email: ____________________",
        *filler(30, 1003),
        "IN WITNESS WHEREOF, the Parties have executed this Agreement as of the Effective Date.",
        {
            "table": [
                ["SIGNATURES", "SIGNATURES"],
                ["NORTHWIND ROBOTICS, INC.", "[RECIPIENT NAME]"],
                ["By:\tAvery Castellanos", "By:\t____________________"],
                ["Name:\tAvery Castellanos", "Name:\t____________________"],
                ["Title:\tChief Executive Officer", "Title:\t____________________"],
                ["Date:\tNovember 2, 2026", "Date:\t____________________"],
            ],
            "merge": [(0, 0, 1)],
        },
    ],
    "checks": [
        {
            "rule": "term",
            "find": "1.4 “Term” means",
            "expect": "change",
            "any_of": ["second (2nd) anniversary", "two (2) years", "2nd anniversary"],
            "absent": ["third (3rd)"],
        },
        {
            "rule": "term",
            "find": "7.1 This Agreement shall remain",
            "expect": "change",
            "any_of": ["two (2) years", "two years"],
            "absent": ["five years"],
        },
        {"rule": "term", "find": "1.2 “Confidential Information”", "expect": "keep"},
        {
            "rule": "term",
            "find": "7.2 With respect to any trade secret",
            "expect": "keep",
        },
        {
            "rule": "reps",
            "find": "1.3 “Representatives”",
            "expect": "change",
            "all_of": [
                "investor",
                "agent",
                "advis",
                "financing",
                "(but excluding any of the foregoing",
            ],
            "order": ["investor", "(but excluding"],
        },
        {
            "rule": "retain",
            "find": "5.1 Upon the Disclosing Party",
            "expect": "change",
            "all_of": ["retention polic"],
            "or_next": True,
        },
        {
            "rule": "sign",
            "find": "[RECIPIENT NAME]",
            "expect": "change",
            "all_of": ["Halden Capital LLC"],
            "last": True,
        },
        {
            "rule": "sign",
            "find": "Name:\t____",
            "expect": "change",
            "all_of": ["Jordan Ellis"],
        },
        {
            "rule": "sign",
            "find": "Title:\t____",
            "expect": "change",
            "all_of": ["Managing Partner"],
        },
        {"rule": "sign", "find": "By:\tAvery Castellanos", "expect": "keep"},
        {"rule": "collateral", "find": "Attention: ____", "expect": "keep"},
        {"rule": "collateral", "find": "Email: ____", "expect": "keep"},
        {
            "rule": "collateral",
            "find": "2.41 Each Party shall notify",
            "expect": "keep",
        },
        {"rule": "collateral", "find": "Date:\t____", "expect": "keep"},
    ],
}

CX2 = {
    "id": "CX2_three_party_two_rep_definitions",
    "description": (
        "Three signing parties (the third, a financial advisor, also has a blank block); two different "
        "Representatives definitions; 18-month term with a 36-month survival tail; an existing archival-copy "
        "right; placeholder recipient name '[●]'."
    ),
    "blocks": [
        "CONFIDENTIALITY AND NON-USE AGREEMENT",
        "This Agreement is made among Tern Medical, Inc. (“Discloser”), [●] (“Recipient”) and "
        "Halyard Partners LLC, financial advisor to Discloser (“Advisor”).",
        "1. “Discloser Representatives” means Discloser’s directors, officers and employees.",
        "2. “Recipient Representatives” or “Representatives” means Recipient’s directors, officers, "
        "employees and outside legal counsel.",
        "3. Recipient shall hold Evaluation Material in confidence and use it only to evaluate the Transaction.",
        "4. This Agreement shall terminate eighteen (18) months after the date hereof; provided that the "
        "confidentiality obligations in Section 3 shall survive for thirty-six (36) months after termination.",
        "5. Upon Discloser’s request, Recipient shall return or destroy all Evaluation Material, except that "
        "Recipient’s legal department may keep one archival copy solely to monitor compliance.",
        "6. Advisor is a party solely for the purpose of Section 7. 7. Advisor will direct all inquiries from Recipient.",
        *[f"{8 + i}. " + FILLER[i % len(FILLER)] for i in range(10)],
        "IN WITNESS WHEREOF, the parties have signed this Agreement.",
        "DISCLOSER: Tern Medical, Inc.",
        "By: Anne Cho",
        "Title: Chief Executive Officer",
        "RECIPIENT: [●]",
        "By: ____________________",
        "Name: ____________________",
        "Title: ____________________",
        "ADVISOR: Halyard Partners LLC",
        "By: ____________________",
        "Name: ____________________",
        "Title: ____________________",
    ],
    "checks": [
        {
            "rule": "term",
            "find": "4. This Agreement shall terminate",
            "expect": "change",
            "all_of": ["eighteen (18) months", "two (2) years after termination"],
            "absent": ["thirty-six"],
        },
        {
            "rule": "reps",
            "find": "2. “Recipient Representatives”",
            "expect": "change",
            "all_of": [
                "investor",
                "agent",
                "advis",
                "financing",
                "outside legal counsel",
            ],
        },
        {"rule": "reps", "find": "1. “Discloser Representatives”", "expect": "keep"},
        {"rule": "retain", "find": "5. Upon Discloser", "expect": "keep"},
        {
            "rule": "sign",
            "find": "RECIPIENT: [●]",
            "expect": "change",
            "all_of": ["Halden Capital LLC"],
            "absent": ["[●]"],
        },
        {
            "rule": "sign",
            "find": "Name: ____",
            "expect": "change",
            "all_of": ["Jordan Ellis"],
            "nth": 0,
        },
        {
            "rule": "sign",
            "find": "Title: ____",
            "expect": "change",
            "all_of": ["Managing Partner"],
            "nth": 0,
        },
        {"rule": "sign", "find": "Name: ____", "expect": "keep", "nth": 1},
        {"rule": "sign", "find": "Title: ____", "expect": "keep", "nth": 1},
        {"rule": "sign", "find": "By: ____", "expect": "keep", "nth": 1},
        {
            "rule": "collateral",
            "find": "This Agreement is made among",
            "expect": "keep",
        },
    ],
}

CX3 = {
    "id": "CX3_already_good_many_durations",
    "description": (
        "Already compliant everywhere and already signed by a different person, but full of other durations "
        "(record keeping, standstill, notice, audit) that must not be capped. Tests over-redlining."
    ),
    "blocks": [
        "NON-DISCLOSURE AGREEMENT",
        "Quarry Analytics Corp. (“Company”) and the undersigned (“Recipient”) agree as follows.",
        "1. “Representatives” means Recipient’s affiliates, directors, officers, employees, investors, agents, "
        "advisors and potential debt and equity financing sources.",
        "2. Recipient’s obligations under this Agreement terminate two (2) years from the date hereof.",
        "3. Recipient shall maintain records of all persons to whom Confidential Information is disclosed for five (5) "
        "years after the date of disclosure.",
        "4. For a period of three (3) years following the date hereof, Recipient shall not acquire any voting securities of Company.",
        "5. Company may audit Recipient’s compliance once in any twelve (12) month period on thirty (30) days’ notice.",
        "6. On request Recipient will return or destroy Confidential Information, except that Recipient’s outside "
        "counsel may keep one copy for archival purposes.",
        "7. Recipient shall preserve all Confidential Information subject to litigation holds for the duration of any "
        "proceeding, which may exceed four (4) years.",
        "IN WITNESS WHEREOF:",
        "QUARRY ANALYTICS CORP.",
        "By: Lena Ortiz",
        "Title: President",
        "RECIPIENT",
        "Company: Brightline Capital Partners LP",
        "By: Harper Quinn",
        "Title: Principal",
    ],
    "checks": [
        {"rule": "term", "find": "2. Recipient’s obligations", "expect": "keep"},
        {
            "rule": "term",
            "find": "3. Recipient shall maintain records",
            "expect": "keep",
        },
        {"rule": "term", "find": "4. For a period of three", "expect": "keep"},
        {"rule": "term", "find": "5. Company may audit", "expect": "keep"},
        {"rule": "term", "find": "7. Recipient shall preserve", "expect": "keep"},
        {"rule": "reps", "find": "1. “Representatives”", "expect": "keep"},
        {"rule": "retain", "find": "6. On request", "expect": "keep"},
        {"rule": "sign", "find": "Company: Brightline", "expect": "keep"},
        {"rule": "sign", "find": "By: Harper Quinn", "expect": "keep"},
        {"rule": "sign", "find": "Title: Principal", "expect": "keep"},
    ],
}


def _long_blocks():
    blocks = [
        {"p": [{"t": "MASTER CONFIDENTIALITY AGREEMENT", "b": 1}]},
        "This Master Confidentiality Agreement is between Osprey Grid Systems Inc. (“Osprey”) and the Recipient named below.",
    ]
    blocks += filler(260, 1)
    blocks.append(
        {
            "p": [
                "261. “Representatives” means the Recipient’s officers and employees."
            ],
            "frag": True,
        }
    )
    blocks += filler(260, 262)
    blocks.append(
        {
            "p": [
                "523. Upon request the Recipient shall destroy all Confidential Information."
            ],
            "frag": True,
        }
    )
    blocks += filler(60, 524)
    blocks.append(
        {
            "p": [
                "584. The Recipient’s obligations shall survive for a period of sixty (60) months."
            ],
            "frag": True,
        }
    )
    blocks += [
        "IN WITNESS WHEREOF:",
        "OSPREY GRID SYSTEMS INC.",
        "By: Priya Raman",
        "RECIPIENT:",
        "By: ________",
        "Title: ________",
    ]
    return blocks


CX4 = {
    "id": "CX4_30_pages",
    "description": "About 30 pages and 600 paragraphs of fragmented text; the clauses that matter are on pages 13, 26 and 29. Tests speed and that nothing else moves.",
    "blocks": _long_blocks(),
    "checks": [
        {
            "rule": "term",
            "find": "584. The Recipient",
            "expect": "change",
            "all_of": ["two (2) years"],
            "absent": ["sixty"],
        },
        {
            "rule": "reps",
            "find": "261. “Representatives”",
            "expect": "change",
            "all_of": ["investor", "agent", "advis", "financing"],
        },
        {
            "rule": "retain",
            "find": "523. Upon request",
            "expect": "change",
            "all_of": ["retention polic"],
        },
        {
            "rule": "sign",
            "find": "RECIPIENT:",
            "expect": "change",
            "all_of": ["Halden Capital LLC"],
        },
        {
            "rule": "sign",
            "find": "By: ________",
            "expect": "change",
            "all_of": ["Jordan Ellis"],
        },
        {
            "rule": "sign",
            "find": "Title: ________",
            "expect": "change",
            "all_of": ["Managing Partner"],
        },
    ],
}

COMPLEX = [CX1, CX2, CX3, CX4]


# ---------------------------------------------------------------------------
# Second blind round: written after the fixes above, run once without tuning.
def _cell_block(lines):
    return "\n".join(lines)


CY1 = {
    "id": "CY1_defined_period_roman_list_accepted_block",
    "description": (
        "'Confidentiality Period' defined as four years; Representatives as a (i)/(ii)/(iii) list; return "
        "clause under its own bold heading; recipient signs first under 'ACCEPTED AND AGREED' with an "
        "'Entity:' line; numbering from a Word list style."
    ),
    "blocks": [
        {"p": [{"t": "CONFIDENTIALITY AGREEMENT", "b": 1}]},
        "Marlow Instruments plc (“Marlow”) and the entity accepting below (“Recipient”) agree:",
        {
            "p": [
                "“Confidentiality Period” means the period commencing on the Effective Date and continuing until "
                "the date that is four (4) years after the Effective Date."
            ],
            "style": "List Number",
            "frag": True,
        },
        {
            "p": [
                "“Representatives” shall include a party’s: (i) affiliates; (ii) directors and officers; and "
                "(iii) employees."
            ],
            "style": "List Number",
            "frag": True,
        },
        {
            "p": [
                "During the Confidentiality Period, Recipient shall not disclose Confidential Information except to its "
                "Representatives."
            ],
            "style": "List Number",
        },
        {"p": [{"t": "Return of Materials", "b": 1}]},
        {
            "p": [
                "Upon the written request of Marlow, Recipient shall return or destroy all Confidential Information and "
                "all copies thereof."
            ],
            "style": "List Number",
            "frag": True,
        },
        {
            "p": [
                "Recipient represents that it has not, in the preceding three (3) years, been subject to any "
                "regulatory sanction."
            ],
            "style": "List Number",
        },
        "ACCEPTED AND AGREED:",
        "Entity: ____________________",
        "Signature: ____________________",
        "Printed Name: ____________________",
        "Title: ____________________",
        "MARLOW INSTRUMENTS PLC",
        "Signature: /s/ Rhys Bevan",
        "Printed Name: Rhys Bevan",
        "Title: Company Secretary",
    ],
    "checks": [
        {
            "rule": "term",
            "find": "“Confidentiality Period” means",
            "expect": "change",
            "all_of": ["two (2) years"],
            "absent": ["four (4) years"],
        },
        {
            "rule": "term",
            "find": "Recipient represents that it has not",
            "expect": "keep",
        },
        {
            "rule": "reps",
            "find": "“Representatives” shall include",
            "expect": "change",
            "all_of": ["investor", "agent", "advis", "financing", "(iii) employees"],
            "order": ["(iii) employees", "investor"],
        },
        {
            "rule": "retain",
            "find": "Upon the written request of Marlow",
            "expect": "change",
            "all_of": ["retention polic"],
        },
        {"rule": "retain", "find": "Return of Materials", "expect": "keep"},
        {
            "rule": "sign",
            "find": "Entity: ____",
            "expect": "change",
            "all_of": ["Halden Capital LLC"],
        },
        {
            "rule": "sign",
            "find": "Printed Name: ____",
            "expect": "change",
            "all_of": ["Jordan Ellis"],
        },
        {
            "rule": "sign",
            "find": "Title: ____",
            "expect": "change",
            "all_of": ["Managing Partner"],
        },
        {"rule": "sign", "find": "Signature: ____", "expect": "keep"},
        {"rule": "sign", "find": "Printed Name: Rhys Bevan", "expect": "keep"},
    ],
}

CY2 = {
    "id": "CY2_earlier_of_mixed_survival_cell_blocks",
    "description": (
        "Term as 'the earlier of (a) ... and (b) thirty (30) months'; mixed survival periods in one sentence; "
        "'preceding three (3) years' representation; capitalised 'Financing Sources' already listed; retention "
        "policy already allowed; each party's signature block is several paragraphs inside one table cell."
    ),
    "blocks": [
        "MUTUAL NONDISCLOSURE AGREEMENT",
        "Kestrel Labs, Inc. (“Kestrel”) and the Recipient identified below enter into this Agreement.",
        "1. “Representatives” means a party’s officers, directors and employees and, solely with respect to "
        "the Recipient, its Financing Sources.",
        "2. This Agreement terminates on the earlier of (a) the consummation of the Transaction and (b) the date that "
        "is thirty (30) months after the date hereof.",
        "3. Sections 4 and 5 shall survive termination for three (3) years; Section 7 (Non-Solicitation) shall survive "
        "for one (1) year.",
        "4. The Recipient has not, in the preceding three (3) years, been a party to litigation with Kestrel.",
        "5. Upon request, the Recipient shall return or destroy Confidential Information, except as required to comply "
        "with applicable law, regulation or bona fide internal document retention policies.",
        "IN WITNESS WHEREOF, the parties have executed this Agreement.",
        {
            "table": [
                [
                    _cell_block(
                        [
                            "KESTREL LABS, INC.",
                            "By: Omar Haddad",
                            "Name: Omar Haddad",
                            "Title: CFO",
                        ]
                    ),
                    _cell_block(
                        [
                            "RECIPIENT",
                            "Company: ____________",
                            "By: ____________",
                            "Name: ____________",
                            "Title: ____________",
                        ]
                    ),
                ]
            ]
        },
    ],
    "checks": [
        {
            "rule": "term",
            "find": "2. This Agreement terminates",
            "expect": "change",
            "all_of": ["two (2) years", "earlier of"],
            "absent": ["thirty (30) months"],
        },
        {
            "rule": "term",
            "find": "3. Sections 4 and 5",
            "expect": "change",
            "all_of": ["two (2) years", "one (1) year"],
            "absent": ["three (3) years"],
        },
        {"rule": "term", "find": "4. The Recipient has not", "expect": "keep"},
        {
            "rule": "reps",
            "find": "1. “Representatives”",
            "expect": "change",
            "all_of": ["investor", "agent", "advis", "Financing Sources"],
        },
        {"rule": "retain", "find": "5. Upon request", "expect": "keep"},
        {"rule": "sign", "find": "RECIPIENT", "expect": "keep", "last": True},
        {
            "rule": "sign",
            "find": "Company: ____",
            "expect": "change",
            "all_of": ["Halden Capital LLC"],
        },
        {
            "rule": "sign",
            "find": "Name: ____",
            "expect": "change",
            "all_of": ["Jordan Ellis"],
        },
        {
            "rule": "sign",
            "find": "Title: ____",
            "expect": "change",
            "all_of": ["Managing Partner"],
        },
        {"rule": "sign", "find": "By: Omar Haddad", "expect": "keep"},
    ],
}

CY3 = {
    "id": "CY3_nbsp_hyphenated_inline_signature",
    "description": (
        "Non-breaking spaces and curly quotes; 'a five (5)-year period'; a one-line signature "
        "('Signed by ____ for and on behalf of ____'); em dashes."
    ),
    "blocks": [
        "Non-Disclosure Undertaking — Project Larch",
        "The Recipient agrees to keep the Information confidential for a five (5)-year period from the date of "
        "this undertaking — and to use it only for Project Larch.",
        "The Recipient may share the Information with its directors and professional advisers (its "
        "“Representatives”).",
        "On written demand the Recipient shall destroy all Information within ten (10) days.",
        "Signed by ____________________ for and on behalf of ____________________ (the Recipient)",
        "Date: ____________________",
    ],
    "checks": [
        {
            "rule": "term",
            "find": "The Recipient agrees to keep",
            "expect": "change",
            "all_of": ["two"],
            "absent": ["five"],
        },
        {
            "rule": "reps",
            "find": "The Recipient may share",
            "expect": "change",
            "all_of": ["investor", "agent", "advis", "financing"],
        },
        {
            "rule": "retain",
            "find": "On written demand",
            "expect": "change",
            "all_of": ["retention polic"],
        },
        {
            "rule": "sign",
            "find": "Signed by ____",
            "expect": "change",
            "all_of": ["Jordan Ellis", "Halden Capital LLC"],
        },
        {"rule": "collateral", "find": "Date: ____", "expect": "keep"},
    ],
}

COMPLEX_BLIND2 = [CY1, CY2, CY3]
