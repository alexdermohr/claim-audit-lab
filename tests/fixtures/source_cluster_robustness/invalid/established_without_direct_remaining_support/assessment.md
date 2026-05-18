# Assessment: established without direct remaining support (invalid fixture)

After removing the official cluster, two independent supporting relations remain for
claim c001, but both are supports_indirectly. The knockout test still asserts
verdict_without_cluster='established', which the validator must reject because
established requires at least one supports_directly relation among the remainder.
