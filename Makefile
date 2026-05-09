.PHONY: validate test report

validate:
	python scripts/validate_claims.py cases
	python scripts/validate_assessment.py cases

test:
	python -m pytest tests

report:
	@echo "Report generation not yet implemented in MVP 0.1"
