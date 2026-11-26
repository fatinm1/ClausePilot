# Complex NDA evaluation

Run 2026-11-26 04:17.

| Provider | Document | Checks passed | Untracked edits | Invalid IDs | Opens in LibreOffice | Time |
|---|---|---|---|---|---|---|
| rule-based | CX1_long_defined_terms_prior_redlines | 10/14 | 0 | 0 | yes | 0.06s |
| rule-based | CX2_three_party_two_rep_definitions | 5/11 | 0 | 0 | yes | 0.03s |
| rule-based | CX3_already_good_many_durations | 7/10 | 0 | 0 | yes | 0.02s |
| rule-based | CX4_30_pages | 6/6 | 0 | 0 | yes | 0.22s |

| Provider | Rule | Passed |
|---|---|---|
| rule-based | collateral | 5/5 |
| rule-based | reps | 5/5 |
| rule-based | retain | 2/4 |
| rule-based | sign | 10/16 |
| rule-based | term | 6/11 |

## Failed checks

- **rule-based / CX1_long_defined_terms_prior_redlines** [term, expect change] `1.4 “Term” means`: not changed; not tracked; none of ['second (2nd) anniversary', 'two (2) years', '2nd anniversary']; still contains 'third (3rd)' | got: 1.4 “Term” means the period beginning on the Effective Date and ending on the third (3rd) anniversary thereof.
- **rule-based / CX1_long_defined_terms_prior_redlines** [term, expect change] `7.1 This Agreement shall remain`: not changed; not tracked; none of ['two (2) years', 'two years']; still contains 'five years' | got: 7.1 This Agreement shall remain in effect during the Term. Sections 3 through 6 survive any expiration or termination of this Agreement for a period of five years.
- **rule-based / CX1_long_defined_terms_prior_redlines** [term, expect keep] `1.2 “Confidential Information”`: changed: 1.2 “Confidential Information” means all non-public information disclosed by or on behalf of a Party, including information disclosed during the two (2) years b
- **rule-based / CX1_long_defined_terms_prior_redlines** [sign, expect change] `[RECIPIENT NAME]`: not changed; not tracked; missing 'Halden Capital LLC' | got: [RECIPIENT NAME]
- **rule-based / CX2_three_party_two_rep_definitions** [retain, expect keep] `5. Upon Discloser`: changed: 5. Upon Discloser’s request, Recipient shall return or destroy all Evaluation Material, except that Recipient’s legal department may keep one archival copy sole
- **rule-based / CX2_three_party_two_rep_definitions** [sign, expect change] `RECIPIENT: [●]`: not changed; not tracked; missing 'Halden Capital LLC'; still contains '[●]' | got: RECIPIENT: [●]
- **rule-based / CX2_three_party_two_rep_definitions** [sign, expect change] `Name: ____`: not changed; not tracked; missing 'Jordan Ellis' | got: Name: ____________________
- **rule-based / CX2_three_party_two_rep_definitions** [sign, expect change] `Title: ____`: not changed; not tracked; missing 'Managing Partner' | got: Title: ____________________
- **rule-based / CX2_three_party_two_rep_definitions** [sign, expect keep] `Name: ____`: changed: Name: Jordan Ellis
- **rule-based / CX2_three_party_two_rep_definitions** [sign, expect keep] `Title: ____`: changed: Title: Managing Partner
- **rule-based / CX3_already_good_many_durations** [term, expect keep] `3. Recipient shall maintain records`: changed: 3. Recipient shall maintain records of all persons to whom Confidential Information is disclosed for two (2) years after the date of disclosure.
- **rule-based / CX3_already_good_many_durations** [term, expect keep] `7. Recipient shall preserve`: changed: 7. Recipient shall preserve all Confidential Information subject to litigation holds for the duration of any proceeding, which may exceed two (2) years.
- **rule-based / CX3_already_good_many_durations** [retain, expect keep] `6. On request`: changed: 6. On request Recipient will return or destroy Confidential Information, except that Recipient’s outside counsel may keep one copy for archival purposes. Notwit