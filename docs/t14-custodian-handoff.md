# T14 custodian handoff

This handoff generates the three remaining custody inputs without freezing the sample or
authorizing ratings. The command must be run by the person who accepts custody. Codex and
other agents may validate the resulting hashes but cannot assert the custodian's identity.

## Custody choices

1. **Independent custodian — recommended.** A person other than the steward, raters, and
   confirmatory analyst controls the study secret and restricted artifacts. This gives the
   strongest blinding claim but requires coordination and a secure transfer process.
2. **Steward self-custody.** The benchmark steward controls the secret and artifacts. This is
   faster and acceptable for procedural blinding, but it must be labelled
   `procedural-self-custody-not-independent` and cannot support an independence claim.
3. **Defer.** Preserve the pending packet unchanged. This carries no new disclosure risk but
   blocks the freeze decision and all later rating work.

## Preconditions

- Work from the exact candidate-preparation branch and verify it is clean.
- Choose an output directory outside the Git repository on an encrypted local volume.
- Create a new study-specific secret with at least 32 bytes of entropy and retain it in an
  approved secret store. Do not paste it into chat, a shell argument, a repository file, or
  terminal output.
- Generate the secret with an operating-system CSPRNG. The receipt proves only key
  commitment and minimum byte length; it cannot attest entropy. Weak user-selected secrets
  remain vulnerable to offline guessing and are prohibited.
- Use a non-personal custodian identifier where policy permits.

Set the secret in an environment variable without placing its value on the command line,
then run:

```bash
python scripts/prepare_t14_custody_artifacts.py \
  --output-directory /absolute/path/outside/repository/t14-custody \
  --secret-environment PB_T14_CUSTODY_SECRET \
  --custodian-id '<ACCOUNTABLE_CUSTODIAN_ID>' \
  --custody-classification independent-custody \
  --acknowledge-accountable-custodian
```

For steward self-custody, replace the classification with
`procedural-self-custody-not-independent`. Unset the environment variable immediately after
the command. The tool refuses missing acknowledgement or secret material, repository-local
output, non-empty output directories, secrets shorter than 32 bytes, and overwrites. It
writes all three files with mode `0600` and prints only the receipt hash and destination.

Return the three artifact SHA-256 values, the custody receipt, and the exact tested branch
commit to the repository maintainer. Do not return the secret, alias mapping, or duplicate
schedule contents through chat. The maintainer can then bind the hashes into the pending
packet and present a separate exact-hash freeze decision. Generation itself has no freeze,
rating, promotion, release, publication, or unblinding effect.
