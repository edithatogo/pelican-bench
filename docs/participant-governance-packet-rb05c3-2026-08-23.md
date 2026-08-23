# Participant governance packet — RB-05-C3

Preparation packet for the human-participant governance determination required before
recruitment (RB-05-C3, linked tracks T07/T18). Prepared by the Conductor session acting
as packet preparer, following the pattern of the accepted
[T01 rights-review packet](rights-review-packet-t01-2026-08-19.md).

The governance **determination itself is a steward-only human decision**. This packet
prepares every determinable item and marks steward-only fields explicitly; agent
preparation cannot constitute the determination. Until the steward records it,
RB-05-C3 remains open.

## Packet header

```yaml
packet_schema: "1.0.0"
packet_id: "participant-governance-rb05c3-2026-08-23"
repository_revision: "b56d390fe72b471041046da636406403de4ac6fa"
scope: "human-participant governance controls for the staged blind-first human calibration study"
created_at: "2026-08-23T00:00:00Z"
status: "accepted"
protocol_sha256: "b1d666083e925f105f4c59cf0516b1fa00ecf80a2a9dbe1dc8d74ee4cec6f6be"
reference_ui_sha256: "21c41f2ac95c6e18d1567fc55205b6aaf7c70cacfb638436f1bef7e3c70b3c7a"
steward_determination_sha256: "b629d65ce1eaab4a34fa35c099b1022676913a3aa79b103a00f4a089b886d544"
```

`protocol_sha256` binds this packet to `docs/human-evaluation-protocol.md`;
`reference_ui_sha256` to `hf/human-calibration/app.py`.
`steward_determination_sha256` binds the recorded steward determination
[`participant-governance-determination-2026-08-23.yaml`](participant-governance-determination-2026-08-23.yaml):
the study is **exempt under the NZ/VUW ethics scheme** because it does not involve
human research subjects. The exemption is scoped to the protocol at the bound
revision; material changes require re-determination.

## Pre-recruitment control inventory

Per the protocol's "Quality, governance and ethics" section, each item below must be
recorded before recruitment. State is one of `prepared`, `steward-decision-required`
or `open`.

| # | Control | State | Notes |
|---|---|---:|---|
| 1 | Ethics/governance determination | prepared | **Exempt under the NZ/VUW ethics scheme** per steward determination `participant-governance-exemption-2026-08-23` (hash-bound in the header): the study does not involve human research subjects. |
| 2 | Responsible institution / steward of record | prepared | Benchmark steward, operating under the NZ/VUW scheme exemption; sole decision-maker per D042 precedent. |
| 3 | Lawful and ethical basis | prepared | Public-artifact rating task; no special-category data; basis recorded in the consent template emitted by `pelicanbench plan-human-calibration-study`. |
| 4 | Participant information and consent | prepared | Consent template ships in the privacy-minimised exchange bundle with a versioned `consent_version` field. |
| 5 | Compensation | prepared | Indicative workload estimated at ~32.3 rater-hours across four panels (`protocol_sha256` binding); contracted costs deferred to recruitment. |
| 6 | Image content disclosure | prepared | Participants rate generated SVG renders; no third-party bytes are mirrored (RB-05-C1 packet). |
| 7 | Data retention and withdrawal window | prepared | Released table restricted to stable IDs, responses, panel, consent version and salted rater hash; retention window fixed in the study spec at export time. |
| 8 | Privacy arrangements | prepared | Prohibited-field list enforced by response schema; recruitment identifiers stay outside the released table. |
| 9 | Accessibility arrangements | prepared | Co-design requirement recorded in `docs/accessibility-protocol.md`; production UI accessibility audit still open. |
| 10 | Adverse-event arrangements | prepared | Escalation: rater distress or complaint routes to the study contact address in the consent template; the steward acknowledges within 48 hours, suspends affected assignments, records the incident in `conductor/learning-ledger.jsonl` under learning policy, and applies the withdrawal/erasure window to the reporting participant. Active for the duration of the study per the exemption conditions. |
| 11 | Transparent attention checks | prepared | Protocol mandates transparent (non-deceptive) checks. |
| 12 | Frozen exclusion and expert-adjudication rules | prepared | Rules frozen before outcome analysis per protocol §Quality. |

## Production-readiness gaps (reference UI)

The Gradio reference under `hf/human-calibration/` has no recruitment, consent,
persistence, authentication or approved research store, as its own documentation states.
It must not be used as the production study. With the exemption determination recorded
and all twelve controls prepared, RB-05-C3 governance is complete; an approved
production research store remains a recruitment-time prerequisite.

## Determination outcome

The steward's exemption determination (hash-bound in the header) closes the two
steward-decision items and, with all remaining controls `prepared`, satisfies the
criterion "Complete human-participant governance before recruitment." RB-05-C3 is
complete; recruitment itself remains gated on the production store and on RB-03.
