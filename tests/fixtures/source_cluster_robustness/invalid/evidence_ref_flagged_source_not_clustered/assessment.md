# Assessment: evidence_ref flagged source not clustered (invalid)

Claim c001 has source_refs: [s001] explicitly and evidence_refs: [e002], where e002
comes from s002. Both s001 and s002 are flagged by investigation-integrity.yml.
The declared cluster only covers s001. Source s002 is flagged but not covered by
any declared cluster, which violates the full-coverage requirement.
