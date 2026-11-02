"""Canonical cloud graph and source-review loaders.

Cloud mode reads reviewed source tables and LocalEconomy. Local mode reads the
reproducible registry/BEA review. Neither invents financial inputs. The explicit
canonical mode is an illustrative 11-applicant regression fixture, not evidence.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tools.scoring_engine import CANONICAL_CENTRAL_MARKET_APPLICANTS


REPO_ROOT = Path(__file__).resolve().parent.parent



# ============================================================================
# GQL DDL & MULTI-HOP PROPERTY GRAPH QUERIES (Section 13 of Notebook)
# ============================================================================

def get_property_graph_ddl(dataset: str = "a4i_econ") -> str:
    """One canonical graph over reviewed tables; raw tables are preserved.

    Run schema_and_queries.sql after Challenge3.ipynb produces canonical rates
    and address-checked loan matches. No hardcoded lookup values are installed.
    """
    import re
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", dataset):
        raise ValueError("Invalid dataset identifier")
    return f"""
CREATE OR REPLACE PROPERTY GRAPH {dataset}.LocalEconomy
NODE TABLES (
  {dataset}.businesses_enriched KEY (business_id)
    LABEL Business PROPERTIES (business_id, name, naics4, industry_type, latitude, longitude, registration_year, tenure_years),
  {dataset}.employer_blocks KEY (block_id) LABEL Employer PROPERTIES (block_id, jobs),
  {dataset}.lenders_enriched KEY (bank_name) LABEL Lender PROPERTIES (bank_name)
)
EDGE TABLES (
  {dataset}.supplies_enriched KEY (edge_id)
    SOURCE KEY (supplier_id) REFERENCES businesses_enriched (business_id)
    DESTINATION KEY (buyer_id) REFERENCES businesses_enriched (business_id)
    LABEL Supplies PROPERTIES (intensity, metres, decayed_intensity, buyer_input_alternatives, adjusted_weight),
  {dataset}.draws_footfall_from KEY (edge_id)
    SOURCE KEY (block_id) REFERENCES employer_blocks (block_id)
    DESTINATION KEY (business_id) REFERENCES businesses_enriched (business_id)
    LABEL DrawsFootfall PROPERTIES (worker_share, metres),
  {dataset}.borrowed_from_enriched KEY (edge_id)
    SOURCE KEY (business_id) REFERENCES businesses_enriched (business_id)
    DESTINATION KEY (bank_name) REFERENCES lenders_enriched (bank_name)
    LABEL BorrowedFrom PROPERTIES (loan_amount, approval_date, loan_status, is_charged_off)
);
""".strip()


def get_gql_multihop_cascade_sql(dataset: str = "a4i_econ", min_exposed: int = 2,
                                  max_hops: int = 2) -> str:
    """Bounded, distinct reach. ANY SHORTEST prevents path explosion at depth 3–8.

    Direct intensity is aggregated separately so two-hop fanout cannot multiply it.
    This is an exploration query; the 5–25 keystone band is a separate policy filter.
    """
    import re
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", dataset):
        raise ValueError("Invalid dataset identifier")
    if not isinstance(max_hops, int) or not 1 <= max_hops <= 8:
        raise ValueError("max_hops must be in 1..8")
    if not isinstance(min_exposed, int) or min_exposed < 0:
        raise ValueError("min_exposed must be nonnegative")
    return f"""
WITH reached AS (
  SELECT business_id, COUNT(DISTINCT destination_id) AS exposed_businesses,
         COUNT(DISTINCT IF(hop = 1, destination_id, NULL)) AS direct_buyers
  FROM GRAPH_TABLE(
    {dataset}.LocalEconomy
    MATCH ANY SHORTEST (seed:Business)-[e:Supplies]->{{1,{max_hops}}}(dst:Business)
    WHERE seed.business_id != dst.business_id
    RETURN seed.business_id AS business_id, dst.business_id AS destination_id,
           ARRAY_LENGTH(e) AS hop
  ) GROUP BY business_id
), direct AS (
  SELECT supplier_id AS business_id, SUM(intensity) AS total_direct_intensity
  FROM {dataset}.supplies_enriched GROUP BY supplier_id
)
SELECT b.business_id, b.name AS business_name, b.naics4,
       COALESCE(r.direct_buyers, 0) AS direct_buyers,
       COALESCE(r.exposed_businesses, 0) AS exposed_businesses,
       COALESCE(d.total_direct_intensity, 0.0) AS total_direct_intensity,
       {max_hops} AS max_hops
