PYTHON ?= python
# Optional compatibility hook for distro-managed packages in constrained images.
# Override SYSTEM_PYTHONPATH= to disable, or set PYTHONPATH explicitly for a venv/custom path.
SYSTEM_PYTHONPATH ?= $(wildcard /usr/lib/python3/dist-packages)
PYTHONPATH_PREFIX = $(if $(PYTHONPATH),$(PYTHONPATH):$(SYSTEM_PYTHONPATH),$(SYSTEM_PYTHONPATH))

.PHONY: validate test report

validate:
	PYTHONPATH=$(PYTHONPATH_PREFIX) $(PYTHON) scripts/validate_claims.py cases
	PYTHONPATH=$(PYTHONPATH_PREFIX) $(PYTHON) scripts/validate_sources.py cases
	PYTHONPATH=$(PYTHONPATH_PREFIX) $(PYTHON) scripts/validate_source_weight_audit.py cases
	PYTHONPATH=$(PYTHONPATH_PREFIX) $(PYTHON) scripts/validate_hypothesis_support_ledger.py cases
	PYTHONPATH=$(PYTHONPATH_PREFIX) $(PYTHON) scripts/validate_verdict_discipline.py cases
	PYTHONPATH=$(PYTHONPATH_PREFIX) $(PYTHON) scripts/validate_evidence_pack.py cases
	PYTHONPATH=$(PYTHONPATH_PREFIX) $(PYTHON) scripts/validate_case_references.py cases
	PYTHONPATH=$(PYTHONPATH_PREFIX) $(PYTHON) scripts/validate_lifecycle.py cases

test:
	PYTHONPATH=$(PYTHONPATH_PREFIX) $(PYTHON) -m pytest tests

report:
	@echo "Report generation not yet implemented in MVP 0.1"
