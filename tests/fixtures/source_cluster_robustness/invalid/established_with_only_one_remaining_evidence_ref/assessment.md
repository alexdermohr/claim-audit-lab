# Assessment: established with only one remaining evidence_ref (invalid fixture)

After removing the official cluster, two supporting relations remain for claim c001,
but they are backed by only a single distinct evidence_ref. The knockout test still
asserts verdict_without_cluster='established', which the validator must reject because
established requires at least two distinct evidence_refs among the remaining support.