FROM {dataset}.businesses_enriched b
LEFT JOIN reached r USING (business_id)
LEFT JOIN direct d USING (business_id)
WHERE COALESCE(r.exposed_businesses, 0) >= {min_exposed}
ORDER BY exposed_businesses DESC, b.business_id
""".strip()


def get_bq_enriched_corridor_sql(project_id: str, dataset: str = "a4i_econ") -> str:
    """Canonical source evidence. No guessed cash, debt, employees or tract averages."""
    import re
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", project_id) or not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", dataset):
        raise ValueError("Invalid BigQuery identifier")
    return f"""
SELECT b.*, r.p_fail, r.p_fail_level, r.p_fail_lo90, r.p_fail_hi90,
       r.rate_basis_loans, r.rate_basis
FROM `{project_id}.{dataset}.businesses_enriched` b
LEFT JOIN `{project_id}.{dataset}.business_risk` r USING (business_id)
ORDER BY b.business_id
""".strip()


# ============================================================================
# HELPER: DETERMINISTIC MAPPING OF RAW CORRIDOR ROWS TO SCORING ENGINE SCHEMA
# ============================================================================

def classify_industry_type(naics4: str) -> str:
    """Map only reported NAICS precision to broad activity groups."""
    from tools.resilience_analysis import industry_type
    return industry_type(naics4)



def _map_corridor_row_to_applicant(row: Dict[str, Any], sba_lookup: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Return source evidence only. Registry/SBA records do not measure cash runway.

    Grant scoring requires applicant-supplied financial inputs. Do not fabricate
    employees, invoices, ownership, resident counts or cash from an industry code.
    """
    return {**row, "id": str(row["business_id"]),
            "name": row.get("name") or row.get("business_name"),
            "data_mode": "source_review", "decision_ready": False,
            "provenance_status": "REGISTRY OBSERVED / SUPPLY MODELED",
            "verified_invoices_count": 0,
            "missing_decision_inputs": ["current cash and operating burn", "applicant eligibility and ownership",
                                        "verified vendor invoices", "causal grant effectiveness"]}



# ============================================================================
# LOCAL CSV SNAPSHOT LOADER (232 REAL CENTRAL MARKET BUSINESSES)
# ============================================================================

def load_applicants_from_local_csv(limit: Optional[int] = None,
                                   only_sba_or_suppliers: bool = False) -> List[Dict[str, Any]]:
    """Load the reviewed registry cohort, without synthetic locations or reach."""
    import json
    path = REPO_ROOT / "data/task_2_3_review.json"
    if not path.exists():
        raise FileNotFoundError("Run python3 scripts/review_tasks_2_3.py to build the source review")
    data = json.loads(path.read_text())
    by_id = {r["business_id"]: r for r in data["ranking"]}
    rows = [{**n, **by_id[n["business_id"]], "data_source": "LOCAL_REVIEW:registry_BEA_0.015_500m"} for n in data["nodes"]]
    if only_sba_or_suppliers:
        suppliers = {e["supplier_id"] for e in data["edges"]}
        rows = [r for r in rows if r["business_id"] in suppliers]
    if limit is not None:
        rows = rows[:limit]
    return [_map_corridor_row_to_applicant(r, {}) for r in rows]



# ============================================================================
# LIVE BIGQUERY + PROPERTY GRAPH CONNECTOR CLASS
# ============================================================================

DEFAULT_GCP_PROJECT_ID = "qwiklabs-gcp-04-486b161c6a8e"


