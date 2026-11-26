"""Synthetic NDAs for the redlining evaluation.

Every document, party and person here is invented for testing. Each NDA comes
with the outcome a careful reviewer would expect for each of the four standard
rules, so the output .docx can be scored automatically.
"""

# Same keys the web app sends (FirmDetails in web/lib/api.ts)
FIRM = {
    "name": "Halden Capital LLC",
    "address": "200 Pratt Street, Suite 900",
    "city": "Baltimore",
    "state": "MD",
    "zipCode": "21202",
    "signerName": "Jordan Ellis",
    "signerTitle": "Managing Partner",
}

RULES = [
    {
        "id": 1,
        "name": "Cap the confidentiality term",
        "category": "term",
        "instruction": (
            "If the confidentiality obligations or the term of the agreement last longer "
            "than two (2) years (or are perpetual), replace that period with two (2) years. "
            "If the period is already two years or less, make no change."
        ),
    },
    {
        "id": 2,
        "name": "Widen Representatives",
        "category": "parties",
        "instruction": (
            "Ensure the definition of Representatives includes the Recipient's investors, "
            "agents, advisors and potential financing sources. Add only the missing "
            "categories; do not change anything else in the definition."
        ),
    },
    {
        "id": 3,
        "name": "Retention carve-out",
        "category": "return",
        "instruction": (
            "After the clause requiring return or destruction of Confidential Information, "
            "add: 'Notwithstanding the foregoing, Recipient may retain an electronic copy of "
            "Confidential Information if required under Recipient's document retention "
            "policy, provided that such retained materials remain subject to the "
            "confidentiality obligations set forth herein.' Do not add it if an equivalent "
            "retention right already exists."
        ),
    },
    {
        "id": 4,
        "name": "Signature block",
        "category": "signature",
        "instruction": (
            "Fill the Recipient's signature block with the firm name, signer name and "
            "title from the firm details. Do not add new signature lines."
        ),
    },
]

FILLER = [
    "No License. Nothing in this Agreement grants the Recipient any right or license "
    "under any patent, copyright, trade secret or other intellectual property right of "
    "the Discloser, except the limited right to use Confidential Information for the Purpose.",
    'No Warranty. All Confidential Information is provided "AS IS". The Discloser makes no '
    "representation or warranty as to the accuracy or completeness of any Confidential Information.",
    "Compelled Disclosure. If the Recipient is required by law, regulation or legal process to "
    "disclose any Confidential Information, it shall give the Discloser prompt written notice "
    "so that the Discloser may seek a protective order, and shall disclose only the portion "
    "legally required.",
    "Remedies. The Recipient acknowledges that unauthorized disclosure may cause irreparable "
    "harm for which monetary damages would be inadequate, and that the Discloser shall be "
    "entitled to seek equitable relief in addition to any other remedy.",
    "Non-Solicitation. For twelve (12) months after the date hereof, the Recipient shall not "
    "solicit for employment any employee of the Discloser with whom it had contact in "
    "connection with the Purpose, provided that general solicitations shall not breach this section.",
    "Governing Law. This Agreement shall be governed by the laws of the State of Delaware, "
    "without regard to its conflict of laws principles.",
    "Entire Agreement. This Agreement is the entire agreement between the parties on its "
    "subject matter and supersedes all prior discussions. It may be amended only in a writing "
    "signed by both parties.",
    "Assignment. Neither party may assign this Agreement without the prior written consent of "
    "the other party, except to a successor to all or substantially all of its business.",
    "Notices. All notices under this Agreement shall be in writing and delivered by hand, "
    "nationally recognised courier or email with confirmation of receipt.",
    "Counterparts. This Agreement may be executed in counterparts, each of which is an "
    "original and all of which together are one instrument. Electronic signatures are binding.",
    "Standstill. For a period of twelve (12) months, the Recipient shall not acquire any "
    "securities of the Discloser without its prior written consent.",
    "Export Control. The Recipient shall comply with all applicable export control laws in "
    "its handling of any technical data included in the Confidential Information.",
]


def _sig(name="________________", title="________________", company="________________"):
    return [
        "IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.",
        "DISCLOSER: Northwind Robotics, Inc.",
        "By: Avery Castellanos",
        "Title: Chief Executive Officer",
        "RECIPIENT:",
        f"Company: {company}",
        f"By: {name}",
        f"Title: {title}",
    ]


