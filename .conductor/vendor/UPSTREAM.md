# Conductor upstream provenance

The workspace plugin is a Git submodule pinned to
`gemini-cli-extensions/conductor@f06add33b598f4262a190f234828dda551db70d7`
(`conductor-v0.4.1-16-gf06add3`). The upstream gitlink is immutable in each
PelicanBench commit. PelicanBench-specific operating rules remain separate in
`.agents/skills/conductor-*` and `.agents/rules/pelicanbench.md` so updating the
submodule cannot overwrite project policy.

Run `scripts/refresh_conductor.sh` to initialize or refresh the exact pin, then
run `scripts/sync_conductor_install.py --check` to validate the submodule and
adapters.