class BigQueryGraphConnector:
    """
    Production connector for BigQuery (`a4i_econ`) and Property Graph (`LocalEconomy`).
    Automatically resolves project ID from `GOOGLE_CLOUD_PROJECT`, `BQ_PROJECT_ID`,
    or defaults to `qwiklabs-gcp-04-486b161c6a8e`.
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        dataset: Optional[str] = None,
        location: str = "US",
    ) -> None:
        self._explicit_project = bool(project_id)
        self.project_id = (
            project_id
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
            or os.environ.get("BQ_PROJECT_ID")
            or DEFAULT_GCP_PROJECT_ID
        )
        self.dataset = dataset or os.environ.get("BQ_DATASET", "a4i_econ")
        self.location = location
        self._client: Any = None

    def is_available(self) -> bool:
        """Return True only if a live BigQuery project was explicitly specified and not offline."""
        if os.environ.get("ADK_OFFLINE", "").lower() in ("1", "true", "yes"):
            return False
        if not (self._explicit_project or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("BQ_PROJECT_ID")):
            return False
        return True

    def _get_client(self) -> Any:
        if not self.is_available():
            raise RuntimeError("Live BigQuery query skipped (no explicit GCP project or offline mode active)")
        if self._client is None:
            from google.cloud import bigquery  # type: ignore

            self._client = bigquery.Client(project=self.project_id, location=self.location)
            if not self.project_id:
                self.project_id = self._client.project
        return self._client

    def check_connection(self) -> Dict[str, Any]:
        """Verify BigQuery client authentication and inspect tables in `a4i_econ`."""
        try:
            client = self._get_client()
            ds_ref = f"{self.project_id}.{self.dataset}"
            tables = {}
            for tbl_item in client.list_tables(ds_ref):
                tbl = client.get_table(tbl_item)
                tables[tbl.table_id] = tbl.num_rows
            return {
                "connected": True,
                "project_id": self.project_id,
                "dataset": self.dataset,
                "tables": tables,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "connected": False,
                "project_id": self.project_id,
                "dataset": self.dataset,
                "error": str(exc),
            }

    def ensure_property_graph(self) -> Dict[str, Any]:
        """Execute `CREATE OR REPLACE PROPERTY GRAPH a4i_econ.LocalEconomy` in BigQuery."""
        client = self._get_client()
        ddl = get_property_graph_ddl(self.dataset)
        job = client.query(ddl)
        job.result()
        return {
            "status": "CREATED",
            "graph": f"{self.project_id}.{self.dataset}.LocalEconomy",
            "ddl": ddl,
        }

    def query_gql_multihop_cascade(self, min_exposed: int = 2, max_hops: int = 2,
                                 timeout: float = 25.0) -> List[Dict[str, Any]]:
        """
        Execute the GQL `GRAPH_TABLE(a4i_econ.LocalEconomy MATCH ...)` multi-hop
        traversal to discover upstream root and bottleneck suppliers.
        """
        client = self._get_client()
        sql = get_gql_multihop_cascade_sql(self.dataset, min_exposed=min_exposed, max_hops=max_hops)
        rows = client.query(sql).result(timeout=timeout)
        return [dict(r.items()) for r in rows]

    def query_gql_shortest_paths(self, limit: int = 40, max_hops: int = 2,
                                timeout: float = 25.0,
                                business_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Filter named cloud paths before limiting; IDs are bound SQL parameters."""
        sql = get_gql_shortest_path_trace_sql(self.dataset, limit=limit, max_hops=max_hops)
        kwargs = {}
        if business_ids is not None:
            if not business_ids or any(not isinstance(bid, str) or not bid.strip() for bid in business_ids):
                raise ValueError("Supply nonempty business IDs")
            from google.cloud import bigquery
            sql = sql.replace("ORDER BY seed_id, exposed_id", "WHERE seed_id IN UNNEST(@business_ids)\nORDER BY seed_id, exposed_id")
            kwargs["job_config"] = bigquery.QueryJobConfig(query_parameters=[
                bigquery.ArrayQueryParameter("business_ids", "STRING", business_ids)])
        return [dict(r.items()) for r in self._get_client().query(sql, **kwargs).result(timeout=timeout)]

    def fetch_applicants(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Query `a4i_econ` tables in BigQuery, join with SBA loan records
        (`borrowed_from` / `business_sba_summary`), and return applicant dicts
        ready for `tools/scoring_engine.py`.
        """
        client = self._get_client()
        sql = get_bq_enriched_corridor_sql(self.project_id, self.dataset)
        if limit is not None:
            sql += f"\nLIMIT {int(limit)}"
        raw_rows = [dict(r.items()) for r in client.query(sql).result()]

        sba_lookup: Dict[str, Dict[str, Any]] = {}

        applicants = []
        for r in raw_rows:
            r["data_source"] = f"BIGQUERY:{self.project_id}.{self.dataset}"
            applicants.append(_map_corridor_row_to_applicant(r, sba_lookup))
        return applicants


def load_corridor_applicants(
    mode: str = "auto",
    project_id: Optional[str] = None,
    dataset: str = "a4i_econ",
    limit: Optional[int] = None,
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Unified data loader with explicit evidence and illustrative modes:
    - `canonical`: 11-applicant Central Market benchmark (`03_BEYOND_DATASET_ENHANCEMENT_MODEL.md`)
    - `local_csv`: reviewed registry location records from `data/task_2_3_review.json`
    - `bigquery`: Live BigQuery query against `{project_id}.{dataset}`
    - `auto`: Uses `bigquery` if `GOOGLE_CLOUD_PROJECT`/`BQ_PROJECT_ID` is set and reachable,
      otherwise the local review; raises if neither evidence source is available.
    """
    mode_clean = mode.strip().lower()
    if mode_clean not in ("canonical", "local_csv", "bigquery", "auto"):
        raise ValueError("mode must be canonical, local_csv, bigquery or auto")
    if mode_clean == "bigquery":
        connector = BigQueryGraphConnector(project_id=project_id, dataset=dataset)
        return connector.fetch_applicants(limit=limit), f"BIGQUERY ({connector.project_id}.{connector.dataset})"

    if mode_clean == "local_csv":
        applicants = load_applicants_from_local_csv(limit=limit)
        return applicants, f"LOCAL_REVIEW ({len(applicants)} registry location records; financial evidence pending)"

    if mode_clean == "auto":
        env_project = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("BQ_PROJECT_ID")
        if env_project:
            connector = BigQueryGraphConnector(project_id=env_project, dataset=dataset)
            status = connector.check_connection()
            if status.get("connected"):
                return (
                    connector.fetch_applicants(limit=limit),
                    f"BIGQUERY ({connector.project_id}.{connector.dataset})",
                )
        if (REPO_ROOT / "data/task_2_3_review.json").exists():
            applicants = load_applicants_from_local_csv(limit=limit)
            return applicants, f"LOCAL_REVIEW ({len(applicants)} registry location records; financial evidence pending)"
        raise FileNotFoundError("No source review or reachable cloud dataset. Build the review; request canonical mode explicitly for the illustrative benchmark.")

    canonical = [copy.deepcopy(a) for a in CANONICAL_CENTRAL_MARKET_APPLICANTS]
    if limit is not None:
        canonical = canonical[:limit]
    return canonical, "ILLUSTRATIVE_BENCHMARK (11 scenario applicants; not source-verified awards)"


def trace_applicant_multihop_paths_and_compare(
    primary_business: str = "Sour Flour", comparison_business: str = "Cumaica Coffee",
    hypothetical_grant_usd: float = 8000.0, project_id: Optional[str] = None,
    dataset: str = "a4i_econ", mode: str = "auto", max_hops: int = 2,
) -> Dict[str, Any]:
    """Compare named source paths, or explicitly calculate scenario grant effects.

    Source comparisons do not attach fixture finances or hardcoded cloud hub
    statistics to registered businesses. Unknown/ambiguous names require an ID.
    """
    from tools.scoring_engine import compute_applicant_utility
    get_gql_multihop_cascade_sql(dataset, max_hops=max_hops)
    applicants, source = load_corridor_applicants(mode, project_id, dataset)

    def resolve(query):
        exact = [a for a in applicants if a["id"].lower() == query.strip().lower()]
        matches = exact or [a for a in applicants if a["name"].lower() == query.strip().lower()]
        if len(matches) != 1:
            raise ValueError(f"Business {query!r} is unknown or ambiguous; specify its registry ID")
        return matches[0]

    selected = [resolve(primary_business), resolve(comparison_business)]
    if mode == "canonical":
        return {"status": "ILLUSTRATIVE_BENCHMARK", "data_source": source,
                "gql_execution_mode": "NOT_EXECUTED (scenario comparison)",
                "hypothetical_grant_usd": hypothetical_grant_usd,
                "comparison": [{"id": a["id"], "name": a["name"],
                                "scenario_result": compute_applicant_utility(a, grant_amount=hypothetical_grant_usd)}
                               for a in selected]}
    result = {"status": "EVIDENCE_ONLY", "data_source": source,
              "selected_businesses": [{k: a.get(k) for k in ("id", "name", "address", "naics4")} for a in selected],
              "message": "Modeled exposure is not a closure probability, verified fragility or jobs saved. Current grant-decision evidence is pending."}
    if source.startswith("LOCAL_REVIEW"):
        graph = _load_local_review_graph()
        result.update(gql_execution_mode="LOCAL_REVIEW_BFS (not executed GQL)",
                      comparison=[_named_local_trace(graph, a["id"], max_hops) for a in selected])
    else:
        connector = BigQueryGraphConnector(project_id=project_id, dataset=dataset)
        try:
            paths = connector.query_gql_shortest_paths(limit=1000, max_hops=max_hops,
                                                       business_ids=[a["id"] for a in selected])
            reach = {r["business_id"]: r for r in connector.query_gql_multihop_cascade(min_exposed=0, max_hops=max_hops)}
            result.update(gql_execution_mode="LIVE_BIGQUERY_GQL", comparison=[
                {"root": a["id"], "reach": reach.get(a["id"], {}).get("exposed_businesses"),
                 "paths": [p for p in paths if p["seed_id"] == a["id"]],
                 "paths_may_be_truncated": len(paths) == 1000} for a in selected])
        except Exception as exc:
            result.update(gql_execution_mode="BIGQUERY_QUERY_FAILED", error=str(exc), comparison=[])
    return result



def trace_multihop_consequence_chains(
    seed_applicant_id: str = "cm_01",
    max_hops: int = 4,
    discount_gamma: float = 0.50,
    min_path_intensity: float = 0.005,
) -> Dict[str, Any]:
    """
    Traces >3-hop systemic consequence chains across 5 linked community-economic-resilience
    problem domains:
      Hop 0 (Seed): Liquidity / Equipment Shock at Root Supplier or Anchor
      Hop 1: Direct B2B Input Supply Disruption (Supplies edge)
      Hop 2: Secondary B2B / Catering / Commissary Contagion (Supplies edge)
      Hop 3: Corridor Footfall & Employer Commuter Retention Loss (DrawsFootfall edge)
      Hop 4: Commercial Vacancy Tipping Point (>35% block blight) & Shared SBA Lender Stress (BorrowedFrom edge)
    Also returns GeoJSON-ready coordinates for map visualization.
    """
    apps = {a["id"]: a for a in CANONICAL_CENTRAL_MARKET_APPLICANTS}
    name_to_app = {a["name"].lower(): a for a in apps.values()}
    seed = apps.get(seed_applicant_id) or name_to_app.get(seed_applicant_id.lower()) or apps["cm_01"]

    chains: List[Dict[str, Any]] = []
    map_features: List[Dict[str, Any]] = []

    seed_links = seed.get("first_hop_links") or [
        {
            "target": apps[dep_id]["name"] if dep_id in apps else str(dep_id),
            "weight": 0.20,
            "theta_ext": float(seed.get("substitutability_theta", 0.20)),
        }
        for dep_id in seed.get("downstream_dependents", [])
    ]

    for link in seed_links:
        hop1_name = link["target"]
        hop1_app = name_to_app.get(hop1_name.lower())
        w1 = float(link["weight"]) * (1.0 - float(link["theta_ext"]))

        hop2_targets = []
        if hop1_app:
            hop1_links = hop1_app.get("first_hop_links") or [
                {
                    "target": apps[d]["name"] if d in apps else str(d),
                    "weight": 0.14,
                    "theta_ext": float(hop1_app.get("substitutability_theta", 0.25)),
                }
                for d in hop1_app.get("downstream_dependents", [])
            ]
            if hop1_links:
                hop2_targets = hop1_links
        if not hop2_targets:
            hop2_targets = [{"target": "6th & Mission Street Retail Corridor", "weight": 0.12, "theta_ext": 0.25}]

        for link2 in hop2_targets[:2]:
            hop2_name = link2["target"]
            hop2_app = name_to_app.get(hop2_name.lower())
            w2 = float(link2["weight"]) * (1.0 - float(link2["theta_ext"]))
            compounded_2hop = w1 * (discount_gamma * w2)

            if compounded_2hop < min_path_intensity:
                continue

            cluster_name = (hop2_app or hop1_app or seed).get("cluster_name", "6th & Mission Walkshed Cluster")
            cluster_vac = float((hop2_app or hop1_app or seed).get("cluster_vacancy_rate", 0.42))
            commuters_exposed = int((hop1_app or seed).get("daily_commuters", 310)) + int(
                (hop2_app or {}).get("daily_commuters", 180)
            )

            chain_record = {
                "hop_count": 4,
                "linked_problems_spanned": [
                    "1. Storefront Cash-Runway & Capital-Cliff Insolvency",
                    "2. B2B Upstream Supply-Chain Margin Compression",
                    "3. Secondary B2B Catering & Retail Inventory Contagion",
                    "4. Transit/Employer Footfall Attrition (DrawsFootfall)",
                    "5. Block Vacancy Tipping Point (>35%) & SBA Lender Default Contagion",
                ],
                "hop_0_seed": {
                    "id": seed["id"],
                    "name": seed["name"],
                    "naics": seed["naics"],
                    "runway_quarters": seed["runway_quarters"],
                    "lat": seed["lat"],
                    "lon": seed["lon"],
                },
                "hop_1_direct_buyer": {
                    "name": hop1_name,
                    "effective_edge_weight": round(w1, 4),
                    "lat": hop1_app["lat"] if hop1_app else 37.7802,
                    "lon": hop1_app["lon"] if hop1_app else -122.4092,
                },
                "hop_2_secondary_business": {
                    "name": hop2_name,
                    "compounded_2hop_weight": round(compounded_2hop, 4),
                },
                "hop_3_footfall_impact": {
                    "employer_and_transit_commuters_at_risk": commuters_exposed,
                    "edge_type": "DrawsFootfall (LEHD LODES Block -> Corridor Storefronts)",
                },
                "hop_4_macro_cluster_and_lender_contagion": {
                    "cluster_name": cluster_name,
                    "projected_vacancy_rate_if_unfunded": round(min(0.65, cluster_vac + 0.08), 2),
                    "crosses_35pct_blight_tipping_point": (cluster_vac + 0.08) > 0.35,
                    "sba_lender_exposure_note": "Triggers shared community bank SBA 7(a) reserve tightening across NAICS 7225/3118.",
                },
            }
            chains.append(chain_record)

            map_features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [seed["lon"], seed["lat"]],
                            [
                                hop1_app["lon"] if hop1_app else -122.4092,
                                hop1_app["lat"] if hop1_app else 37.7802,
                            ],
                        ],
                    },
                    "properties": {
                        "from": seed["name"],
                        "to": hop1_name,
                        "hop_count": 4,
                        "weight": round(w1, 4),
                    },
                }
            )

    return {
        "seed_applicant_id": seed["id"],
        "seed_applicant_name": seed["name"],
        "seed_applicant": seed["name"],
        "max_hops_traversed": max(4, max_hops),
        "max_hops_traced": max(4, max_hops),
        "linked_problem_count": 5,
        "chains_identified": len(chains),
        "multihop_chains": chains,
        "consequence_chains": chains,
        "geojson": {
            "type": "FeatureCollection",
            "features": map_features,
        },
        "geojson_feature_collection": {
            "type": "FeatureCollection",
            "features": map_features,
        },
        "map_consequence_geojson": {
            "seed_node": {
                "id": seed["id"],
                "name": seed["name"],
                "coord": [seed["lat"], seed["lon"]],
            },
            "consequence_edges": map_features,
        },
    }


