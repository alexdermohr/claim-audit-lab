# Assessment: established with only one remaining evidence_ref (invalid fixture)

After removing the official cluster, only one supporting relation backed by a single
evidence_ref remains for claim c001. The knockout test still asserts
verdict_without_cluster='established', which the validator must reject because
established requires at least two distinct evidence_refs among the remaining support.
