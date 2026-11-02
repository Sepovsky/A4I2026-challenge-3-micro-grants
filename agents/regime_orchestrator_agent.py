"""
Regime Stress-Test & Orchestrator Agent (`agents/regime_orchestrator_agent.py`).

Coordinates the 3 specialized evaluation agents:
  1. Supply & Provenance Agent (`Supply_Provenance_Agent`)
  2. Runway, Sector & Purity Agent (`Runway_Sector_Purity_Agent`)
  3. Spatial Foot-Traffic & Human-Impact Agent (`Spatial_Human_Impact_Agent`)

The deterministic pipeline evaluates supplied scenarios and returns source-only
records without awards. Live graph tools are separate explicit calls. Allocation
is a budgeted priority heuristic; sensitivity is sampled and reports are drafts.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from ADK.adk_context_loader import (
    build_system_prompt_with_adk_docs,
    get_agent_rubric,
    get_context_audit_summary,
    get_red_team_defenses,
    get_scoring_formulas,
)
from agents.runway_sector_purity_agent import (
    RunwaySectorPurityAgent,
    create_runway_sector_purity_adk_agent,
)
from agents.spatial_human_impact_agent import (
    SpatialHumanImpactAgent,
    create_spatial_human_impact_adk_agent,
)
from agents.supply_provenance_agent import (
    SupplyProvenanceAgent,
    create_supply_provenance_adk_agent,
)
from tools.bigquery_connector import (
    ensure_bigquery_property_graph,
    evaluate_gql_cascade_and_recommend_funding,
    get_gql_multihop_cascade_sql,
    get_gql_shortest_path_trace_sql,
    get_property_graph_ddl,
    load_corridor_applicants,
    trace_applicant_multihop_paths_and_compare,
    traverse_corridor_graph_gql,
)
from tools.compliance_reporter import (
    evaluate_red_team_compliance,
    format_red_team_compliance_report_markdown,
)
from tools.mcp_bigquery_toolset import (
    get_google_managed_bigquery_mcp_toolsets,
    get_mcp_bigquery_server_status,
)
from tools.scoring_engine import (
    audit_context_and_simulate_what_if,
    compute_applicant_utility,
    compute_sensitivity_and_robust_awardees,
    evaluate_all_applicants,
    evaluate_industry_variety,
    get_canonical_applicants,
    jaccard_similarity,
    optimize_portfolio_knapsack,
    run_all_regimes_comparison,
)
from tools.resilience_analysis import analyze_corridor_impact, find_corridor_businesses, review_industry_variety, industry_variety


ORCHESTRATOR_BASE_PROMPT = """You are the Regime Stress-Test & Orchestrator Agent (Chief Municipal Economist)
for the San Francisco Central Market Micro-Grant ADK.
Evidence rule: ADK financial examples and legacy priors are illustrative scenarios.
For source_review records, use analyze_corridor_impact (1–8 hops) and review_industry_variety.
Call find_corridor_businesses to obtain a registry location ID by name/address before tracing.
cm_* IDs are illustrative scenario IDs, not registry keys. Check status == OK before
reporting tool reach; use candidate IDs to resolve unknown or ambiguous businesses.
Do not optimize grants when cash, current debt, eligibility or canonical rates are missing.
Read data/TASK_2_3_REVIEW.md for corrected source claims. Never promise jobs saved from reach.
You must NEVER perform arithmetic in prose. You orchestrate:
1. Supply & Provenance Agent (`supply_provenance_agent`)
2. Runway, Sector & Purity Agent (`runway_sector_purity_agent`)
3. Spatial Foot-Traffic & Human-Impact Agent (`spatial_human_impact_agent`)
and invoke deterministic optimization tools to compare Regimes A, B, and C under a $50,000 budget,
prevent partial-grant dilution on Indivisible Capital Cliffs, audit a 200m straight-line cluster radius proxy,
report sampled award stability, and produce a draft scenario report.
Never claim exact optimization, all-weight proofs, inspected documents or approved awards."""


class RegimeStressTestOrchestratorAgent:
    """
    End-to-end multi-agent pipeline orchestrator combining all 4 ADK modules and
    dynamically referencing `./ADK/DOCS/*.md` as its single source of truth.
    """

    def __init__(self, adk_dir: Optional[str] = None) -> None:
        self.name = "Regime_Stress_Test_Orchestrator_Agent"
        self.display_name = "Regime Stress-Test & Orchestrator Agent"
        self.agent_name = "regime_orchestrator_agent"
        self.adk_dir = adk_dir
        self.rubric = get_agent_rubric(self.agent_name, adk_dir=adk_dir)
        self.system_prompt = build_system_prompt_with_adk_docs(
            base_system_prompt=ORCHESTRATOR_BASE_PROMPT,
            adk_dir=adk_dir,
            agent_name=self.agent_name,
        )
        self.supply_agent = SupplyProvenanceAgent(adk_dir=adk_dir)
        self.runway_agent = RunwaySectorPurityAgent(adk_dir=adk_dir)
        self.spatial_agent = SpatialHumanImpactAgent(adk_dir=adk_dir)

    def evaluate(
        self,
        applicants: Optional[List[Dict[str, Any]]] = None,
        budget: float = 50000.0,
    ) -> Dict[str, Any]:
        """Alias for `run_pipeline` so all 4 deterministic agents share `.evaluate()`."""
        return self.run_pipeline(applicants=applicants, budget=budget)

    def run_pipeline(
        self,
        applicants: Optional[List[Dict[str, Any]]] = None,
        budget: float = 50000.0,
        preferred_regime: str = "C",
        weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Executes the complete 4-agent decision pipeline:
          Step 1: Dynamic Context Audit of `./ADK/DOCS/*.md`
          Step 2: Multi-Hop GQL Property Graph Traversal & Post-Traversal Decision Analysis
          Step 3: Supply & Provenance Agent Evaluation
          Step 4: Runway, Sector & Purity Agent Evaluation
          Step 5: Multi-Regime (A, B, C) Submodular Knapsack Optimization
          Step 6: Spatial Foot-Traffic & Human-Impact Agent Cluster Verification
          Step 7: Parameter Invariance & Simplex Robustness Stress-Test
          Step 8: 10-Vector Red-Team Compliance Report Generation
        """
        apps = applicants if applicants is not None else load_corridor_applicants(mode="auto")[0]

        if any(app.get("data_mode") == "source_review" for app in apps):
            return {
                "status": "EVIDENCE_ONLY",
                "industry_variety": {"loaded_records": industry_variety(apps),
                                     "local_review": review_industry_variety() if all(str(a.get("data_source", "")).startswith("LOCAL_REVIEW") for a in apps) else None},
                "message": "Source records lack current applicant financial and eligibility evidence. No grant awards computed.",
                "applicants": apps,
                "traversal_tool": "Local reviewed graph: analyze_corridor_impact(business_id, max_hops=1..8, direction=downstream|upstream). Cloud graph: BigQueryGraphConnector.query_gql_multihop_cascade(max_hops=1..8). Do not mix graph counts.",
            }

        context_audit = get_context_audit_summary(adk_dir=self.adk_dir)
        gql_decision_output = {
            "status": "ILLUSTRATIVE_BENCHMARK",
            "note": "This portfolio uses supplied scenario applicants. Call traverse_corridor_graph_gql explicitly for live paths; do not join cloud reach to fixture finances.",
        }
        supply_output = self.supply_agent.evaluate(applicants=apps)
        runway_output = self.runway_agent.evaluate(applicants=apps)

        regimes_comparison = run_all_regimes_comparison(applicants=apps, budget=budget, weights=weights)
        selected_portfolio = optimize_portfolio_knapsack(
            applicants=apps,
            budget=budget,
            regime=preferred_regime,
            weights=weights,
        )

        spatial_output = self.spatial_agent.evaluate(
            applicants=apps,
            funded_ids=selected_portfolio["funded_ids"],
        )
        sensitivity_output = compute_sensitivity_and_robust_awardees(
            applicants=apps,
            budget=budget,
        )
        compliance_audit = evaluate_red_team_compliance(
            portfolio_result=selected_portfolio,
            applicants=apps,
            adk_dir=self.adk_dir,
        )
        compliance_markdown = format_red_team_compliance_report_markdown(
            portfolio_result=selected_portfolio,
            applicants=apps,
            adk_dir=self.adk_dir,
        )

        return {
            "status": "MODELED_SCENARIO",
            "orchestrator": self.name,
            "orchestrator_id": self.agent_name,
            "display_name": self.display_name,
            "context_audit": context_audit,
            "gql_traversal_and_decision": gql_decision_output,
            "mcp_bigquery_status": get_mcp_bigquery_server_status(),
            "supply_agent_output": supply_output,
            "runway_agent_output": runway_output,
            "spatial_agent_output": spatial_output,
            "regimes_comparison": regimes_comparison,
            "selected_portfolio": selected_portfolio,
            "sensitivity_analysis": sensitivity_output,
            "red_team_compliance_audit": compliance_audit,
            "red_team_compliance_report_markdown": compliance_markdown,
        }


