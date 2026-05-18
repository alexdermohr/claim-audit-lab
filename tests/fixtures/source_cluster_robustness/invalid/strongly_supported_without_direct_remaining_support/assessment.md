# Assessment: strongly_supported without direct remaining support (invalid fixture)

After removing the official cluster, only an indirect supporting relation remains for
claim c001. The knockout test still asserts verdict_without_cluster='strongly_supported',
which exceeds the structural support available outside the cluster. The validator must
flag the missing supports_directly remainder.
