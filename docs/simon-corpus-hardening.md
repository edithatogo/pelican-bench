# Simon corpus hardening

The Atom importer treats remote feeds and embedded HTML as untrusted input. Network requests use
a positive timeout and read at most the configured feed ceiling plus one detection byte. Parsing
then rejects feeds above 5 MB, more than 1,000 entries, or more than one million plain-text
characters in any entry. Callers may choose smaller positive limits.

XML parsing uses `defusedxml`; HTML extraction uses the Python standard library and never executes
markup. Raw-content export and derived analysis remain separately rights-gated. These resource
controls prevent exhaustion but do not establish feed completeness, annotation validity or
redistribution permission.

Edge tests exercise every ceiling and invalid policy values. The full harness verifies dependency
locks, supply-chain metadata, deterministic fixtures and the rights audit.