def create_orchestrator_adk_pipeline(
    model: str = "gemini-2.5-flash",
    adk_dir: Optional[str] = None,
    include_mcp_toolsets: bool = True,
) -> Any:
    """
    Constructs the root Google ADK `Agent` coordinating the 3 sub-agents, custom
    multi-hop GQL Property Graph traversal & decision tools, Google-managed BigQuery
    MCP toolsets, and Red-Team compliance tools.
    """
    from google.adk.agents import Agent

    supply_sub = create_supply_provenance_adk_agent(
        model=model, adk_dir=adk_dir, include_mcp_toolsets=include_mcp_toolsets
    )
    runway_sub = create_runway_sector_purity_adk_agent(model=model, adk_dir=adk_dir)
    spatial_sub = create_spatial_human_impact_adk_agent(model=model, adk_dir=adk_dir)

    prompt = build_system_prompt_with_adk_docs(
        base_system_prompt=ORCHESTRATOR_BASE_PROMPT,
        adk_dir=adk_dir,
        agent_name="regime_orchestrator_agent",
    )

    orchestrator_tools: List[Any] = [
        trace_applicant_multihop_paths_and_compare,
        audit_context_and_simulate_what_if,
        evaluate_industry_variety,
        ensure_bigquery_property_graph,
        traverse_corridor_graph_gql,
        evaluate_gql_cascade_and_recommend_funding,
        get_mcp_bigquery_server_status,
        compute_applicant_utility,
        evaluate_all_applicants,
        jaccard_similarity,
        optimize_portfolio_knapsack,
        run_all_regimes_comparison,
        compute_sensitivity_and_robust_awardees,
        evaluate_red_team_compliance,
        format_red_team_compliance_report_markdown,
        get_red_team_defenses,
        get_scoring_formulas,
        load_corridor_applicants,
        get_property_graph_ddl,
        get_gql_multihop_cascade_sql,
        get_gql_shortest_path_trace_sql,
        analyze_corridor_impact,
        find_corridor_businesses,
        review_industry_variety,
    ]
    if include_mcp_toolsets:
        orchestrator_tools.extend(get_google_managed_bigquery_mcp_toolsets())

    return Agent(
        name="Regime_Stress_Test_Orchestrator_Agent",
        model=model,
        description=(
            "Regime Stress-Test & Orchestrator Agent: Chief Municipal Economist & Multi-Agent "
            "Orchestrator for the Central Market Ecosystem & Demand-Anchored Micro-Grant ADK, "
            "powered by BigQuery Property Graph GQL multi-hop traversal and Google-managed "
            "BigQuery MCP tools."
        ),
        instruction=prompt,
        sub_agents=[supply_sub, runway_sub, spatial_sub],
        tools=orchestrator_tools,
    )


