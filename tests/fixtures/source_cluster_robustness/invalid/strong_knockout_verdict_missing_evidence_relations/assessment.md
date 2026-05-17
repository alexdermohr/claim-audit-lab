# Assessment: strong knockout verdict missing evidence-relations (invalid fixture)

Verdict for c001 is strongly_supported, but this case has a cluster dependency problem.
The cluster dependency is high: both s001 and s002 are part of the official investigation cluster.
After removing the official cluster, no independent supporting evidence remains, yet
verdict_without_cluster is set to "plausible" rather than "weak" or "very_weak".

This fixture tests that strong post-knockout verdicts are rejected when
evidence-relations.yml is missing.
