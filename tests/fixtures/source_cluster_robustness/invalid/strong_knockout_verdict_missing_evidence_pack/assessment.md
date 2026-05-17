# Assessment: high verdict without remaining support (invalid fixture)

Verdict for c001 is strongly_supported, but this case has a cluster dependency problem.
The cluster dependency is high: both s001 and s002 are part of the official investigation cluster.
After removing the official cluster, no independent supporting evidence remains, yet
verdict_without_cluster is set to "plausible" rather than "weak" or "very_weak".

This fixture tests that the relational knockout check catches the mismatch between
the declared verdict_without_cluster and the actual remaining evidence relations.
