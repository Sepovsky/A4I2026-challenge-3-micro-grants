# Source evidence takes priority over illustrative benchmark claims

The four preceding design documents contain assumed financials, hypothetical
applicants, geographic diagrams, policy thresholds and illustrative impact totals.
They are not empirical proof, a city policy, a grant determination or verified
beneficiary counts. Their named examples must not override source records.

Use `data/TASK_2_3_REVIEW.md` and `data/task_2_3_review.json` for the current review.
The inherited cohort has 232 matched registry locations, including branches.
The local reviewed model has 293 BEA/proximity supply edges at a coefficient
floor of 0.015, distance <=500m, and up to five suppliers per buyer. This is a
different, explicitly labeled model from the starter's 0.005/1200m graph.

Use `analyze_corridor_impact` for one through eight hops in either direction.
First call `find_corridor_businesses(query)` to select the registry location ID
using its name and address. The `cm_*` IDs in the illustrative benchmark are not
registry keys. A unique exact business/legal name also resolves, but partial or
ambiguous names require selecting a candidate ID. Check `status == "OK"` before
reporting reach; unknown, ambiguous and scenario IDs return a structured response,
not zero exposure or an inferred business match.
Count distinct destinations and exclude the source. Default to two hops for
decisions, with three through eight as sensitivity. Do not claim longer impact
where the observed graph stops gaining destinations. Use strongest weighted
endpoint exposure, not a sum of every walk; cycles cannot create beneficiaries.

Use `review_industry_variety` to compare the cohort and the 5–25 destination
cascade shortlist. This band is a policy scenario, not a validation criterion or
reason to deny essential-service/direct relief. Industry is not ownership;
never disqualify every IT, manufacturing or professional-services business by NAICS.

The five connected problems are input disruption, upstream demand loss, worker
demand loss, debt pressure and essential-service access. Only the first two are
traversable from the local supply graph. Employer/footfall, address-checked SBA,
and ACS/catchment evidence must be added for the other mechanisms. Do not turn
these mechanisms into fabricated measured resident or worker counts.

Only `industry_failure_rates` produced by `notebooks/Challenge3.ipynb` is an
accepted risk prior. The legacy `sba_industry_failure_rates.csv` is quarantined
from runtime consumers. A loan charge-off is not a current closure or insolvency.
Require same-street-address matches; a missing street number is not verification.
An SBA history match is never a supplier invoice.

Location tenure comes from the registry location start date, never digits in an
account number. Preserve short NAICS codes and fall back to sector/state rates;
do not turn `72` into `7225` or `44` into `4451`. Same-name locations are retained
and audited using IDs, legal names and addresses before any merge.

No current cash, operating burn, debt payment or eligibility attestation is
present in the registry. Real-source records stay in evidence review until
applicant inputs are supplied. The $8,000 debt-bridge function is explicitly an
assumption sensitivity, not an estimated causal effect. Missing debt is unknown,
and does not mean zero need. A flat 25% multiplier cannot reorder a ranking.

The saved notebook found AUC 0.700 for loan terms and 0.695 with graph features
(difference -0.005; 95% interval -0.018 to +0.007). That does not establish a
predictive improvement. Hub reach versus failure risk had rho=-0.14, p=0.33
across 47 industries. Use graph structure for modeled consequence, and label SBA
history as an industry charge-off prior with its own limitations.


Current implementation rules: portfolio allocation is a budgeted priority heuristic,
not an exact knapsack optimizer. Awards cannot exceed requests, and an indivisible
shock receives either its entire request or zero. Regime comparisons use the same
supplied policy weights. Sensitivity checks compare actual funded awards under the
budget at 51 grid points; there is no hardcoded 0.72 crossover or all-weight proof.
Spatial compliance includes a straight-line centroid radius check; missing coordinates
cannot establish co-location. Fixture clusters may fail this check.

Reports are draft scenario analyses. Do not label a modeled job count as jobs saved,
an invoice flag as a reviewed invoice, or a calculated portfolio as an approved award.
Documentary checks remain REVIEW_REQUIRED in scenario reports. The connected console
supports versioned intake with a separate recorded review; reviewed source records
still require independently validated grant-effect assumptions and source rates.