NDAS = [
    {
        "id": "A_short_mutual",
        "description": "Short mutual NDA. Five-year term, narrow Representatives, no retention right, blank signature.",
        "paragraphs": [
            "MUTUAL NON-DISCLOSURE AGREEMENT",
            'This Mutual Non-Disclosure Agreement (the "Agreement") is entered into as of March 3, 2026 '
            'between Northwind Robotics, Inc. ("Northwind") and the Recipient named below, in connection '
            'with a possible investment in Northwind (the "Purpose").',
            '1. Confidential Information. "Confidential Information" means all non-public information '
            'disclosed by a party (the "Discloser") to the other party (the "Recipient"), whether oral, '
            "written or electronic, that is marked confidential or would reasonably be understood to be confidential.",
            '2. Representatives. "Representatives" means a party\'s affiliates, directors, officers and employees.',
            "3. Obligations. The Recipient shall use Confidential Information solely for the Purpose and shall "
            "not disclose it to anyone other than its Representatives who need to know it for the Purpose.",
            "4. Term. The obligations of the Recipient under this Agreement shall survive for a period of "
            "five (5) years from the date hereof.",
            "5. Return of Materials. Upon written request, the Recipient shall promptly return or destroy all "
            "Confidential Information in its possession.",
            FILLER[5],
            FILLER[6],
            *_sig(),
        ],
        "expect": {
            "term": "change",
            "reps": "change",
            "retain": "change",
            "sign": "change",
        },
        "term_old": "five (5) years",
        "reps_para": "2. Representatives.",
        "return_para": "5. Return of Materials.",
        "term_para": "4. Term.",
    },
    {
        "id": "B_long_oneway",
        "description": "Long one-way NDA (~2,000 words). Key clauses sit in the middle of the document.",
        "paragraphs": [
            "CONFIDENTIALITY AGREEMENT",
            'This Confidentiality Agreement (this "Agreement") is made as of June 14, 2026 by Northwind '
            'Robotics, Inc., a Delaware corporation (the "Discloser"), for the benefit of the recipient '
            'identified in the signature block (the "Recipient").',
            "Background. The Discloser is considering a strategic transaction and is prepared to make "
            "certain information available to the Recipient in connection with its evaluation of that "
            'transaction (the "Purpose"), on the terms of this Agreement.',
            *[f"{i + 1}. {FILLER[i % len(FILLER)]}" for i in range(0, 6)],
            '7. Definition of Confidential Information. "Confidential Information" includes all '
            "information, in any form, concerning the business, finances, technology, customers or "
            "employees of the Discloser that is furnished to the Recipient or its Representatives, "
            "together with all notes, analyses and compilations prepared by the Recipient that contain "
            "or reflect such information.",
            '8. Representatives. As used in this Agreement, "Representatives" means the Recipient\'s '
            "directors, officers, employees and professional advisors, including attorneys and accountants.",
            "9. Use and Disclosure. The Recipient shall hold Confidential Information in strict confidence, "
            "shall use it solely for the Purpose, and may disclose it only to those of its Representatives "
            "who need to know it, are informed of its confidential nature and agree to be bound by this Agreement.",
            *[f"{i + 4}. {FILLER[i % len(FILLER)]}" for i in range(6, 12)],
            "16. Return or Destruction. At any time upon the Discloser's request, the Recipient shall, at its "
            "election, return to the Discloser or destroy all Confidential Information and certify such "
            "destruction in writing within ten (10) business days.",
            "17. Duration. This Agreement and the Recipient's obligations hereunder shall remain in effect "
            "for three (3) years from the Effective Date.",
            *[f"{i + 12}. {FILLER[(i + 3) % len(FILLER)]}" for i in range(6, 12)],
            *_sig(),
        ],
        "expect": {
            "term": "change",
            "reps": "change",
            "retain": "change",
            "sign": "change",
        },
        "term_old": "three (3) years",
        "reps_para": "8. Representatives.",
        "return_para": "16. Return or Destruction.",
        "term_para": "17. Duration.",
    },
    {
        "id": "C_already_compliant",
        "description": "Already meets three rules: two-year term, full Representatives, retention right. Only the signature needs filling. Tests over-redlining.",
        "paragraphs": [
            "NON-DISCLOSURE AGREEMENT",
            'This Non-Disclosure Agreement (the "Agreement") dated September 9, 2026 is between '
            'Northwind Robotics, Inc. (the "Discloser") and the recipient named below (the "Recipient").',
            '1. Representatives. "Representatives" means the Recipient\'s affiliates, directors, officers, '
            "employees, investors, agents, advisors and potential financing sources.",
            "2. Obligations. The Recipient shall keep Confidential Information confidential and use it only "
            "to evaluate a possible business relationship with the Discloser.",
            "3. Term. The obligations in this Agreement shall continue for two (2) years from the date hereof.",
            "4. Return of Materials. Upon request, the Recipient shall return or destroy all Confidential "
            "Information, except that the Recipient may retain copies as required by its document retention "
            "policy or applicable law, which shall remain subject to this Agreement.",
            FILLER[0],
            FILLER[5],
            *_sig(),
        ],
        "expect": {"term": "keep", "reps": "keep", "retain": "keep", "sign": "change"},
        "term_old": "two (2) years",
        "reps_para": "1. Representatives.",
        "return_para": "4. Return of Materials.",
        "term_para": "3. Term.",
    },
    {
        "id": "D_months_and_perpetual",
        "description": "Unusual phrasing: term in months plus a perpetual trade-secret tail; Representatives under a different heading.",
        "paragraphs": [
            "NONDISCLOSURE AND CONFIDENTIALITY AGREEMENT",
            'Northwind Robotics, Inc. ("Company") and the undersigned recipient ("Recipient") agree as follows.',
            "1. Permitted Recipients. Recipient may share Evaluation Material only with its partners, "
            'members and employees (collectively, "Representatives") who need to know it.',
            "2. Confidentiality Period. Recipient's obligations shall last for a period of thirty-six (36) "
            "months after the date of this Agreement; provided that obligations with respect to trade "
            "secrets shall survive in perpetuity.",
            "3. Destruction. Within thirty (30) days after Company's written request, Recipient shall destroy "
            "all Evaluation Material and confirm the destruction to Company in writing.",
            FILLER[2],
            FILLER[3],
            *_sig(),
        ],
        "expect": {
            "term": "change",
            "reps": "change",
            "retain": "change",
            "sign": "change",
        },
        "term_old": "thirty-six (36)",
        "reps_para": "1. Permitted Recipients.",
        "return_para": "3. Destruction.",
        "term_para": "2. Confidentiality Period.",
    },
]


