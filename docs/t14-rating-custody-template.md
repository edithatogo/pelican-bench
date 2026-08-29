# T14 rating and custody packet template

**State:** preparation only; contains no rating, participant, consent, identity, or custody
evidence.

Use this template only after an exact sample freeze. Rating interfaces receive aliases and
canonical renders, never source labels, automatic scores, model identities, private maps, or
agent recommendations. Original responses are append-only and adjudication never overwrites
them.

```yaml
schema_version: "1.0.0"
study_id: "<STUDY_ID>"
freeze_commitment_sha256: "<64_HEX>"
protocol_sha256: "<64_HEX>"
participant_governance_sha256: "<64_HEX>"
production_store_review_sha256: "<64_HEX>"
accessibility_review_sha256: "<64_HEX>"
alias_manifest_sha256: "<64_HEX>"
assignment_manifest_sha256: "<64_HEX>"
consent_version: "<VERSION>"
rating_route: "pending"
raters: []
adjudicator: null
custodian: null
private_map_location: null
response_ledger_head_sha256: null
missingness_receipt_sha256: null
adjudication_receipt_sha256: null
blinding_breach: null
status: "not-started"
gate_effect: "none"
```

For promotion-grade inter-rater claims, use at least two governed raters and an adjudicator.
A sole-steward route supports test-retest reporting only. Agents and synthetic responses
never qualify. A blinding breach, invalid/omitted rate above 5%, or duplicate consistency
below 0.80 stops promotion; preserve the record and prospectively authorize a new wave.
Operational custody should separate the per-study key and private map from raters and
analysts. Steward self-custody must be labelled procedural, not independent.
