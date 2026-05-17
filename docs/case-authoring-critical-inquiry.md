# Case Authoring: Critical Inquiry Gates

Use this guide when a case moves beyond a draft evidence sketch into a provisional or final assessment. The goal is not to make every draft heavy; it is to prevent closure from silently crossing category boundaries.

## `reported_claim` vs world claim

Use `claim_kind: reported_claim` when the proposition being closed is **source X reports Y**. A strong verdict on that claim closes only the source-content question: the source did or did not say the thing. It does not close the world claim Y.

If the case needs to assess Y as a world proposition, add a separate world claim and evidence relations for that claim. `reports` relations may support source-content closure; world-claim closure needs `supports_directly` or `supports_indirectly` relations and appropriate source-weight, anomaly, and investigation-integrity coverage.

## `absence_claim`

Use `claim_kind: absence_claim` only with a bounded search scope, for example:

- in the current `evidence-pack.yml`;
- in source X;
- in dataset Y;
- in the audited public record named by the case.

An absence claim must not escalate to “exists nowhere.” It must include `forbidden_upgrades: [absence_of_evidence_to_falsehood]`.

## `contradictions.yml`

Use `contradictions.yml` when claims, counterclaims, or evidence create a visible conflict. A contradiction ledger is not a verdict engine: the conflict is documented, referenced, and given a `resolution_status`, but the claim verdict still depends on typed evidence relations and the stated burden.

Strong alternative explanations are not direct falsifications. For co-causation claims, do not mark a claim `contradicted` merely because a better-supported primary cause exists; use `direct_incompatibility_basis` if direct falsification is intended, and tie that basis to the required causal-chain link that is directly ruled out. Direct contradiction requires direct incompatibility. A stronger alternative explanation, missing link, non-test, source-report non-corroboration, or bounded absence claim may weaken or cap confidence, but must not by itself produce `contradicted` for a co-causation/world-causal claim.

## `anomaly-ledger.yml`

Use `anomaly-ledger.yml` for material anomalies such as method gaps, non-tests, chain-of-custody gaps, unavailable raw data, source-cluster dependence, and overstrong conclusions.

An anomaly is not proof. A non-test is not a cover-up. A chain-of-custody gap is not a forgery. High-materiality anomalies (`materiality >= 0.7`) must be visible in `assessment.md` because they can lower confidence or prevent closure even when they do not prove a causal story.

## `investigation-integrity.yml`

Use `investigation-integrity.yml` when a source cluster carries closure power, especially official, government, advocacy, corporate, or NGO reports used for strong world claims. The audit weighs sources by:

- proximity to primary evidence;
- method transparency;
- replicability;
- source-cluster independence;
- institutional interest risk;
- adversarial relevance.

High method depth and high interest risk can both be true. Do not convert source prestige into truth.

## Three forbidden conversions

- **Suspicion to proof:** anomalies, interests, and gaps can create hypotheses or lower confidence; they do not prove manipulation without additional evidence.
- **Source prestige to truth:** official, corporate, academic, NGO, and advocacy sources all need method and independence checks when they carry closure power.
- **Non-test to cover-up:** a material untested path limits closure and must be visible, but it does not prove concealment by itself.


## Overclosure authoring checklist

Before assigning `status: contradicted` to a world-causal or co-causation claim, check that the case is not merely saying one of these weaker things: a better explanation exists, no positive evidence was found, an official source did not corroborate the claim, a causal bridge is missing, or a method/non-test gap remains. Those operations should normally cap or downgrade confidence rather than close the claim negatively.

For `burden_profile: causal_chain`, keep `required_chain` populated whenever the claim uses a strong or negative verdict. If unresolved high-materiality anomalies or source-overlapping non-tested paths still affect the claim, leave the claim below negative closure unless the residual path has been explicitly closed; first-class `affected_claims` and residual-closure fields for non-tested paths are future schema extensions.