# ---------------------------------------------------------------------------
# Held-out set: written after the engine, in styles it was not tuned on.
# Paragraph entries can be a string, ("Bold heading.", " rest of clause") to
# get two differently formatted runs, or {"table": [[cell, cell], ...]}.
HOLDOUT = [
    {
        "id": "H1_bold_headings_table_sig",
        "description": "Bold run headings, 'Receiving Party' wording, one-year term (compliant), signature block in a two-column table with Name and Title lines.",
        "paragraphs": [
            "CONFIDENTIAL DISCLOSURE AGREEMENT",
            'Effective as of October 1, 2026, Calder Bio, LLC ("Disclosing Party") and the receiving party '
            'identified below ("Receiving Party") agree as follows:',
            (
                "1. Purpose.",
                " Receiving Party will receive information to evaluate a licensing arrangement.",
            ),
            (
                "2. Representatives.",
                ' Receiving Party may disclose Confidential Information to its "Representatives", '
                "meaning its officers, employees, attorneys and accountants, in each case who need to know it.",
            ),
            (
                "3. Term of Agreement.",
                " This Agreement expires one (1) year after the Effective Date, and the "
                "confidentiality obligations herein survive for the same period.",
            ),
            (
                "4. Return.",
                " On termination, Receiving Party will promptly deliver to Disclosing Party all documents "
                "containing Confidential Information, or destroy them at Disclosing Party's direction.",
            ),
            (
                "5. Non-Solicitation.",
                " For thirty-six (36) months, Receiving Party will not solicit Disclosing Party's employees.",
            ),
            "Agreed and accepted:",
            {
                "table": [
                    ["CALDER BIO, LLC", "RECEIVING PARTY"],
                    ["By: Mina Okafor", "By: ____________________"],
                    ["Name: Mina Okafor", "Name: ____________________"],
                    ["Title: General Counsel", "Title: ____________________"],
                ]
            },
        ],
        "expect": {
            "term": "keep",
            "reps": "change",
            "retain": "change",
            "sign": "change",
        },
        "term_old": "one (1) year",
        "reps_para": "2. Representatives.",
        "return_para": "4. Return.",
        "term_para": "3. Term of Agreement.",
        "sign_len": 9,
        "discloser_lines": ["By: Mina Okafor", "Title: General Counsel"],
    },
    {
        "id": "H2_perpetual_numbered_defs",
        "description": "Definitions section, perpetual obligations with no number, 'Evaluation Material', signature lines with a 'Print Name' field.",
        "paragraphs": [
            "NONDISCLOSURE AGREEMENT",
            'This Agreement is made between Larkspur Foods Holdings, Inc. (the "Company") and the party signing below (the "Recipient").',
            "Section 1. Definitions.",
            '(a) "Evaluation Material" means all information furnished by the Company to the Recipient in connection with a possible acquisition of the Company.',
            '(b) "Representatives" includes, with respect to the Recipient, its affiliates and its and their respective directors, officers, employees, agents and advisors.',
            "Section 2. Confidentiality. The Recipient shall keep the Evaluation Material confidential and shall not use it except to evaluate the possible acquisition.",
            "Section 3. Survival. The obligations under Section 2 shall survive indefinitely.",
            "Section 4. Return or Destruction of Evaluation Material. If the Recipient decides not to proceed, it shall promptly return or destroy all Evaluation Material.",
            "Section 5. Miscellaneous. This Agreement is governed by New York law.",
            "LARKSPUR FOODS HOLDINGS, INC.",
            "By: /s/ Dana Whitfield",
            "Title: Chief Financial Officer",
            "RECIPIENT",
            "Signature: ______________________",
            "Print Name: ______________________",
            "Title: ______________________",
        ],
        "expect": {
            "term": "change",
            "reps": "change",
            "retain": "change",
            "sign": "change",
        },
        "term_old": "indefinitely",
        "reps_para": '(b) "Representatives"',
        "return_para": "Section 4.",
        "term_para": "Section 3.",
        "sign_len": 7,
        "discloser_lines": ["By: /s/ Dana Whitfield", "Title: Chief Financial Officer"],
    },
    {
        "id": "H3_inline_term_in_obligations",
        "description": "Term buried mid-sentence in the obligations clause, uses 'Recipient Representatives' without a quoted definition, '24 months' style numbers elsewhere.",
        "paragraphs": [
            "Confidentiality Undertaking",
            'In consideration of being given access to information about Brightwater Logistics Ltd ("Brightwater"), '
            'the undersigned ("Recipient") undertakes as follows.',
            "1. Recipient will keep the Information confidential for 5 years from the date of this letter and will "
            "use it only for assessing a potential investment in Brightwater.",
            '2. Recipient may disclose the Information to its directors and employees (its "Representatives") who '
            "need to know it, and will be responsible for any breach by them.",
            "3. If requested by Brightwater, Recipient will return or destroy the Information within 14 days.",
            "4. For 24 months, Recipient will not contact Brightwater's customers about the Information without consent.",
            "Signed for and on behalf of the Recipient:",
            "Name: ______________",
            "Position: ______________",
            "Company: ______________",
        ],
        "expect": {
            "term": "change",
            "reps": "change",
            "retain": "change",
            "sign": "change",
        },
        "term_old": "5 years",
        "reps_para": "2. Recipient may disclose",
        "return_para": "3. If requested",
        "term_para": "1. Recipient will keep",
        "sign_len": 4,
        "discloser_lines": [],
    },
]


