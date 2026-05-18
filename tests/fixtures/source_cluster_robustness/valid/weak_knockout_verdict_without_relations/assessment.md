# Assessment: weak knockout verdict without relations (valid fixture)

Verdict for c001 is strongly_supported, but this case has a cluster dependency problem.
The cluster dependency is high: both s001 and s002 are part of the official investigation cluster.
After removing the official cluster, this fixture sets verdict_without_cluster to "unresolved".

This fixture confirms that weak post-knockout verdicts can remain valid even when
evidence-relations.yml is absent.
