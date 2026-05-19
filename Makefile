PYTHON ?= python
# Optional compatibility hook for distro-managed packages in constrained images.
# Override SYSTEM_PYTHONPATH= to disable, or set PYTHONPATH explicitly for a venv/custom path.
SYSTEM_PYTHONPATH ?= $(wildcard /usr/lib/python3/dist-packages)
PYTHONPATH_PREFIX = $(if $(PYTHONPATH),$(if $(SYSTEM_PYTHONPATH),$(PYTHONPATH):$(SYSTEM_PYTHONPATH),$(PYTHONPATH)),$(SYSTEM_PYTHONPATH))
PYTHONPATH_ENV = $(if $(PYTHONPATH_PREFIX),PYTHONPATH=$(PYTHONPATH_PREFIX),)

.PHONY: validate test report

validate:
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_case_topology.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_anomaly_ledger.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_investigation_integrity.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_assessment_anomaly_coverage.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_no_fixture_language.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_mechanical_migration_discipline.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_claims.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_sources.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_source_verification_gate.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_source_weight_audit.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_hypothesis_support_ledger.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_contradictions.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_model_defeaters.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_inference_ledger.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_burden_layers.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_model_audit.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_verdict_caps.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_verdict_discipline.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_overclosure.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_evidence_pack.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_case_references.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_source_cluster_robustness.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_lifecycle.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_forbidden_language.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_status_prose_consistency.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_answer_receipt.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_answer_receipt_claims_consistency.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_refusal_discipline.py cases
	$(PYTHONPATH_ENV) $(PYTHON) scripts/validate_aggregation_discipline.py cases

test:
	$(PYTHONPATH_ENV) $(PYTHON) -m pytest tests

report:
	@echo "Report generation not yet implemented in MVP 0.1"
