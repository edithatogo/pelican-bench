# Content-addressed study protocol lock

## Purpose

The protocol lock freezes the inferential inputs that must not change silently once the prospective campaign starts. It is independent of Git commit identity and can be verified from any complete checkout.

The lock includes the candidate task commitment, model and judge panels, human-calibration specification, design assumptions, campaign and judge-firewall policies, rubrics, analysis plan, operational implementation modules and numbered amendments. Each file is recorded with a SHA-256 digest and byte length.

## Amendments

Amendments are append-only and record:

- identifier and timestamp;
- whether outcomes had been observed or unblinded;
- rationale;
- affected files;
- whether the task commitment changed; and
- the required primary or sensitivity analysis.

Task-affecting amendments require before and after task commitments. Any amendment after unblinding requires a sensitivity analysis. Original plans and results are not overwritten.

## Commands

```bash
pelicanbench study-protocol-lock --root .
pelicanbench verify-study-protocol --root .
```

The lock must verify before model qualification is promoted into the main campaign. The lock proves file fixity and amendment completeness; it does not prove that the scientific design is valid.