# ==============================================================================
# NAMED AGENT CATALOG & SELECTOR FUNCTIONS
# ==============================================================================

ADK_AGENTS_CATALOG: Dict[str, Dict[str, Any]] = {
    "Regime_Stress_Test_Orchestrator_Agent": {
        "name": "Regime_Stress_Test_Orchestrator_Agent",
        "agent_id": "Regime_Stress_Test_Orchestrator_Agent",
        "display_name": "Regime Stress-Test & Orchestrator Agent",
        "role": (
            "Root Coordinator: Synthesizes all 3 domain sub-agents, executes multi-regime "
            "knapsack optimization (Regimes A, B, C), computes parameter invariance bounds, "
            "and generates the 10-Vector Red-Team Compliance Report."
        ),
        "aliases": [
            "regime_stress_test_orchestrator_agent",
            "regime_orchestrator_agent",
            "orchestrator",
            "root",
            "all",
        ],
        "adk_factory": create_orchestrator_adk_pipeline,
        "deterministic_class": RegimeStressTestOrchestratorAgent,
    },
    "Supply_Provenance_Agent": {
        "name": "Supply_Provenance_Agent",
        "agent_id": "Supply_Provenance_Agent",
        "display_name": "Supply & Provenance Agent",
        "role": (
            "Sub-Agent 1: Traverses the BigQuery LocalEconomy Property Graph via multi-hop GQL, "
            "evaluates upstream parent/root suppliers, substitutability friction, NAICS 81 "
            "disaggregation, un-applied bottlenecks, and 1-invoice provenance verification gates."
        ),
        "aliases": [
            "supply_provenance_agent",
            "supply",
            "provenance",
        ],
        "adk_factory": create_supply_provenance_adk_agent,
        "deterministic_class": SupplyProvenanceAgent,
    },
    "Runway_Sector_Purity_Agent": {
        "name": "Runway_Sector_Purity_Agent",
        "agent_id": "Runway_Sector_Purity_Agent",
        "display_name": "Runway, Sector & Purity Agent",
        "role": (
            "Sub-Agent 2: Enforces Stage 0 Corporate Exclusion Gate, evaluates financial "
            "runway survival lift, structural viability gates, sector volatility multipliers, "
            "and small-business purity."
        ),
        "aliases": [
            "runway_sector_purity_agent",
            "runway",
            "purity",
            "sector",
        ],
        "adk_factory": create_runway_sector_purity_adk_agent,
        "deterministic_class": RunwaySectorPurityAgent,
    },
    "Spatial_Human_Impact_Agent": {
        "name": "Spatial_Human_Impact_Agent",
        "agent_id": "Spatial_Human_Impact_Agent",
        "display_name": "Spatial Foot-Traffic & Human-Impact Agent",
        "role": (
            "Sub-Agent 3: Enforces 200m spatial critical-mass cluster rules, evaluates "
            "Track 1 Community Anchor scores and Census Tract Equity Multipliers, and "
            "computes Total People Helped per Dollar."
        ),
        "aliases": [
            "spatial_human_impact_agent",
            "spatial",
            "human_impact",
            "people",
        ],
        "adk_factory": create_spatial_human_impact_adk_agent,
        "deterministic_class": SpatialHumanImpactAgent,
    },
}