def flat_paragraphs(nda: dict) -> list[str]:
    out = []
    for item in nda["paragraphs"]:
        if isinstance(item, tuple):
            out.append("".join(item))
        elif isinstance(item, dict):
            for row in item["table"]:
                out.extend(row)
        else:
            out.append(item)
    return out


# ---------------------------------------------------------------------------
# Blind set: written after all engine changes and run once without tuning.
BLIND = [
    {
        "id": "X1_notice_termination_lenders",
        "description": "Agreement terminable on notice with a 5-year survival tail; Representatives lists financial advisors and lenders; recipient block listed first.",
        "paragraphs": [
            "MUTUAL CONFIDENTIALITY AGREEMENT",
            'This agreement is between Osprey Grid Systems Inc. ("Osprey") and the counterparty signing below. '
            'Each of them may be a "Disclosing Party" or a "Receiving Party".',
            "1. Representatives. A Receiving Party may share Confidential Information with its affiliates and its and "
            'their directors, officers, employees, financial advisors, legal counsel and lenders ("Representatives").',
            "2. Duration. This Agreement continues until terminated by either party on thirty (30) days' written notice. "
            "The obligations of each Receiving Party survive termination for five (5) years.",
            "3. Return. Upon the written request of the Disclosing Party, the Receiving Party shall cease use of and, "
            "at its option, return or certify the destruction of all Confidential Information.",
            "4. General. This agreement is governed by the laws of Illinois.",
            "AGREED:",
            "COUNTERPARTY",
            "By: ____________________",
            "Name: ____________________",
            "Title: ____________________",
            "OSPREY GRID SYSTEMS INC.",
            "By: Priya Raman",
            "Name: Priya Raman",
            "Title: Vice President, Corporate Development",
        ],
        "expect": {
            "term": "change",
            "reps": "change",
            "retain": "change",
            "sign": "change",
        },
        "term_old": "five (5) years",
        "reps_para": "1. Representatives.",
        "return_para": "3. Return.",
        "term_para": "2. Duration.",
        "sign_len": 10,
        "discloser_lines": [
            "By: Priya Raman",
            "Title: Vice President, Corporate Development",
        ],
    },
    {
        "id": "X2_letter_style",
        "description": "Letter agreement written to 'you'; 18-month term (compliant); definition of Representatives appears after first use; 'For and on behalf of' signature.",
        "paragraphs": [
            "Private and Confidential",
            "Dear Sir or Madam,",
            'In connection with your consideration of a possible purchase of Tamsin Outdoor Co. (the "Company"), we are '
            'prepared to make available to you certain information concerning the Company (the "Information").',
            "You agree to keep the Information confidential and not to disclose it to anyone other than your "
            "Representatives, for a period of eighteen (18) months from the date of this letter.",
            'As used in this letter, "Representatives" shall mean your partners, officers and employees.',
            "If you decide not to proceed, you will promptly return to us or destroy all copies of the Information.",
            "This letter is governed by English law.",
            "Yours faithfully,",
            "For and on behalf of Tamsin Outdoor Co.",
            "Accepted and agreed by:",
            "Name: ____________________",
            "Title: ____________________",
            "For and on behalf of: ____________________",
        ],
        "expect": {
            "term": "keep",
            "reps": "change",
            "retain": "change",
            "sign": "change",
        },
        "term_old": "eighteen (18) months",
        "reps_para": "As used in this letter",
        "return_para": "If you decide not to proceed",
        "term_para": "You agree to keep",
        "sign_len": 6,
        "discloser_lines": ["For and on behalf of Tamsin Outdoor Co."],
    },
    {
        "id": "X3_existing_archive_and_label_table",
        "description": "Already has an archiving carve-out and complete Representatives; term is 'the later of three (3) years or ...'; signature is a label/value table.",
        "paragraphs": [
            "NON-DISCLOSURE AGREEMENT",
            'Fernhill Therapeutics, Inc. ("Fernhill") will disclose information to the recipient identified below '
            '("Recipient") for the purpose of evaluating a research collaboration.',
            '1. Representatives. "Representatives" means Recipient\'s affiliates, directors, officers, employees, '
            "investors, agents, advisors and potential financing sources.",
            "2. Term. Recipient's obligations end on the later of three (3) years from the date hereof and two (2) years "
            "after the end of any collaboration between the parties.",
            "3. Return. On request, Recipient will return or destroy Confidential Information, except to the extent it is "
            "retained in automatic electronic archiving and back-up systems, which shall remain confidential.",
            "4. Miscellaneous. Delaware law governs this Agreement.",
            {
                "table": [
                    ["RECIPIENT", ""],
                    ["By:", "____________________"],
                    ["Name:", "____________________"],
                    ["Title:", "____________________"],
                ]
            },
            "FERNHILL THERAPEUTICS, INC.",
            "By: Theo Brandt",
            "Title: Chief Business Officer",
        ],
        "expect": {
            "term": "change",
            "reps": "keep",
            "retain": "keep",
            "sign": "change",
        },
        "term_old": "three (3) years",
        "reps_para": "1. Representatives.",
        "return_para": "3. Return.",
        "term_para": "2. Term.",
        "sign_len": 11,
        "discloser_lines": ["By: Theo Brandt", "Title: Chief Business Officer"],
    },
]
