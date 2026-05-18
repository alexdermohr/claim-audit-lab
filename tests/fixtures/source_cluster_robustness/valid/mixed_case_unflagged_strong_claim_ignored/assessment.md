# Assessment: mixed case unflagged strong claim ignored (valid)

Claim c001 is strongly_supported but depends only on independent source s001,
which is NOT one of the investigation-flagged sources (s010, s011). Therefore
Rule 3 does not apply to c001: no source-cluster-robustness.yml is required
because c001's resolved source set has no overlap with the flagged cluster sources.
