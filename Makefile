.PHONY: validate test report

validate:
	python scripts/validate_claims.py cases
	python scripts/validate_sources.py cases
	python scripts/validate_evidence_pack.py cases
	python scripts/validate_case_references.py cases
	python scripts/validate_lifecycle.py cases

test:
	python -m pytest tests

report:
	@echo "Report generation not yet implemented in MVP 0.1"