def _resolve_agent_spec(agent_name: Optional[str] = None) -> Dict[str, Any]:
    if not agent_name:
        return ADK_AGENTS_CATALOG["Regime_Stress_Test_Orchestrator_Agent"]
    cleaned = agent_name.strip()
    if cleaned in ADK_AGENTS_CATALOG:
        return ADK_AGENTS_CATALOG[cleaned]
    lowered = cleaned.lower()
    for spec in ADK_AGENTS_CATALOG.values():
        if lowered == spec["name"].lower() or lowered in spec["aliases"]:
            return spec
    valid_names = ", ".join(ADK_AGENTS_CATALOG.keys())
    raise ValueError(f"Unknown ADK agent '{agent_name}'. Available agents: {valid_names}")


def list_available_agents() -> List[Dict[str, str]]:
    """Returns metadata for all 4 selectable named ADK agents."""
    return [
        {
            "name": spec["name"],
            "agent_id": spec["agent_id"],
            "display_name": spec["display_name"],
            "role": spec["role"],
        }
        for spec in ADK_AGENTS_CATALOG.values()
    ]


def select_adk_agent(
    agent_name: Optional[str] = None,
    model: str = "gemini-2.5-flash",
    adk_dir: Optional[str] = None,
) -> Any:
    """
    Constructs and returns the selected Google ADK `Agent` instance by name or alias.
    Defaults to `Regime_Stress_Test_Orchestrator_Agent`.
    """
    spec = _resolve_agent_spec(agent_name)
    factory: Callable[..., Any] = spec["adk_factory"]
    return factory(model=model, adk_dir=adk_dir)


def select_deterministic_agent(
    agent_name: Optional[str] = None,
    adk_dir: Optional[str] = None,
) -> Any:
    """
    Constructs and returns the selected deterministic Python agent evaluator by name or alias.
    Defaults to `RegimeStressTestOrchestratorAgent`.
    """
    spec = _resolve_agent_spec(agent_name)
    cls = spec["deterministic_class"]
    return cls(adk_dir=adk_dir)