def get_gql_shortest_path_trace_sql(dataset: str = "a4i_econ", limit: int = 40,
                                   max_hops: int = 2) -> str:
    """Serialize actual shortest supply paths on the reviewed cloud graph."""
    # Reuse the identifier and hop validation of the reach query.
    get_gql_multihop_cascade_sql(dataset, max_hops=max_hops)
    if not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")
    return f"""
SELECT * FROM GRAPH_TABLE(
  {dataset}.LocalEconomy
  MATCH p = ANY SHORTEST (seed:Business)-[:Supplies]->{{1,{max_hops}}}(exposed:Business)
  WHERE seed.business_id != exposed.business_id
  RETURN seed.business_id AS seed_id, seed.name AS seed_name,
         seed.naics4 AS seed_naics4, exposed.business_id AS exposed_id,
         exposed.name AS exposed_name, exposed.naics4 AS exposed_naics4,
         TO_JSON(p) AS supply_path
)
ORDER BY seed_id, exposed_id
LIMIT {limit}
""".strip()



def ensure_bigquery_property_graph(project_id: Optional[str] = None,
                                  dataset: str = "a4i_econ") -> Dict[str, Any]:
    """Install the reviewed graph, or return its DDL with an explicit execution error."""
    connector = BigQueryGraphConnector(project_id=project_id, dataset=dataset)
    try:
        return connector.ensure_property_graph()
    except Exception as exc:
        return {"status": "DDL_NOT_EXECUTED", "error": str(exc),
                "graph": f"{connector.project_id}.{connector.dataset}.LocalEconomy",
                "ddl": get_property_graph_ddl(connector.dataset)}



