.PHONY: test validate harness fixture issues hf

test:
	PYTHONPATH=src python -m pytest -q
validate:
	PYTHONPATH=src python scripts/validate_repo.py
harness:
	bash scripts/harness.sh
fixture:
	PYTHONPATH=src python -m pelicanbench.cli run-fixture --output artifacts/fixture
issues:
	PYTHONPATH=src python scripts/sync_github_issues.py
hf:
	PYTHONPATH=src python scripts/setup_huggingface.py
