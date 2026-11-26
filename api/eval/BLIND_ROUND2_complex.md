# Complex NDA evaluation

Run 2026-11-26 04:19.

| Provider | Document | Checks passed | Untracked edits | Invalid IDs | Opens in LibreOffice | Time |
|---|---|---|---|---|---|---|
| rule-based | CY1_defined_period_roman_list_accepted_block | 6/10 | 0 | 0 | yes | 0.03s |
| rule-based | CY2_earlier_of_mixed_survival_cell_blocks | 10/10 | 0 | 0 | yes | 0.03s |
| rule-based | CY3_nbsp_hyphenated_inline_signature | 3/5 | 0 | 0 | yes | 0.03s |

| Provider | Rule | Passed |
|---|---|---|
| rule-based | collateral | 1/1 |
| rule-based | reps | 3/3 |
| rule-based | retain | 4/4 |
| rule-based | sign | 7/11 |
| rule-based | term | 4/6 |

## Failed checks

- **rule-based / CY1_defined_period_roman_list_accepted_block** [term, expect change] `“Confidentiality Period” means`: not changed; not tracked; missing 'two (2) years'; still contains 'four (4) years' | got: “Confidentiality Period” means the period commencing on the Effective Date and continuing until the date that is four (4) years after the Effective Date.
- **rule-based / CY1_defined_period_roman_list_accepted_block** [sign, expect change] `Entity: ____`: not changed; not tracked; missing 'Halden Capital LLC' | got: Entity: ____________________
- **rule-based / CY1_defined_period_roman_list_accepted_block** [sign, expect change] `Printed Name: ____`: not changed; not tracked; missing 'Jordan Ellis' | got: Printed Name: ____________________
- **rule-based / CY1_defined_period_roman_list_accepted_block** [sign, expect change] `Title: ____`: not changed; not tracked; missing 'Managing Partner' | got: Title: ____________________
- **rule-based / CY3_nbsp_hyphenated_inline_signature** [term, expect change] `The Recipient agrees to keep`: not changed; not tracked; missing 'two'; still contains 'five' | got: The Recipient agrees to keep the Information confidential for a five (5)-year period from the date of this undertaking — and to use it only for Project Larch.
- **rule-based / CY3_nbsp_hyphenated_inline_signature** [sign, expect change] `Signed by ____`: not changed; not tracked; missing 'Jordan Ellis'; missing 'Halden Capital LLC' | got: Signed by ____________________ for and on behalf of ____________________ (the Recipient)