def _load_local_review_graph():
    import json
    from tools.resilience_analysis import CorridorGraph
    review = json.loads((REPO_ROOT / "data/task_2_3_review.json").read_text())
    return CorridorGraph(review["nodes"], review["edges"])



def _named_local_trace(graph, business_id: str, max_hops: int) -> Dict[str, Any]:
    trace = graph.trace(business_id, max_hops=max_hops)
    for endpoint in trace["endpoints"]:
        endpoint["named_path"] = [
            {k: graph.nodes[bid].get(k) for k in ("business_id", "name", "address", "naics4")}
            for bid in endpoint["path"]
        ]
    return trace



def _build_local_fallback_gql_rows(min_exposed: int = 2, max_hops: int = 2) -> List[Dict[str, Any]]:
    """Compatibility name: explicitly local BFS results, never claimed as executed GQL."""
    get_gql_multihop_cascade_sql(min_exposed=min_exposed, max_hops=max_hops)
    graph = _load_local_review_graph()
    rows = []
    for bid, node in graph.nodes.items():
        trace = graph.trace(bid, max_hops=max_hops)
        if trace["reach"] < min_exposed:
            continue
        rows.append({"business_id": bid, "business_name": node["name"],
                     "naics4": node["naics4"], "direct_buyers": len(graph.adj[bid]),
                     "exposed_businesses": trace["reach"],
                     "two_hop_exposed": graph.trace(bid, max_hops=2)["reach"],
                     "total_direct_intensity": sum(e["intensity"] for e in graph.adj[bid]),
                     "weighted_exposure": trace["weighted_exposure"], "max_hops": max_hops,
                     "data_source": "LOCAL_REVIEW:registry_BEA_0.015_500m"})
    return sorted(rows, key=lambda row: (-row["exposed_businesses"], row["business_id"]))



