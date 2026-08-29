# T14 release and attestation dry-run template

**State:** local dry-run template only; no tag, attestation, release, upload, publication, or
unblinding is authorized.

```yaml
schema_version: "1.0.0"
candidate_release_id: "<ID>"
repository_commit: "<40_HEX>"
repository_tree: "<40_HEX>"
tag_proposed: "<TAG>"
release_class: "non-normative-candidate"
release_manifest_sha256: "<64_HEX>"
source_archive_sha256: "<64_HEX>"
git_bundle_sha256: "<64_HEX>"
sbom_sha256: "<64_HEX>"
ro_crate_sha256: "<64_HEX>"
prov_sha256: "<64_HEX>"
rights_allowlist_sha256: "<64_HEX>"
benchmark_card_sha256: "<64_HEX>"
data_card_sha256: "<64_HEX>"
scorer_card_sha256: "<64_HEX>"
run_failure_evaluation_manifest_sha256: "<64_HEX>"
repository_standards_receipt_sha256: "<64_HEX>"
sha256sums_sha256: "<64_HEX>"
restricted_artifact_scan: "not-run"
local_verification: "not-run"
hosted_ci: "not-authorized"
operational_attestation: "not-authorized"
github_release: "not-authorized"
hugging_face_upload: "not-authorized"
publication: "not-authorized"
unblinding: "not-authorized"
gate_effect: "none"
```

The restricted-artifact scan must reject sealed tasks, credentials, secret key material,
private mappings, unblinding authorizations, unblinded outputs, participant identifiers, and
unversioned normative scores. Operational attestations require a separately authorized
remote workflow against the exact immutable commit and tag. GitHub release, Hub creation or
upload, publication, and post-freeze unblinding each require separate explicit steward
authority and exact-revision verification.