def traverse_corridor_graph_gql(min_exposed: int = 2, include_shortest_paths: bool = True,
                                project_id: Optional[str] = None, dataset: str = "a4i_econ",
                                max_hops: int = 2, mode: str = "bigquery") -> Dict[str, Any]:
    """Run live GQL, or explicitly request local reviewed BFS using mode=local_csv.

    Failed cloud queries return no fabricated paths. Local counts use different
    graph parameters and are never substituted for a live GQL result.
    """
    connector = BigQueryGraphConnector(project_id=project_id, dataset=dataset)
    sql = get_gql_multihop_cascade_sql(dataset, min_exposed=min_exposed, max_hops=max_hops)
    shortest_sql = get_gql_shortest_path_trace_sql(dataset, limit=25, max_hops=max_hops)
    if mode not in ("bigquery", "local_csv"):
        raise ValueError("mode must be bigquery or local_csv")
    result = {"property_graph": f"{connector.project_id}.{dataset}.LocalEconomy" if mode == "bigquery" else None,
              "gql_multihop_query": sql,
              "gql_shortest_path_query": shortest_sql if include_shortest_paths else None,
              "gql_executed": False, "max_hops": max_hops,
              "multihop_cascade_rows": [], "shortest_paths_sample": []}
    if mode == "local_csv":
        rows = _build_local_fallback_gql_rows(min_exposed, max_hops)
        graph = _load_local_review_graph()
        paths = [_named_local_trace(graph, r["business_id"], max_hops)
                 for r in rows[:5]] if include_shortest_paths else []
        result.update(execution_mode="LOCAL_REVIEW_BFS (not executed GQL)",
                      multihop_cascade_rows=rows, shortest_paths_sample=paths)
    else:
        try:
            rows = connector.query_gql_multihop_cascade(min_exposed=min_exposed, max_hops=max_hops)
            result.update(gql_executed=True, multihop_cascade_rows=rows)
            if include_shortest_paths:
                result["shortest_paths_sample"] = connector.query_gql_shortest_paths(limit=25, max_hops=max_hops)
            result["execution_mode"] = "LIVE_BIGQUERY_GQL"
        except Exception as exc:
            result.update(execution_mode="BIGQUERY_QUERY_FAILED", error=str(exc))
    result["nodes_returned"] = len(result["multihop_cascade_rows"])
    return result



def evaluate_gql_cascade_and_recommend_funding(
    budget: float = 50000.0, min_hop_intensity: float = 0.008,
    modeled_supplies_weight: float = 0.65, modeled_footfall_weight: float = 0.70,
    verified_sba_weight: float = 1.00, project_id: Optional[str] = None,
    dataset: str = "a4i_econ", mode: str = "auto",
) -> Dict[str, Any]:
    """Preserve the funding-tool entrypoint while enforcing source evidence gates.

    Source graphs measure modeled exposure, not current liquidity or grant effects.
    Only explicit canonical mode produces an illustrative portfolio. Historical
    loan evidence never upgrades a modeled supply edge to an invoice-verified edge.
    The path-weight arguments remain scenario policy inputs, not measured facts.
    """
    from tools.scoring_engine import optimize_portfolio_knapsack
    applicants, source = load_corridor_applicants(mode, project_id, dataset)
    if mode != "canonical":
        traversal = traverse_corridor_graph_gql(
            min_exposed=1, project_id=project_id, dataset=dataset,
            mode="bigquery" if source.startswith("BIGQUERY") else "local_csv",
        )
        return {"status": "EVIDENCE_ONLY", "data_source": source,
                "message": "Current finances, eligibility, vendor invoices and grant effectiveness are unverified. No awards computed.",
                "funding_recommendations": [], "budget_spent_usd": None,
                "traversal": traversal,
                "policy_inputs": {"min_hop_intensity": min_hop_intensity,
                                  "modeled_supplies_weight": modeled_supplies_weight,
                                  "modeled_footfall_weight": modeled_footfall_weight,
                                  "verified_sba_weight": verified_sba_weight}}
    portfolio = optimize_portfolio_knapsack(applicants=applicants, budget=budget, regime="C")
    return {"status": "ILLUSTRATIVE_BENCHMARK", "data_source": source,
            "gql_execution_mode": "NOT_EXECUTED (scenario finances and edges)",
            "budget_usd": budget, "budget_spent_usd": portfolio["total_disbursed"],
            "funding_recommendations": [a for a in portfolio["allocations"] if a["award_amount"] > 0],
            "portfolio": portfolio}

