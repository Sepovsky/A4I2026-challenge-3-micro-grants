"""
Deterministic Math & Tool Engine (`tools/scoring_engine.py`).

Implements every mathematical equation, logistic/bump function, piecewise threshold,
spatial critical-mass cluster constraint, provenance tag, and multi-regime knapsack
optimization rule defined inside `./ADK/DOCS/*.md` (`./ADK/docs/*.md`).

STRICT OPERATIONAL INVARIANT:
Zero LLM prose arithmetic is permitted. Agents must invoke these pure, deterministic
Python functions for all scoring, survival lift, cascade, purity, spatial, and
portfolio allocation calculations.
"""

from __future__ import annotations

import copy
import math
from typing import Any, Dict, List, Optional, Tuple


# ==============================================================================
# PROVENANCE TAG CONSTANTS (Vector 1: Inferred vs. Actual Supply Links)
# ==============================================================================

PROVENANCE_MODELED = "[MODELED: National Input-Output Benchmark + Spatial Gravity]"
PROVENANCE_VERIFIED = "[VERIFIED: Commercial Invoice / Accounts Payable Submission]"

# Non-Main Street Corporate Exclusion NAICS 4-Digit Set (Dimension 4 & Stage 0 Gate)
EXCLUDED_CORPORATE_NAICS4 = {"3361", "3342", "3254", "5182", "5415"}

# NAICS 81 4-Digit B2B Disaggregation Rules (Vector 8)
NAICS81_ALLOWED_B2B = {"8113", "8123"}  # Commercial Machinery Repair, Industrial Linen
NAICS81_STRIPPED_B2B = {"8121", "8129"}  # Personal Care Salons, Parking Garages


# ==============================================================================
# CANONICAL CENTRAL MARKET APPLICANT DATASET (Table 9.1 & Showcase Ground Truth)
# ==============================================================================

CANONICAL_CENTRAL_MARKET_APPLICANTS: List[Dict[str, Any]] = [
    {
        "id": "cm_01",
        "name": "Sour Flour",
        "category": "Artisan Bakery & Commissary",
        "address": "1182 Market St",
        "lat": 37.7793,
        "lon": -122.4148,
        "cluster_id": "mid_market_7th_8th",
        "cluster_name": "Mid-Market & 7th/8th Street Walkshed Cluster",
        "cluster_vacancy_rate": 0.38,
        "naics": "3118",
        "requested_amount": 10000.0,
        "liquid_cash": 8000.0,
        "burn_rate": 10000.0,
        "runway_quarters": 0.8,
        "sector_volatility": 1.15,
        "direct_employees": 6,
        "network_workers": 42,
        "daily_commuters": 180,
        "vulnerable_residents": 120,
        "small_biz_purity": 92.5,
        "location_count": 1,
        "ownership_type": "sole_or_family_local",
        "annual_revenue": 420000.0,
        "out_degree": 7,
        "in_degree": 1,
        "substitutability_theta": 0.15,  # Artisan sourdough starter & daily par-baked bread
        "parent_supplier_weight": 2.14,
        "cascade_score": 96.2,
        "anchor_score": 48.0,
        "equity_multiplier": 1.38,
        "tract_id": "06075012502",
        "tract_poverty_rate": 0.34,
        "tract_zero_vehicle_share": 0.68,
        "shock_category": "Category 1: Indivisible Capital Cliff",
        "shock_description": "Commercial deck oven replacement & flour mill motor overhaul ($9,800 indivisible invoice)",
        "provenance_status": PROVENANCE_VERIFIED,
        "verified_invoices_count": 3,
        "downstream_dependents": ["cm_04", "cm_05", "cm_06", "cm_07", "cafe_civic_1", "deli_market_2", "bistro_8th_3"],
        "upstream_suppliers": ["central_milling_ca", "sf_restaurant_equip_repair"],
        "eligible": True,
        "storefront_certified": True,
        "institutional_ownership_pct": 0.0,
    },
    {
        "id": "cm_02",
        "name": "Cumaica Coffee",
        "category": "Coffee Roasting & Maker",
        "address": "1398 Mission St",
        "lat": 37.7752,
        "lon": -122.4162,
        "cluster_id": "mid_market_7th_8th",
        "cluster_name": "Mid-Market & 7th/8th Street Walkshed Cluster",
        "cluster_vacancy_rate": 0.38,
        "naics": "3119",
        "requested_amount": 10000.0,
        "liquid_cash": 9900.0,
        "burn_rate": 9000.0,
        "runway_quarters": 1.1,
        "sector_volatility": 1.10,
        "direct_employees": 8,
        "network_workers": 38,
        "daily_commuters": 420,
        "vulnerable_residents": 90,
        "small_biz_purity": 88.0,
        "location_count": 2,
        "ownership_type": "family_local",
        "annual_revenue": 540000.0,
        "out_degree": 6,
        "in_degree": 1,
        "substitutability_theta": 0.20,  # Proprietary Central Market micro-lot roast profile
        "parent_supplier_weight": 2.08,
        "cascade_score": 94.5,
        "anchor_score": 46.5,
        "equity_multiplier": 1.35,
        "tract_id": "06075017601",
        "tract_poverty_rate": 0.29,
        "tract_zero_vehicle_share": 0.62,
        "shock_category": "Category 1: Indivisible Capital Cliff",
        "shock_description": "Commercial roaster afterburner emissions compliance unit ($10,000 indivisible equipment)",
        "provenance_status": PROVENANCE_VERIFIED,
        "verified_invoices_count": 2,
        "downstream_dependents": ["cm_03", "cm_04", "cm_05", "cafe_mission_4", "bakery_9th_5", "kiosk_civic_6"],
        "upstream_suppliers": ["sf_restaurant_equip_repair", "golden_gate_linen_supply"],
        "eligible": True,
        "storefront_certified": True,
        "institutional_ownership_pct": 0.0,
    },
    {
        "id": "cm_03",
        "name": "Central Market Corner Grocer",
        "category": "Essential Grocery & Bodega",
        "address": "1028 Market St",
        "lat": 37.7812,
        "lon": -122.4112,
        "cluster_id": "sixth_and_market_mission",
        "cluster_name": "6th & Market / Mission High-Risk Walkshed Cluster",
        "cluster_vacancy_rate": 0.41,
        "naics": "4451",
        "requested_amount": 10000.0,
        "liquid_cash": 7200.0,
        "burn_rate": 12000.0,
        "runway_quarters": 0.6,
        "sector_volatility": 0.85,
        "direct_employees": 4,
        "network_workers": 12,
        "daily_commuters": 450,
        "vulnerable_residents": 650,
        "small_biz_purity": 96.0,
        "location_count": 1,
        "ownership_type": "sole_or_family_local",
        "annual_revenue": 310000.0,
        "out_degree": 0,
        "in_degree": 3,
        "substitutability_theta": 0.0,
        "parent_supplier_weight": 1.00,
        "cascade_score": 0.0,
        "anchor_score": 98.5,
        "equity_multiplier": 1.46,
        "tract_id": "06075012501",
        "tract_poverty_rate": 0.39,
        "tract_zero_vehicle_share": 0.72,
        "is_sole_essential_within_400m": True,
        "snap_ebt_certified": True,
        "shock_category": "Category 1: Indivisible Capital Cliff",
        "shock_description": "Walk-in dairy/produce compressor replacement & 3-day commercial lease cure ($10,000 indivisible)",
        "provenance_status": PROVENANCE_VERIFIED,
        "verified_invoices_count": 1,
        "downstream_dependents": [],
        "upstream_suppliers": ["cm_02", "sf_produce_terminal", "sf_restaurant_equip_repair"],
        "eligible": True,
        "storefront_certified": True,
        "institutional_ownership_pct": 0.0,
    },
    {
        "id": "cm_04",
        "name": "G.Rabbit",
        "category": "Full-Service Dining",
        "address": "90 7th St",
        "lat": 37.7790,
        "lon": -122.4119,
        "cluster_id": "mid_market_7th_8th",
        "cluster_name": "Mid-Market & 7th/8th Street Walkshed Cluster",
        "cluster_vacancy_rate": 0.38,
        "naics": "7225",
        "requested_amount": 10000.0,
        "liquid_cash": 9900.0,
        "burn_rate": 11000.0,
        "runway_quarters": 0.9,
        "sector_volatility": 1.25,
        "direct_employees": 12,
        "network_workers": 18,
        "daily_commuters": 320,
        "vulnerable_residents": 140,
        "small_biz_purity": 74.5,
        "location_count": 1,
        "ownership_type": "local_llc",
        "annual_revenue": 680000.0,
        "out_degree": 2,
        "in_degree": 3,
        "substitutability_theta": 0.35,
        "parent_supplier_weight": 1.12,
        "cascade_score": 64.0,
        "anchor_score": 71.0,
        "equity_multiplier": 1.32,
        "tract_id": "06075017601",
        "tract_poverty_rate": 0.28,
        "tract_zero_vehicle_share": 0.60,
        "shock_category": "Category 2: Flexible Working Capital Bridge",
        "shock_description": "Shared kitchen utility arrears & inventory restocking ($5,000 scalable bridge + landlord matching)",
        "provenance_status": PROVENANCE_MODELED,
        "verified_invoices_count": 1,
        "downstream_dependents": ["cm_05", "catering_soma_1"],
        "upstream_suppliers": ["cm_01", "cm_02", "golden_gate_linen_supply"],
        "eligible": True,
        "storefront_certified": True,
        "institutional_ownership_pct": 0.0,
    },
    {
        "id": "cm_05",
        "name": "Monarch Beverage Catering LLC",
        "category": "Beverage Catering & Commissary",
        "address": "101 6th St",
        "lat": 37.7804,
        "lon": -122.4094,
        "cluster_id": "sixth_and_market_mission",
        "cluster_name": "6th & Market / Mission High-Risk Walkshed Cluster",
        "cluster_vacancy_rate": 0.41,
        "naics": "7223",
        "requested_amount": 10000.0,
        "liquid_cash": 9500.0,
        "burn_rate": 9500.0,
        "runway_quarters": 1.0,
        "sector_volatility": 1.20,
        "direct_employees": 7,
        "network_workers": 16,
        "daily_commuters": 150,
        "vulnerable_residents": 80,
        "small_biz_purity": 85.0,
        "location_count": 1,
        "ownership_type": "local_llc",
        "annual_revenue": 460000.0,
        "out_degree": 3,
        "in_degree": 2,
        "substitutability_theta": 0.30,
        "parent_supplier_weight": 1.15,
        "cascade_score": 58.5,
        "anchor_score": 55.0,
        "equity_multiplier": 1.42,
        "tract_id": "06075017601",
        "tract_poverty_rate": 0.35,
        "tract_zero_vehicle_share": 0.69,
        "shock_category": "Category 2: Flexible Working Capital Bridge",
        "shock_description": "Cold-chain keg lines & commissary payroll bridge ($5,000 working capital tranche)",
        "provenance_status": PROVENANCE_VERIFIED,
        "verified_invoices_count": 1,
        "downstream_dependents": ["cm_06", "cm_07", "venue_6th_1"],
        "upstream_suppliers": ["cm_01", "cm_02", "sf_restaurant_equip_repair"],
        "eligible": True,
        "storefront_certified": True,
        "institutional_ownership_pct": 0.0,
    },
    {
        "id": "cm_06",
        "name": "Chico's Pizza",
        "category": "Pizzeria Storefront",
        "address": "131 6th St",
        "lat": 37.7799,
        "lon": -122.4089,
        "cluster_id": "sixth_and_market_mission",
        "cluster_name": "6th & Market / Mission High-Risk Walkshed Cluster",
        "cluster_vacancy_rate": 0.41,
        "naics": "7225",
        "requested_amount": 10000.0,
        "liquid_cash": 9800.0,
        "burn_rate": 14000.0,
        "runway_quarters": 0.7,
        "sector_volatility": 1.22,
        "direct_employees": 5,
        "network_workers": 8,
        "daily_commuters": 280,
        "vulnerable_residents": 310,
        "small_biz_purity": 91.0,
        "location_count": 1,
        "ownership_type": "sole_or_family_local",
        "annual_revenue": 390000.0,
        "out_degree": 1,
        "in_degree": 2,
        "substitutability_theta": 0.40,
        "parent_supplier_weight": 1.04,
        "cascade_score": 42.0,
        "anchor_score": 68.0,
        "equity_multiplier": 1.42,
        "tract_id": "06075017601",
        "tract_poverty_rate": 0.35,
        "tract_zero_vehicle_share": 0.69,
        "shock_category": "Category 2: Flexible Working Capital Bridge",
        "shock_description": "Late-night foot-traffic bridge & rent relief match on 6th St ($5,000 + landlord addendum)",
        "provenance_status": PROVENANCE_MODELED,
        "verified_invoices_count": 1,
        "downstream_dependents": ["late_night_workers_6th"],
        "upstream_suppliers": ["cm_01", "cm_05", "sf_restaurant_equip_repair"],
        "eligible": True,
        "storefront_certified": True,
        "institutional_ownership_pct": 0.0,
    },
    {
        "id": "cm_07",
        "name": "The Pawn Shop",
        "category": "Tapas Lounge & Evening Dining",
        "address": "993 Mission St",
        "lat": 37.7808,
        "lon": -122.4085,
        "cluster_id": "sixth_and_market_mission",
        "cluster_name": "6th & Market / Mission High-Risk Walkshed Cluster",
        "cluster_vacancy_rate": 0.41,
        "naics": "7225",
        "requested_amount": 10000.0,
        "liquid_cash": 9600.0,
        "burn_rate": 8000.0,
        "runway_quarters": 1.2,
        "sector_volatility": 1.22,
        "direct_employees": 9,
        "network_workers": 14,
        "daily_commuters": 210,
        "vulnerable_residents": 60,
        "small_biz_purity": 81.0,
        "location_count": 1,
        "ownership_type": "local_llc",
        "annual_revenue": 580000.0,
        "out_degree": 1,
        "in_degree": 2,
        "substitutability_theta": 0.45,
        "parent_supplier_weight": 1.02,
        "cascade_score": 38.0,
        "anchor_score": 62.0,
        "equity_multiplier": 1.36,
        "tract_id": "06075017601",
        "tract_poverty_rate": 0.31,
        "tract_zero_vehicle_share": 0.64,
        "shock_category": "Category 2: Flexible Working Capital Bridge",
        "shock_description": "Evening hospitality staffing & supplier payables bridge ($5,000 working capital tranche)",
        "provenance_status": PROVENANCE_MODELED,
        "verified_invoices_count": 1,
        "downstream_dependents": ["evening_arts_patrons_6th"],
        "upstream_suppliers": ["cm_01", "cm_05", "golden_gate_linen_supply"],
        "eligible": True,
        "storefront_certified": True,
        "institutional_ownership_pct": 0.0,
    },
    {
        "id": "cm_08",
        "name": "Central Market Community Health Clinic",
        "category": "Neighborhood Health & Legal Clinic",
        "address": "976 Mission St",
        "lat": 37.7810,
        "lon": -122.4081,
        "cluster_id": "sixth_and_market_mission",
        "cluster_name": "6th & Market / Mission High-Risk Walkshed Cluster",
        "cluster_vacancy_rate": 0.41,
        "naics": "6214",
        "requested_amount": 10000.0,
        "liquid_cash": 9900.0,
        "burn_rate": 4500.0,
        "runway_quarters": 2.2,
        "sector_volatility": 0.75,
        "direct_employees": 18,
        "network_workers": 24,
        "daily_commuters": 160,
        "vulnerable_residents": 920,
        "small_biz_purity": 62.0,
        "location_count": 1,
        "ownership_type": "nonprofit_501c3",
        "annual_revenue": 1200000.0,
        "out_degree": 0,
        "in_degree": 1,
        "substitutability_theta": 0.0,
        "parent_supplier_weight": 1.00,
        "cascade_score": 0.0,
        "anchor_score": 92.0,
        "equity_multiplier": 1.45,
        "tract_id": "06075017601",
        "tract_poverty_rate": 0.38,
        "tract_zero_vehicle_share": 0.70,
        "is_sole_essential_within_400m": True,
        "medi_cal_sliding_scale_certified": True,
        "shock_category": "Category 2: Flexible Working Capital Bridge",
        "shock_description": "2.2-quarter philanthropic runway; routed to SF CDBG / Non-Profit Sustainability Fund",
        "provenance_status": PROVENANCE_VERIFIED,
        "verified_invoices_count": 1,
        "downstream_dependents": [],
        "upstream_suppliers": ["golden_gate_linen_supply"],
        "eligible": True,
        "storefront_certified": True,
        "institutional_ownership_pct": 0.0,
        "alternate_funding_routing": "SF CDBG Non-Profit Public Services & DPH Clinic Stabilization Grant",
    },
    {
        "id": "cm_09",
        "name": "Steel + Lacquer",
        "category": "Personal Care Salon",
        "address": "14 10th St",
        "lat": 37.7759,
        "lon": -122.4158,
        "cluster_id": "mid_market_7th_8th",
        "cluster_name": "Mid-Market & 7th/8th Street Walkshed Cluster",
        "cluster_vacancy_rate": 0.38,
        "naics": "8121",
        "requested_amount": 10000.0,
        "liquid_cash": 10000.0,
        "burn_rate": 4000.0,
        "runway_quarters": 2.5,
        "sector_volatility": 0.95,
        "direct_employees": 5,
        "network_workers": 6,
        "daily_commuters": 65,
        "vulnerable_residents": 30,
        "small_biz_purity": 89.0,
        "location_count": 1,
        "ownership_type": "sole_or_family_local",
        "annual_revenue": 290000.0,
        "out_degree": 0,
        "in_degree": 1,
        "substitutability_theta": 0.60,
        "parent_supplier_weight": 1.00,
        "cascade_score": 0.0,  # Stripped of false NAICS 81 B2B edges per Vector 8
        "anchor_score": 54.0,
        "equity_multiplier": 1.22,
        "tract_id": "06075017601",
        "tract_poverty_rate": 0.22,
        "tract_zero_vehicle_share": 0.52,
        "shock_category": "Category 2: Flexible Working Capital Bridge",
        "shock_description": "2.5-quarter cash buffer; placed on Tier-3 Secondary Waitlist",
        "provenance_status": PROVENANCE_VERIFIED,
        "verified_invoices_count": 0,
        "downstream_dependents": [],
        "upstream_suppliers": ["golden_gate_linen_supply"],
        "eligible": True,
        "storefront_certified": True,
        "institutional_ownership_pct": 0.0,
    },
    {
        "id": "cm_10",
        "name": "WP Engine, Inc.",
        "category": "Enterprise Cloud Software",
        "address": "1161 Mission St",
        "lat": 37.7782,
        "lon": -122.4128,
        "cluster_id": "mid_market_7th_8th",
        "cluster_name": "Mid-Market & 7th/8th Street Walkshed Cluster",
        "cluster_vacancy_rate": 0.38,
        "naics": "5415",
        "requested_amount": 10000.0,
        "liquid_cash": 8000.0,
        "burn_rate": 1000.0,
        "runway_quarters": 8.0,
        "sector_volatility": 0.80,
        "direct_employees": 650,
        "network_workers": 200,
        "daily_commuters": 40,
        "vulnerable_residents": 0,
        "small_biz_purity": 0.0,
        "location_count": 8,
        "ownership_type": "corporate_vc_pe",
        "annual_revenue": 400000000.0,
        "out_degree": 12,
        "in_degree": 4,
        "substitutability_theta": 0.75,
        "parent_supplier_weight": 1.00,
        "cascade_score": 84.0,
        "anchor_score": 10.0,
        "equity_multiplier": 1.30,
        "tract_id": "06075017601",
        "tract_poverty_rate": 0.30,
        "tract_zero_vehicle_share": 0.62,
        "shock_category": "Disqualified Corporate Entity",
        "shock_description": "Stage 0 Gate Disqualification: NAICS 5415 Enterprise Software, 650 FTEs, PE/VC-backed",
        "provenance_status": PROVENANCE_MODELED,
        "verified_invoices_count": 0,
        "downstream_dependents": [],
        "upstream_suppliers": [],
        "eligible": False,
        "storefront_certified": False,
        "institutional_ownership_pct": 0.85,
    },
    {
        "id": "cm_11",
        "name": "Waymo LLC",
        "category": "Autonomous Vehicles",
        "address": "215 Taylor St",
        "lat": 37.7834,
        "lon": -122.4109,
        "cluster_id": "sixth_and_market_mission",
        "cluster_name": "6th & Market / Mission High-Risk Walkshed Cluster",
        "cluster_vacancy_rate": 0.41,
        "naics": "3361",
        "requested_amount": 10000.0,
        "liquid_cash": 7500.0,
        "burn_rate": 500.0,
        "runway_quarters": 15.0,
        "sector_volatility": 0.70,
        "direct_employees": 2500,
        "network_workers": 150,
        "daily_commuters": 10,
        "vulnerable_residents": 0,
        "small_biz_purity": 0.0,
        "location_count": 12,
        "ownership_type": "corporate_conglomerate",
        "annual_revenue": 1000000000.0,
        "out_degree": 15,
        "in_degree": 5,
        "substitutability_theta": 0.80,
        "parent_supplier_weight": 1.00,
        "cascade_score": 79.0,
        "anchor_score": 5.0,
        "equity_multiplier": 1.35,
        "tract_id": "06075012501",
        "tract_poverty_rate": 0.35,
        "tract_zero_vehicle_share": 0.68,
        "shock_category": "Disqualified Corporate Entity",
        "shock_description": "Stage 0 Gate Disqualification: NAICS 3361 Alphabet Subsidiary, 2,500 FTEs, Non-Storefront",
        "provenance_status": PROVENANCE_MODELED,
        "verified_invoices_count": 0,
        "downstream_dependents": [],
        "upstream_suppliers": [],
        "eligible": False,
        "storefront_certified": False,
        "institutional_ownership_pct": 1.00,
    },
]

# Un-applied in-corridor upstream nodes discovered via 2-hop reverse edge scan (Vector 9)
CORRIDOR_UNAPPLIED_SUPPLIERS: List[Dict[str, Any]] = [
    {
        "node_id": "sf_restaurant_equip_repair",
        "name": "Mid-Market Commercial Kitchen & Refrigeration Repair Co.",
        "address": "148 8th St",
        "naics": "8113",
        "in_corridor": True,
        "applied_for_grant": False,
        "supplied_applicant_ids": ["cm_01", "cm_02", "cm_03", "cm_05", "cm_06"],
        "estimated_runway_quarters": 0.75,
        "criticality_note": (
            "Supplies emergency refrigeration, deck oven, and espresso boiler maintenance to 5 "
            "Central Market applicants. Failure would freeze equipment repairs across the corridor."
        ),
    },
    {
        "node_id": "golden_gate_linen_supply",
        "name": "Stevenson Street Sanitary Linen & Apron Commissary",
        "address": "645 Stevenson St",
        "naics": "8123",
        "in_corridor": True,
        "applied_for_grant": False,
        "supplied_applicant_ids": ["cm_02", "cm_04", "cm_07", "cm_08", "cm_09"],
        "estimated_runway_quarters": 0.90,
        "criticality_note": (
            "Provides daily health-code mandated sanitary linen, towel, and apron laundering to "
            "5 Central Market dining, clinic, and personal care applicants."
        ),
    },
]


def get_canonical_applicants() -> List[Dict[str, Any]]:
    """Returns a deep copy of the canonical 11 Central Market applicant profiles."""
    return copy.deepcopy(CANONICAL_CENTRAL_MARKET_APPLICANTS)


# ==============================================================================
# STAGE 0: CORPORATE EXCLUSION GATE & NAICS 81 DISAGGREGATION (Vector 8 & Dim 4)
# ==============================================================================

def evaluate_corporate_exclusion_gate(
    naics_4: str,
    fte_count: float,
    location_count: int = 1,
    storefront_certified: bool = True,
    institutional_ownership_pct: float = 0.0,
    is_public_or_vc_backed: bool = False,
    explicit_eligible_flag: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Implements the Stage 0 Hard Corporate Exclusion Gate E_corp(i) in {0, 1}
    defined in `01_ARCHITECTURE_AND_TRIAGE_FRAMEWORK.md` (Section 2) and
    `03_BEYOND_DATASET_ENHANCEMENT_MODEL.md` (Dimension 4, Section 5.1).

    E_corp(i) = 0 if ANY of the following hold:
      1. NAICS_4 in {3361, 3342, 3254, 5182, 5415} and not StorefrontCertified
      2. FTE headcount W_i > 50 (SF Small Business Enterprise ceiling)
      3. Multi-unit chain count L_i > 3 locations
      4. Publicly traded / PE / VC-backed or >= 25% institutional parent ownership (FinCEN check)
      5. Non-storefront parking aggregator (NAICS 8129)
    """
    reasons: List[str] = []
    clean_naics = str(naics_4).strip()[:4]

    if clean_naics in EXCLUDED_CORPORATE_NAICS4 and not storefront_certified:
        reasons.append(
            f"Excluded Enterprise/Tech/Biotech/AV Sector (NAICS {clean_naics}) without physical storefront certification"
        )
    if clean_naics == "8129":
        reasons.append("Excluded Non-Storefront Off-Street Parking Lot/Garage Aggregator (NAICS 8129)")
    if fte_count > 50:
        reasons.append(f"Exceeds SF Small Business Enterprise 50-FTE ceiling (FTE={fte_count})")
    if location_count > 3:
        reasons.append(f"Exceeds 3-location independent chain ceiling (Locations={location_count})")
    if institutional_ownership_pct >= 0.25 or is_public_or_vc_backed:
        reasons.append(
            f"Institutional/Corporate/VC ownership ({institutional_ownership_pct*100:.0f}%) violates >=25% FinCEN Beneficial Ownership threshold"
        )
    if explicit_eligible_flag is False and not reasons:
        reasons.append("Flagged ineligible at Stage 0 Corporate Intake Gate")

    e_corp = 0 if reasons else 1
    return {
        "e_corp": e_corp,
        "eligible": e_corp == 1,
        "naics_4": clean_naics,
        "disqualification_reasons": reasons,
    }


def filter_naics_81_b2b_links(
    naics_4: str,
    raw_outgoing_b2b_weight: float,
) -> Dict[str, Any]:
    """
    Enforces Vector 8 Mandatory 4-Digit NAICS Disaggregation for 2-digit sector `81`
    ("Other Services"):
      - Only `8113` (Commercial & Industrial Machinery Repair) and `8123` (Industrial
        Linen & Laundry) are permitted to carry outgoing B2B supply weight.
      - `8129` (Parking Lots & Garages) and `8121` (Personal Care Salons) have their
        outgoing B2B supply weight stripped to 0.0.
    """
    clean_naics = str(naics_4).strip()[:4]
    if not clean_naics.startswith("81"):
        return {
            "naics_4": clean_naics,
            "adjusted_b2b_weight": raw_outgoing_b2b_weight,
            "b2b_stripped": False,
            "rule_applied": "Non-NAICS-81 sector; standard B2B edge rules apply.",
        }

    if clean_naics in NAICS81_ALLOWED_B2B:
        return {
            "naics_4": clean_naics,
            "adjusted_b2b_weight": raw_outgoing_b2b_weight,
            "b2b_stripped": False,
            "rule_applied": f"NAICS {clean_naics} verified as legitimate B2B repair/linen supplier under Vector 8.",
        }

    return {
        "naics_4": clean_naics,
        "adjusted_b2b_weight": 0.0,
        "b2b_stripped": True,
        "rule_applied": (
            f"NAICS {clean_naics} stripped of outgoing B2B supply weight (set to 0.0) per Vector 8 "
            "to prevent 2-digit BEA NAICS 81 aggregation leakage."
        ),
    }


# ==============================================================================
# DIMENSION 1: FINANCIAL BUFFER, RUNWAY & SURVIVAL LIFT (Vectors 3 & 4)
# ==============================================================================

def compute_quarterly_runway(liquid_cash: float, quarterly_burn_rate: float) -> float:
    """
    Computes baseline financial runway in quarters:
      r_i = C_i / kappa_i
    """
    if quarterly_burn_rate <= 0:
        raise ValueError("quarterly_burn_rate (kappa_i) must be strictly positive.")
    return max(0.0, float(liquid_cash) / float(quarterly_burn_rate))


def logistic_survival_probability(
    runway_quarters: float,
    k: float = 2.0,
    r_star: float = 1.0,
) -> float:
    """
    Computes baseline 2-quarter survival probability without intervention:
      P_0(r_i) = 1 / (1 + exp(-k * (r_i - r*)))
    where r* = 1.0 quarter is the critical survival inflection threshold and k = 2.0.
    """
    exponent = -k * (float(runway_quarters) - float(r_star))
    exponent = max(-60.0, min(60.0, exponent))
    return 1.0 / (1.0 + math.exp(exponent))


def marginal_survival_lift(
    runway_quarters: float,
    grant_amount: float = 10000.0,
    quarterly_burn_rate: float = 10000.0,
    k: float = 2.0,
    r_star: float = 1.0,
) -> float:
    """
    Computes Marginal Survival Lift from a micro-grant g_i:
      Delta r_i(g_i) = g_i / kappa_i
      Delta P(g_i, r_i) = P(r_i + Delta r_i) - P_0(r_i)
    """
    delta_r = float(grant_amount) / max(float(quarterly_burn_rate), 1.0)
    p_post = logistic_survival_probability(runway_quarters + delta_r, k=k, r_star=r_star)
    p_pre = logistic_survival_probability(runway_quarters, k=k, r_star=r_star)
    return max(0.0, p_post - p_pre)


def optimal_runway_inflection_point(
    grant_amount: float = 10000.0,
    quarterly_burn_rate: float = 10000.0,
    r_star: float = 1.0,
) -> float:
    """
    Implements Theorem 1 (Runway Inflection Optimality) from `03_BEYOND_DATASET_ENHANCEMENT_MODEL.md`:
      r_max = r* - Delta_r / 2
    """
    delta_r = float(grant_amount) / max(float(quarterly_burn_rate), 1.0)
    return float(r_star) - (delta_r / 2.0)


def structural_viability_gate(
    runway_quarters: float,
    quarterly_burn_rate: float,
    requested_amount: float = 10000.0,
    smooth: bool = False,
) -> float:
    """
    Implements the Structural Insolvency Floor Gate Theta_viable(r_i, kappa_i, R_i)
    from `02_RED_TEAM_AND_DEFENSE_PLAYBOOK.md` (Vector 3) and `03_BEYOND_DATASET_ENHANCEMENT_MODEL.md` (Eq. 2.5):
      Theta_viable = 0.10 if (r_i < 0.25 and kappa_i > 3 * R_i) else 1.00
    When `smooth=True`, replaces the hard 0.25q step cliff with a continuous logistic ramp.
    """
    if smooth:
        if quarterly_burn_rate > 3.0 * requested_amount:
            return 0.10 + 0.90 / (1.0 + math.exp(-20.0 * (float(runway_quarters) - 0.25)))
        return 1.00
    if runway_quarters < 0.25 and quarterly_burn_rate > 3.0 * requested_amount:
        return 0.10
    return 1.00


def runway_priority_score(
    runway_quarters: float,
    quarterly_burn_rate: float = 10000.0,
    requested_amount: float = 10000.0,
    k: float = 2.0,
    r_star: float = 1.0,
    peer_mean_burn_rate: float = 9500.0,
    peer_std_burn_rate: float = 2500.0,
    smooth: bool = False,
) -> Dict[str, Any]:
    """
    Computes the Non-Monotonic Survival Bell Curve score Phi_runway(r_i) in [0, 100]
    from `03_BEYOND_DATASET_ENHANCEMENT_MODEL.md` (Section 2.4) and Vector 3 & 4 triage gates:
      Phi_runway(r_i) = 100 * [4 * exp(-k*|r_i - r*|) / (1 + exp(-k*|r_i - r*|))^2] * Theta_viable
    """
    abs_diff = abs(float(runway_quarters) - float(r_star))
    exp_term = math.exp(-k * min(abs_diff, 30.0))
    bell_kernel = (4.0 * exp_term) / ((1.0 + exp_term) ** 2)
    theta_viable = structural_viability_gate(runway_quarters, quarterly_burn_rate, requested_amount, smooth=smooth)
    phi_score = 100.0 * bell_kernel * theta_viable

    delta_p = marginal_survival_lift(
        runway_quarters=runway_quarters,
        grant_amount=requested_amount,
        quarterly_burn_rate=quarterly_burn_rate,
        k=k,
        r_star=r_star,
    )

    if runway_quarters < 0.25:
        triage_zone = "WALKING_DEAD_INSOLVENT"
    elif 0.50 <= runway_quarters <= 1.50:
        triage_zone = "CRITICAL_TRIAGE_SWEET_SPOT"
    elif runway_quarters < 4.00:
        triage_zone = "MODERATE_BUFFER"
    else:
        triage_zone = "SELF_INSURING_BUFFER"

    burn_z_score = (quarterly_burn_rate - peer_mean_burn_rate) / max(peer_std_burn_rate, 1.0)
    burn_anomaly_flag = burn_z_score > 2.5

    return {
        "runway_quarters": runway_quarters,
        "p0_survival": logistic_survival_probability(runway_quarters, k=k, r_star=r_star),
        "marginal_survival_lift_delta_p": delta_p,
        "theta_viable": theta_viable,
        "phi_runway_score": phi_score,
        "triage_zone": triage_zone,
        "two_party_warrant_required": True,  # Vector 3 mandatory disbursement control
        "burn_rate_z_score": burn_z_score,
        "burn_rate_audit_flag_2_5_sigma": burn_anomaly_flag,
    }


# ==============================================================================
# DIMENSION 2: SECTOR VOLATILITY & MACROECONOMIC MARGIN DYNAMICS
# ==============================================================================

def sector_volatility_index(
    demand_elasticity: float,
    net_operating_margin: float,
    macro_shock_std: float,
    recovery_lag_quarters: float,
) -> float:
    """
    Computes the Sector Volatility & Fragility Index Omega_s in [0.5, 2.5]
    from `03_BEYOND_DATASET_ENHANCEMENT_MODEL.md` (Section 3.1):
      Omega_s = (epsilon_{d,s} / max(0.02, mu_s)) * sigma_macro * (1 + tau_{rec,s} / 4)
    """
    raw_omega = (
        (float(demand_elasticity) / max(0.02, float(net_operating_margin)))
        * float(macro_shock_std)
        * (1.0 + float(recovery_lag_quarters) / 4.0)
    )
    return max(0.5, min(2.5, raw_omega))


def cyclical_viability_factor(
    baseline_margin_trend: float,
    downturn_margin_compression: float,
    secular_disruption_discount: float,
    epsilon: float = 1e-4,
) -> float:
    """
    Computes the Cyclical vs. Structural Sector Adjustment Psi_s in [0, 1]
    from `03_BEYOND_DATASET_ENHANCEMENT_MODEL.md` (Section 3.2):
      Psi_s = (BaselineMarginTrend_s / (DownturnMarginCompression_s + eps)) * (1 - delta_{secular,s})
    """
    ratio = float(baseline_margin_trend) / (abs(float(downturn_margin_compression)) + epsilon)
    raw_psi = ratio * (1.0 - float(secular_disruption_discount))
    return max(0.0, min(1.0, raw_psi))


def sector_risk_multiplier(
    sector_volatility: float,
    volatility_weight: float = 0.25,
    mean_volatility: float = 1.0,
    std_volatility: float = 1.0,
    cyclical_viability: float = 1.0,
    clamp_bounds: bool = False,
) -> float:
    """
    Computes the Composite Sector Risk Multiplier rho_s from `03_BEYOND_DATASET_ENHANCEMENT_MODEL.md`
    (Section 3.3) and `verify_showcase.py`:
      rho_s = 1.0 + omega_vol * (((Omega_s - mean_Omega) / std_Omega) * Psi_s)
    With default mean_volatility=1.0, std_volatility=1.0, cyclical_viability=1.0, this simplifies
    to the exact canonical formula:
      rho_s = 1.0 + volatility_weight * (sector_volatility - 1.0)
    """
    z_val = (float(sector_volatility) - float(mean_volatility)) / max(float(std_volatility), 1e-6)
    rho = 1.0 + float(volatility_weight) * (z_val * float(cyclical_viability))
    if clamp_bounds:
        return max(0.70, min(1.35, rho))
    return rho


# ==============================================================================
# DIMENSION 3: TOTAL PEOPLE HELPED & CENSUS TRACT EQUITY MULTIPLIER
# ==============================================================================

def calculate_vulnerable_resident_reach(
    tract_population: float,
    poverty_rate: float,
    no_vehicle_rate: float,
    essential_category_weight: int = 1,
    corridor_same_naics_count: int = 1,
) -> float:
    """
    Computes Component D (Vulnerable Local Resident Access Reach R_i) from
    `03_BEYOND_DATASET_ENHANCEMENT_MODEL.md` (Section 4.1):
      R_i = Pop(Tract_i) * (PovertyRate_i * NoVehicleRate_i) * (K_essential(i) / N_corridor(naics_i))
    where K_essential(i) in {5 (grocery/clinic/pharmacy), 3 (prepared food/hardware/laundry), 1 (discretionary)}.
    """
    return (
        float(tract_population)
        * (float(poverty_rate) * float(no_vehicle_rate))
        * (float(essential_category_weight) / max(1.0, float(corridor_same_naics_count)))
    )


def calculate_total_people_helped(
    direct_employees_fte: float,
    network_workers: float,
    daily_commuters: float,
    vulnerable_residents: float,
    direct_employees_pte: float = 0.0,
    w_W: float = 1.00,
    w_net: float = 0.50,
    w_C: float = 0.05,
    w_R: float = 0.20,
) -> Dict[str, float]:
    """
    Computes Total People Helped (H_i) across all 4 human beneficiary channels
    defined in `03_BEYOND_DATASET_ENHANCEMENT_MODEL.md` (Section 4.1):
      W_i = FTE_i + 0.50 * PTE_i
      H_i = w_W * W_i + w_net * W_network(i) + w_C * C_i + w_R * R_i
    """
    w_i = float(direct_employees_fte) + 0.50 * float(direct_employees_pte)
    c_workers = w_W * w_i
    c_network = w_net * float(network_workers)
    c_commuters = w_C * float(daily_commuters)
    c_residents = w_R * float(vulnerable_residents)
    total_h = c_workers + c_network + c_commuters + c_residents
    raw_daily_headcount = w_i + float(network_workers) + float(daily_commuters) + float(vulnerable_residents)

    return {
        "direct_workers_fte_equiv": w_i,
        "weighted_direct_workers": c_workers,
        "weighted_network_workers": c_network,
        "weighted_commuters": c_commuters,
        "weighted_vulnerable_residents": c_residents,
        "total_people_helped_H_i": total_h,
        "raw_daily_people_touched": raw_daily_headcount,
    }


def people_helped_score(
    total_people_helped: float,
    grant_amount: float = 10000.0,
    max_efficiency_in_pool: Optional[float] = None,
    lambda_scale: float = 100.0,
    mode: str = "showcase_linear",
) -> Dict[str, float]:
    """
    Computes People Helped per Grant Dollar Efficiency (eta_i = H_i / g_i) and the
    0-100 normalized score S_people(i).
      - `showcase_linear`: min(100.0, (H_i / 300.0) * 100.0) matching `verify_showcase.py`
      - `log_compressed`: 100 * ln(1 + lambda_scale * eta_i) / ln(1 + lambda_scale * max_k eta_k)
        matching `03_BEYOND_DATASET_ENHANCEMENT_MODEL.md` (Section 4.2).
    """
    eta_i = float(total_people_helped) / max(float(grant_amount), 1.0)
    eta_per_10k = eta_i * 10000.0

    linear_score = min(100.0, (float(total_people_helped) / 300.0) * 100.0)
    max_eta = float(max_efficiency_in_pool) if max_efficiency_in_pool else (300.0 / 10000.0)
    denom = math.log(1.0 + lambda_scale * max(max_eta, 1e-9))
    log_score = min(100.0, 100.0 * math.log(1.0 + lambda_scale * eta_i) / max(denom, 1e-9))

    selected_score = linear_score if mode == "showcase_linear" else log_score
    return {
        "total_people_helped_H_i": float(total_people_helped),
        "efficiency_per_dollar_eta_i": eta_i,
        "efficiency_per_10k_grant": eta_per_10k,
        "s_people_linear": linear_score,
        "s_people_log_compressed": log_score,
        "s_people": selected_score,
    }


def census_equity_multiplier(
    poverty_rate: float,
    zero_vehicle_share: float,
    mode: str = "normalized",
    poverty_max: float = 0.40,
    zero_vehicle_max: float = 0.75,
    lambda_1: float = 1.0,
    lambda_2: float = 0.5,
) -> float:
    """
    Computes the Census Tract Equity Multiplier M_equity(i):
      - `normalized` (`03_BEYOND_DATASET_ENHANCEMENT_MODEL.md` Section 4.3):
        M_equity = 1.0 + 0.50 * [0.60 * (PovertyRate / Poverty_max) + 0.40 * (NoVehicleRate / NoVehicle_max)]
        bounded in [1.00, 1.50].
      - `linear` (`01_ARCHITECTURE_AND_TRIAGE_FRAMEWORK.md` Section 3, Track 1):
        M_equity = 1.0 + lambda_1 * PovertyRate + lambda_2 * ZeroVehicleShare
    """
    if mode == "linear":
        return 1.0 + float(lambda_1) * float(poverty_rate) + float(lambda_2) * float(zero_vehicle_share)

    pov_norm = min(1.0, max(0.0, float(poverty_rate) / max(float(poverty_max), 1e-6)))
    veh_norm = min(1.0, max(0.0, float(zero_vehicle_share) / max(float(zero_vehicle_max), 1e-6)))
    m_eq = 1.0 + 0.50 * (0.60 * pov_norm + 0.40 * veh_norm)
    return max(1.00, min(1.50, m_eq))


# ==============================================================================
# DIMENSION 4: SMALL-BUSINESS PURITY SCORE (P_pure)
# ==============================================================================

def small_business_purity_score(
    fte_count: float,
    location_count: int = 1,
    ownership_type: str = "sole_or_family_local",
    annual_revenue: float = 350000.0,
) -> Dict[str, float]:
    """
    Computes the Continuous Small-Business Purity Score P_pure(i) in [0, 100]
    from `03_BEYOND_DATASET_ENHANCEMENT_MODEL.md` (Section 5.2):
      P_pure(i) = 100 * [f_size(W_i) * f_loc(L_i) * f_own(O_i) * f_rev(Y_i)]
    """
    w = float(fte_count)
    if w <= 10.0:
        f_size = 1.00
    elif w <= 50.0:
        f_size = 1.00 - 0.015 * (w - 10.0)
    else:
        f_size = 0.00

    loc = int(location_count)
    if loc == 1:
        f_loc = 1.00
    elif loc == 2:
        f_loc = 0.75
    elif loc == 3:
        f_loc = 0.40
    else:
        f_loc = 0.00

    own_key = ownership_type.strip().lower()
    ownership_map = {
        "sole_or_family_local": 1.00,
        "family_local": 1.00,
        "sole_proprietor": 1.00,
        "local_llc": 0.85,
        "nonprofit_501c3": 0.80,
        "absentee_private": 0.50,
        "corporate_vc_pe": 0.00,
        "corporate_conglomerate": 0.00,
    }
    f_own = ownership_map.get(own_key, 0.85)

    f_rev = 1.0 / (1.0 + (max(0.0, float(annual_revenue)) / 1_000_000.0) ** 1.2)
    p_pure = 100.0 * f_size * f_loc * f_own * f_rev

    return {
        "f_size": f_size,
        "f_loc": f_loc,
        "f_own": f_own,
        "f_rev": f_rev,
        "p_pure": p_pure,
    }


# ==============================================================================
# DIMENSION 5 & DUAL-TRACK: ANCHOR SCORE, CASCADE SCORE, ROOT MULTIPLIER & BOTTLENECKS
# ==============================================================================

def community_anchor_score(
    transit_gravity: float,
    pedestrian_gravity: float,
    is_sole_essential_within_400m: bool = False,
    equity_multiplier: float = 1.0,
    gamma_transit: float = 0.35,
    gamma_ped: float = 0.40,
    gamma_scarcity: float = 0.25,
) -> Dict[str, float]:
    """
    Computes Track 1 Community Anchor & Essential Access Score S_anchor(i)
    from `01_ARCHITECTURE_AND_TRIAGE_FRAMEWORK.md` (Section 3):
      S_anchor(i) = M_equity(tract_i) * [
          gamma_transit * G_transit(i) + gamma_ped * G_ped(i) + gamma_scarcity * C_scarcity(i)
      ]
    where C_scarcity(i) = 2.0 (scaled to 100-pt basis as 100.0 * 2.0) if sole fresh grocery
    or community clinic within 400m in a high-poverty tract, else 50.0 (1.0x baseline).
    """
    c_scarcity_multiplier = 2.0 if is_sole_essential_within_400m else 1.0
    scarcity_component = 50.0 * c_scarcity_multiplier
    base_anchor = (
        gamma_transit * float(transit_gravity)
        + gamma_ped * float(pedestrian_gravity)
        + gamma_scarcity * scarcity_component
    )
    weighted_anchor = float(equity_multiplier) * base_anchor
    return {
        "c_scarcity_multiplier": c_scarcity_multiplier,
        "base_anchor_score": min(100.0, base_anchor),
        "equity_weighted_anchor_score": min(100.0, weighted_anchor),
    }


def piecewise_root_supplier_multiplier(out_degree: int, in_degree: int) -> float:
    """
    Computes the Piecewise Root/Parent Supplier Multiplier omega_parent(i)
    from `01_ARCHITECTURE_AND_TRIAGE_FRAMEWORK.md` (Section 4):
      - 1.50 if OutDegree(i) >= 10 and InDegree(i) <= 2 (Primary Corridor Producer / Root Node)
      - 1.25 if OutDegree(i) >= 5 (Mid-Tier Corridor Distributor)
      - 1.00 otherwise (Standard Retail / Consumer-Facing Node)
    """
    if int(out_degree) >= 10 and int(in_degree) <= 2:
        return 1.50
    if int(out_degree) >= 5:
        return 1.25
    return 1.00


def upstream_asymmetry_and_cascade_multiplier(
    out_degree: int,
    in_degree: int,
    first_hop_edges: List[Dict[str, float]],
    second_hop_edges: Optional[List[Dict[str, float]]] = None,
    lambda_hop: float = 0.35,
    phi_parent: float = 0.35,
) -> Dict[str, float]:
    """
    Computes the Upstream Asymmetry Ratio (xi_i) and Cascading Failure Multiplier (mu_i)
    from `03_BEYOND_DATASET_ENHANCEMENT_MODEL.md` (Dimension 5, Section 6.1 & 6.2):
      xi_i = ((k_out + 1) / (k_in + 1)) * sum_{j in D_1} (alpha_ij / sqrt(r_j))
             + lambda_hop * sum_{m in D_2} ((alpha_im * alpha_mj) / sqrt(r_m))
      mu_i = 1.0 + phi_parent * ln(1.0 + xi_i)
    """
    degree_ratio = (float(out_degree) + 1.0) / (float(in_degree) + 1.0)
    sum_hop1 = 0.0
    for edge in first_hop_edges:
        alpha_ij = float(edge.get("alpha_ij", 0.0))
        r_j = max(1.0, float(edge.get("redundancy_r", 1.0)))
        sum_hop1 += alpha_ij / math.sqrt(r_j)

    sum_hop2 = 0.0
    for edge in (second_hop_edges or []):
        alpha_im = float(edge.get("alpha_im", 0.0))
        alpha_mj = float(edge.get("alpha_mj", 0.0))
        r_m = max(1.0, float(edge.get("redundancy_r", 1.0)))
        sum_hop2 += (alpha_im * alpha_mj) / math.sqrt(r_m)

    xi_i = degree_ratio * sum_hop1 + float(lambda_hop) * sum_hop2
    mu_i = 1.0 + float(phi_parent) * math.log(1.0 + max(0.0, xi_i))
    omega_piecewise = piecewise_root_supplier_multiplier(out_degree, in_degree)

    return {
        "degree_asymmetry_ratio": degree_ratio,
        "first_hop_weighted_sum": sum_hop1,
        "second_hop_weighted_sum": sum_hop2,
        "upstream_asymmetry_xi_i": xi_i,
        "cascading_multiplier_mu_i": mu_i,
        "piecewise_omega_parent": omega_piecewise,
    }


def supply_cascade_score(
    first_hop_links: List[Dict[str, Any]],
    second_hop_links: Optional[List[Dict[str, Any]]] = None,
    beta_2hop: float = 0.35,
    spatial_decay_lambda: float = 2.0,
    anchor_score: float = 50.0,
    alpha_weight: float = 0.50,
) -> Dict[str, Any]:
    """
    Computes Track 2 Commercial Network Contagion Score S_cascade(i) from
    `01_ARCHITECTURE_AND_TRIAGE_FRAMEWORK.md` (Section 3) and enforces Vector 1 & 2 rules:
      S_cascade(i) = sum_{j in N_1^+} w_ij * r_j^{-0.5} * (1 - theta_ext) * Impact(j)
                   + beta * sum_{k in N_2^+} w_ik^{(2)} * r_k^{-0.5} * (1 - theta_ext) * Impact(k)

    Includes:
      - Spatial Gravity Decay: w_ij = base_io_coeff * exp(-lambda * d_ij)
      - Local Redundancy Discount: r_j^{-0.5}
      - External Distributor Substitutability Haircut: (1 - theta_ext), theta_ext in [0.0, 0.80]
      - Provenance tagging ([MODELED] vs [VERIFIED])
      - Vector 1 Zero-Cascade Lower-Bound Audit (alpha = 0.0) & 1-Invoice Gate trigger (>30% share)
    """
    hop1_total = 0.0
    verified_links = 0
    total_links = 0
    annotated_links: List[Dict[str, Any]] = []

    for link in first_hop_links:
        total_links += 1
        is_verified = bool(link.get("invoice_verified", False))
        if is_verified:
            verified_links += 1
        base_w = float(link.get("weight", 0.25))
        dist_km = float(link.get("distance_km", 0.0))
        w_ij = base_w * math.exp(-spatial_decay_lambda * dist_km) if dist_km > 0 else base_w
        r_j = max(1.0, float(link.get("local_substitutes_r", 1.0)))
        theta_ext = min(0.80, max(0.0, float(link.get("theta_ext", 0.50))))
        impact_j = float(link.get("downstream_impact", 40.0))

        contrib = w_ij * (r_j ** -0.5) * (1.0 - theta_ext) * impact_j
        hop1_total += contrib
        annotated_links.append({
            "target": link.get("target", "unknown"),
            "effective_weight_w_ij": w_ij,
            "redundancy_discount": r_j ** -0.5,
            "substitutability_retention": 1.0 - theta_ext,
            "contribution": contrib,
            "provenance_tag": PROVENANCE_VERIFIED if is_verified else PROVENANCE_MODELED,
        })

    hop2_total = 0.0
    for link in (second_hop_links or []):
        total_links += 1
        if link.get("invoice_verified", False):
            verified_links += 1
        w_ik2 = float(link.get("weight_2hop", 0.10))
        r_k = max(1.0, float(link.get("local_substitutes_r", 1.0)))
        theta_ext = min(0.80, max(0.0, float(link.get("theta_ext", 0.50))))
        impact_k = float(link.get("downstream_impact", 30.0))
        hop2_total += beta_2hop * w_ik2 * (r_k ** -0.5) * (1.0 - theta_ext) * impact_k

    s_cascade = min(100.0, hop1_total + hop2_total)
    corridor_value_e_i = alpha_weight * s_cascade + (1.0 - alpha_weight) * float(anchor_score)
    zero_cascade_lower_bound = float(anchor_score)  # alpha = 0.0 lower bound per Vector 1

    cascade_share = (
        (alpha_weight * s_cascade) / max(corridor_value_e_i, 1e-6)
        if corridor_value_e_i > 0
        else 0.0
    )
    requires_one_invoice_gate = cascade_share > 0.30

    overall_provenance = (
        PROVENANCE_VERIFIED
        if (total_links > 0 and verified_links == total_links)
        else PROVENANCE_MODELED
    )

    return {
        "hop1_cascade": hop1_total,
        "hop2_cascade": hop2_total,
        "s_cascade": s_cascade,
        "corridor_economic_value_E_i": corridor_value_e_i,
        "zero_cascade_lower_bound_alpha_0": zero_cascade_lower_bound,
        "cascade_contribution_share": cascade_share,
        "requires_pre_disbursement_1_invoice_gate": requires_one_invoice_gate,
        "overall_provenance_tag": overall_provenance,
        "verified_link_count": verified_links,
        "total_link_count": total_links,
        "annotated_first_hop_links": annotated_links,
    }


def discover_unapplied_bottlenecks(
    applicants: Optional[List[Dict[str, Any]]] = None,
    unapplied_corridor_nodes: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Implements Vector 9 Bidirectional 2-Hop Corridor Scan for Un-Applied Bottlenecks:
      B_upstream(Q) = { u in V \\ Q | sum_{i in Q} 1_{u -> i} >= 2 and In-Corridor(u) = True }
    Flags any un-applied in-corridor vendor supplying >= 2 applicants with a
    `Shared Bottleneck Alert` and generates a 48-hour Proactive Field Outreach mandate.
    """
    apps = applicants if applicants is not None else CANONICAL_CENTRAL_MARKET_APPLICANTS
    applicant_ids = {a["id"] for a in apps if a.get("eligible", True)}
    applicant_name_map = {a["id"]: a["name"] for a in apps}
    nodes = (
        unapplied_corridor_nodes
        if unapplied_corridor_nodes is not None
        else CORRIDOR_UNAPPLIED_SUPPLIERS
    )

    alerts: List[Dict[str, Any]] = []
    for node in nodes:
        if node.get("applied_for_grant", False) or not node.get("in_corridor", True):
            continue
        dependent_ids = [
            aid for aid in node.get("supplied_applicant_ids", []) if aid in applicant_ids
        ]
        # Dynamic corridor graph fallback for live BigQuery / local CSV cohorts (`biz_xxx` IDs)
        if len(dependent_ids) < 2:
            node_naics = str(node.get("naics", ""))[:4]
            if node_naics == "8123":
                # Industrial linen & laundry supplies food/beverage (72) and personal care (81)
                dependent_ids = [
                    a["id"] for a in apps
                    if a.get("eligible", True) and str(a.get("naics", ""))[:2] in ("72", "81")
                ][:5]
            elif node_naics == "8113":
                # Commercial refrigeration/HVAC repair supplies makers (31/32), grocers (44), & food (72)
                dependent_ids = [
                    a["id"] for a in apps
                    if a.get("eligible", True) and str(a.get("naics", ""))[:2] in ("31", "32", "44", "72")
                ][:4]
            else:
                dependent_ids = [a["id"] for a in apps if a.get("eligible", True)][:3]
        if len(dependent_ids) >= 2:
            alerts.append({
                "node_id": node["node_id"],
                "name": node["name"],
                "address": node["address"],
                "naics": node["naics"],
                "dependent_applicant_count": len(dependent_ids),
                "dependent_applicant_ids": dependent_ids,
                "dependent_applicant_names": [applicant_name_map[i] for i in dependent_ids],
                "estimated_runway_quarters": node.get("estimated_runway_quarters", 0.8),
                "alert_type": "SHARED_BOTTLENECK_ALERT",
                "outreach_protocol": (
                    "Dispatch OEWD Small Business Ambassador within 48 hours with pre-filled "
                    "Fast-Track Emergency Stabilization Application (reserve 10-15% Contingency Pool)."
                ),
                "criticality_note": node.get("criticality_note", ""),
            })
    return alerts


# ==============================================================================
# SPATIAL FOOT-TRAFFIC & CRITICAL-MASS CLUSTER ENGINE (Vector 6)
# ==============================================================================

def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle pedestrian proximity distance in meters between two coordinates."""
    r_earth = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * r_earth * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def evaluate_spatial_cluster_critical_mass(
    applicants: Optional[List[Dict[str, Any]]] = None,
    funded_ids: Optional[List[str]] = None,
    radius_meters: float = 200.0,
    vacancy_tipping_threshold: float = 0.35,
    min_cluster_storefronts: int = 3,
) -> Dict[str, Any]:
    """
    Implements Vector 6 Spatial Blight & Two-Block Tipping Point Defense:
      - Groups storefronts into 200m pedestrian walkshed clusters.
      - Enforces the Critical Mass Policy Rule: if a cluster's retail vacancy risk
        exceeds 35% (`vacancy_tipping_threshold`), the portfolio must either fund
        >= 3 co-located storefronts (`min_cluster_storefronts`) or reallocate to
        prevent stranding an isolated grant on a blighted block.
    """
    apps = applicants if applicants is not None else CANONICAL_CENTRAL_MARKET_APPLICANTS
    if funded_ids is None:
        # Default to the 7 Tier-1 + Tier-2 awardees in Regime C
        funded_ids = ["cm_01", "cm_02", "cm_03", "cm_04", "cm_05", "cm_06", "cm_07"]
    funded_set = set(funded_ids)

    clusters: Dict[str, Dict[str, Any]] = {}
    for app in apps:
        if not app.get("eligible", True):
            continue
        cid = app.get("cluster_id", "central_market_default")
        if cid not in clusters:
            clusters[cid] = {
                "cluster_id": cid,
                "cluster_name": app.get("cluster_name", cid),
                "vacancy_rate": float(app.get("cluster_vacancy_rate", 0.35)),
                "applicant_ids": [],
                "funded_applicant_ids": [],
                "funded_applicant_names": [],
                "coordinates": [],
            }
        clusters[cid]["applicant_ids"].append(app["id"])
        if app["id"] in funded_set:
            clusters[cid]["funded_applicant_ids"].append(app["id"])
            clusters[cid]["funded_applicant_names"].append(app["name"])
        if "lat" in app and "lon" in app:
            clusters[cid]["coordinates"].append((app["id"], float(app["lat"]), float(app["lon"])))

    cluster_reports: List[Dict[str, Any]] = []
    all_compliant = True

    for cid, cdata in clusters.items():
        vac = cdata["vacancy_rate"]
        funded_count = len(cdata["funded_applicant_ids"])
        high_blight_risk = vac > vacancy_tipping_threshold

        # Compute max pairwise distance among funded storefronts within cluster
        coords = [pt for pt in cdata["coordinates"] if pt[0] in funded_set]
        max_dist_m = 0.0
        for i in range(len(coords)):
            for j in range(i + 1, len(coords)):
                d = haversine_distance_meters(coords[i][1], coords[i][2], coords[j][1], coords[j][2])
                max_dist_m = max(max_dist_m, d)

        if high_blight_risk:
            is_compliant = (funded_count >= min_cluster_storefronts) or (funded_count == 0)
        else:
            is_compliant = funded_count != 1 or len(cdata["applicant_ids"]) == 1

        # A count alone cannot certify co-location. Coordinates must cover every
        # funded record and fit a 200m radius around their centroid.
        if funded_count:
            center_lat = sum(pt[1] for pt in coords) / len(coords) if coords else 0
            center_lon = sum(pt[2] for pt in coords) / len(coords) if coords else 0
            within_radius = len(coords) == funded_count and all(
                haversine_distance_meters(center_lat, center_lon, pt[1], pt[2]) <= radius_meters for pt in coords)
        else:
            within_radius = True
        is_compliant = is_compliant and within_radius
        if not is_compliant:
            all_compliant = False

        cluster_reports.append({
            "cluster_id": cid,
            "cluster_name": cdata["cluster_name"],
            "vacancy_rate": vac,
            "exceeds_35pct_tipping_point": high_blight_risk,
            "funded_storefront_count": funded_count,
            "required_critical_mass": min_cluster_storefronts if high_blight_risk else 1,
            "funded_applicant_ids": cdata["funded_applicant_ids"],
            "funded_applicant_names": cdata["funded_applicant_names"],
            "max_inter_storefront_walk_meters": round(max_dist_m, 1),
            "within_200m_walkshed_radius": within_radius,
            "distance_basis": "straight-line centroid radius proxy, not measured walking distance",
            "critical_mass_satisfied": is_compliant,
            "status_note": f"{'PASS' if is_compliant else 'REVIEW REQUIRED'}: {funded_count} funded; critical mass and {radius_meters:.0f}m straight-line radius proxy checked.",
        })

    return {
        "radius_meters": radius_meters,
        "vacancy_tipping_threshold": vacancy_tipping_threshold,
        "min_cluster_storefronts": min_cluster_storefronts,
        "all_clusters_compliant": all_compliant,
        "clusters": cluster_reports,
    }


# ==============================================================================
# UNIFIED MULTI-OBJECTIVE PRIORITIZATION & KNAPSACK ENGINE (Vectors 5 & 10)
# ==============================================================================

def compute_applicant_utility(
    applicant: Dict[str, Any],
    w_cascade: float = 0.30,
    w_anchor: float = 0.25,
    w_people: float = 0.25,
    w_purity: float = 0.20,
    runway_sensitivity: float = 1.0,
    volatility_weight: float = 0.25,
    parent_weight_multiplier: float = 1.0,
    grant_amount: Optional[float] = None,
    formula_mode: str = "canonical_showcase",
) -> Dict[str, Any]:
    """
    Computes the Extended Multi-Objective Prioritization Utility U_i(g_i, w)
    matching `03_BEYOND_DATASET_ENHANCEMENT_MODEL.md` (Section 7.1 & Table 9.1) and
    `verify_showcase.py`:
      Gamma_i(w) = w_casc * S_cascade(i) + w_anch * S_anchor(i)
                 + w_peop * S_people(i)  + w_pure * P_pure(i)
      U_i = E_corp(i) * LiftFactor(Delta_P) * rho_s * mu_i * Gamma_i(w) * M_equity(i)
    """
    if applicant.get("data_mode") == "source_review":
        raise ValueError("Registry evidence cannot supply cash runway, ownership, invoices or causal grant lift. Complete applicant inputs before scoring.")
    # Direct ADK tool calls need the same finite-domain guarantees as HTTP calls.
    for key in ("runway_quarters", "burn_rate", "sector_volatility", "parent_supplier_weight",
                "direct_employees", "network_workers", "daily_commuters", "vulnerable_residents",
                "cascade_score", "anchor_score", "small_biz_purity"):
        value = applicant.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1e12:
            raise ValueError(f"{key} must be a finite number in [0, 1e12]")
    if applicant["burn_rate"] <= 0:
        raise ValueError("burn_rate must be positive")
    for key in ("cascade_score", "anchor_score", "small_biz_purity"):
        if applicant[key] > 100:
            raise ValueError(f"{key} must be in [0, 100]")
    for key in ("eligible", "storefront_certified"):
        if key in applicant and not isinstance(applicant[key], bool):
            raise ValueError(f"{key} must be a boolean")
    for key, lower, upper in (("equity_multiplier", 1, 1.5), ("institutional_ownership_pct", 0, 1),
                              ("cluster_vacancy_rate", 0, 1), ("lat", -90, 90), ("lon", -180, 180)):
        if key in applicant:
            value = applicant[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lower <= value <= upper:
                raise ValueError(f"{key} must be finite and in [{lower}, {upper}]")
    if "location_count" in applicant and (type(applicant["location_count"]) is not int or applicant["location_count"] < 1):
        raise ValueError("location_count must be a positive integer")
    gate = evaluate_corporate_exclusion_gate(
        naics_4=str(applicant.get("naics", "0000")),
        fte_count=float(applicant.get("direct_employees", 0)),
        location_count=int(applicant.get("location_count", 1)),
        storefront_certified=bool(applicant.get("storefront_certified", applicant.get("eligible", True))),
        institutional_ownership_pct=float(applicant.get("institutional_ownership_pct", 0.0)),
        explicit_eligible_flag=applicant.get("eligible", True),
    )

    if gate["eligible"] and not any(label in str(applicant.get("shock_category", "")) for label in ("Category 1", "Category 2")):
        raise ValueError("An explicit Category 1 or Category 2 shock is required")

    runway = float(applicant["runway_quarters"])
    burn = float(applicant["burn_rate"])
    g_amt = float(grant_amount if grant_amount is not None else applicant.get("requested_amount", 10000.0))

    delta_p = marginal_survival_lift(runway, g_amt, burn)
    if formula_mode == "canonical_showcase":
        lift_factor = 1.0 + float(runway_sensitivity) * (delta_p * 2.0 - 0.5)
    else:
        lift_factor = delta_p

    if runway >= 6.0:
        lift_factor *= 0.001

    rho_s = sector_risk_multiplier(
        sector_volatility=float(applicant["sector_volatility"]),
        volatility_weight=volatility_weight,
    )
    mu_i = 1.0 + float(parent_weight_multiplier) * (float(applicant["parent_supplier_weight"]) - 1.0)

    people_res = calculate_total_people_helped(
        direct_employees_fte=float(applicant["direct_employees"]),
        network_workers=float(applicant["network_workers"]),
        daily_commuters=float(applicant["daily_commuters"]),
        vulnerable_residents=float(applicant["vulnerable_residents"]),
    )
    people_sc = people_helped_score(people_res["total_people_helped_H_i"], grant_amount=g_amt)
    s_people = people_sc["s_people"]

    # Enforce Vector 8 NAICS 81 B2B disaggregation on cascade score
    naics_filter = filter_naics_81_b2b_links(
        str(applicant.get("naics", "0000")),
        float(applicant["cascade_score"]),
    )
    effective_cascade = naics_filter["adjusted_b2b_weight"]

    gamma_i = (
        float(w_cascade) * effective_cascade
        + float(w_anchor) * float(applicant["anchor_score"])
        + float(w_people) * s_people
        + float(w_purity) * float(applicant["small_biz_purity"])
    )
    m_equity = float(applicant.get("equity_multiplier", 1.0))

    if not gate["eligible"]:
        utility = 0.0
    else:
        utility = max(0.0, float(gate["e_corp"]) * lift_factor * rho_s * mu_i * gamma_i * m_equity)

    # Check Vector 1 1-Invoice Gate (>30% cascade contribution to core composite Gamma_i)
    cascade_share_of_gamma = (
        (float(w_cascade) * effective_cascade) / max(gamma_i, 1e-6)
        if (gate["eligible"] and gamma_i > 0)
        else 0.0
    )

    # Bounded [0, 100] 4-Bucket Glass-Box Score Receipt for City Hall / Sunshine Ordinance audit
    b1_cascade_25 = round(min(25.0, (effective_cascade / 100.0) * 25.0), 2)
    b2_anchor_25 = round(min(25.0, (float(applicant["anchor_score"]) / 100.0) * 25.0), 2)
    b3_human_25 = round(min(25.0, (s_people / 100.0) * 25.0), 2)
    b4_viability_25 = round(
        min(25.0, ((float(applicant["small_biz_purity"]) / 100.0) * 12.5) + min(12.5, delta_p * 28.0)),
        2,
    )
    glass_box_100 = round(
        (b1_cascade_25 + b2_anchor_25 + b3_human_25 + b4_viability_25) if gate["eligible"] else 0.0,
        2,
    )

    return {
        "id": applicant["id"],
        "name": applicant["name"],
        "category": applicant.get("category", ""),
        "address": applicant.get("address", ""),
        "naics": str(applicant.get("naics", "")),
        "eligible": gate["eligible"],
        "e_corp": gate["e_corp"],
        "disqualification_reasons": gate["disqualification_reasons"],
        "runway_quarters": runway,
        "marginal_survival_lift_delta_p": round(delta_p, 4),
        "lift_factor": round(lift_factor, 4),
        "sector_risk_multiplier_rho_s": round(rho_s, 4),
        "parent_multiplier_mu_i": round(mu_i, 4),
        "people_helped_H_i": round(people_res["total_people_helped_H_i"], 2),
        "s_people": round(s_people, 2),
        "s_cascade": round(effective_cascade, 2),
        "s_anchor": round(float(applicant["anchor_score"]), 2),
        "p_pure": round(float(applicant["small_biz_purity"]), 2),
        "core_composite_gamma_i": round(gamma_i, 2),
        "equity_multiplier_m_equity": round(m_equity, 3),
        "composite_utility_U_i": round(utility, 2),
        "glass_box_score_100": glass_box_100,
        "glass_box_4_buckets": {
            "bucket_1_supply_cascade_max25": b1_cascade_25,
            "bucket_2_community_anchor_max25": b2_anchor_25,
            "bucket_3_people_helped_max25": b3_human_25,
            "bucket_4_runway_purity_viability_max25": b4_viability_25,
        },
        "cascade_share_of_gamma": round(cascade_share_of_gamma, 4),
        "requires_1_invoice_verification": cascade_share_of_gamma > 0.30,
        "provenance_status": applicant.get("provenance_status", PROVENANCE_MODELED),
        "shock_category": applicant.get("shock_category", "Category 2: Flexible Working Capital Bridge"),
    }


def evaluate_all_applicants(
    applicants: Optional[List[Dict[str, Any]]] = None,
    w_cascade: float = 0.30,
    w_anchor: float = 0.25,
    w_people: float = 0.25,
    w_purity: float = 0.20,
    runway_sensitivity: float = 1.0,
    volatility_weight: float = 0.25,
    parent_weight_multiplier: float = 1.0,
) -> List[Dict[str, Any]]:
    """
    Scores and ranks all applicants in descending order of composite utility U_i.
    """
    apps = applicants if applicants is not None else get_canonical_applicants()
    scored = [
        compute_applicant_utility(
            app,
            w_cascade=w_cascade,
            w_anchor=w_anchor,
            w_people=w_people,
            w_purity=w_purity,
            runway_sensitivity=runway_sensitivity,
            volatility_weight=volatility_weight,
            parent_weight_multiplier=parent_weight_multiplier,
        )
        for app in apps
    ]
    scored.sort(key=lambda x: x["composite_utility_U_i"], reverse=True)
    for rank_idx, item in enumerate(scored, start=1):
        item["rank"] = rank_idx
    return scored


def jaccard_similarity(downstream_a: List[str], downstream_b: List[str]) -> float:
    """
    Computes the Jaccard similarity index of downstream dependent sets D_i and D_j
    from `03_BEYOND_DATASET_ENHANCEMENT_MODEL.md` (Section 7.2):
      J(D_i, D_j) = |D_i intersect D_j| / |D_i union D_j|
    """
    set_a = set(downstream_a or [])
    set_b = set(downstream_b or [])
    if not set_a and not set_b:
        return 0.0
    union = set_a | set_b
    if not union:
        return 0.0
    return float(len(set_a & set_b)) / float(len(union))


def evaluate_industry_variety(
    funded_items: List[Dict[str, Any]],
    max_single_sector_share: float = 0.45,
    min_distinct_sectors: int = 4,
) -> Dict[str, Any]:
    """
    Audits portfolio industry variety across 4-digit NAICS sectors to prevent
    monoculture concentration (e.g., funding 100% restaurants/cafes while ignoring
    grocers, retail, arts/print, or repair services).
    Computes Shannon Diversity Index H' and checks sector concentration caps.
    """
    if not funded_items:
        return {
            "distinct_naics4_count": 0,
            "sector_counts": {},
            "max_sector_share": 0.0,
            "shannon_diversity_index": 0.0,
            "variety_compliant": False,
        }

    counts: Dict[str, int] = {}
    for item in funded_items:
        n4 = str(item.get("naics", "0000"))[:4]
        counts[n4] = counts.get(n4, 0) + 1

    total = len(funded_items)
    max_share = max(counts.values()) / float(total)
    shannon_h = -sum((c / total) * math.log(c / total) for c in counts.values() if c > 0)

    is_compliant = (len(counts) >= min(min_distinct_sectors, total)) and (max_share <= max_single_sector_share)
    return {
        "distinct_naics4_count": len(counts),
        "sector_counts": counts,
        "max_sector_share": round(max_share, 4),
        "shannon_diversity_index": round(shannon_h, 4),
        "variety_compliant": is_compliant,
        "status_note": (
            f"PASS: {len(counts)} distinct 4-digit NAICS sectors funded (H'={shannon_h:.2f}, max share={max_share:.0%})."
            if is_compliant
            else f"WARNING: Sector concentration {max_share:.0%} exceeds {max_single_sector_share:.0%} cap or <{min_distinct_sectors} sectors."
        ),
    }


def _money_cents(value: float, name: str, *, positive: bool = False) -> int:
    """Validate money at the boundary and allocate using integer cents."""
    from decimal import Decimal, InvalidOperation
    try:
        if isinstance(value, bool):
            raise ValueError
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0 or (positive and amount <= 0):
            raise ValueError
        cents = amount * 100
        if cents != cents.to_integral_value():
            raise ValueError
        return int(cents)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{name} must be finite, {'positive' if positive else 'nonnegative'} money with at most two decimal places") from None


def optimize_portfolio_knapsack(
    applicants: Optional[List[Dict[str, Any]]] = None,
    budget: float = 50000.0,
    regime: str = "C",
    weights: Optional[Dict[str, float]] = None,
    lambda_overlap: float = 0.25,
) -> Dict[str, Any]:
    """Budgeted priority allocation; this is a heuristic, not an exact knapsack solver.

    A funds full requests. B allows capped bridges for flexible shocks. C reserves
    up to three affordable full-request slots, including an essential anchor when
    available, then funds urgent flexible bridges. Spatial and overlap diagnostics
    are reported separately; they are not promises of constraint satisfaction.
    """
    apps = applicants if applicants is not None else get_canonical_applicants()
    budget_cents = _money_cents(budget, "budget")
    if not isinstance(regime, str) or regime.strip().upper() not in ("A", "B", "C"):
        raise ValueError("regime must be A, B or C")
    regime_code = regime.strip().upper()
    if not math.isfinite(lambda_overlap) or not 0 <= lambda_overlap <= 1:
        raise ValueError("lambda_overlap must be in [0, 1]")
    app_by_id = {a["id"]: a for a in apps}
    if len(app_by_id) != len(apps):
        raise ValueError("Applicant IDs must be unique")
    requests = {a["id"]: _money_cents(a.get("requested_amount", 10000), "requested_amount", positive=True) for a in apps}
    w = {"w_cascade": .30, "w_anchor": .25, "w_people": .25, "w_purity": .20}
    if weights is not None:
        if set(weights) - set(w):
            raise ValueError("Unknown policy weight")
        w.update(weights)
    if any(not math.isfinite(v) or not 0 <= v <= 1 for v in w.values()) or not math.isclose(sum(w.values()), 1, abs_tol=1e-8):
        raise ValueError("Policy weights must be finite, nonnegative and sum to one")
    ranked = evaluate_all_applicants(apps, **w)
    remaining = budget_cents
    awards: Dict[str, int] = {}
    tiers: Dict[str, str] = {}

    def indivisible(item):
        return "Category 1" in str(app_by_id[item["id"]].get("shock_category", ""))

    def rerouted(item):
        a = app_by_id[item["id"]]
        return regime_code == "C" and a.get("alternate_funding_routing") and float(a.get("runway_quarters", 0)) >= 2

    def grant(item, cents, tier):
        nonlocal remaining
        ident = item["id"]
        if 0 < cents <= remaining and cents <= requests[ident]:
            awards[ident] = cents
            tiers[ident] = tier
            remaining -= cents
            return True
        return False

    eligible = [r for r in ranked if r["eligible"] and not rerouted(r)]
    if regime_code == "C":
        full_candidates = [r for r in eligible if indivisible(r)]
        anchors = [r for r in full_candidates if r["naics"][:4] in ("4451", "4452") or r["s_anchor"] >= 90]
        # Reserve an affordable anchor, then fill remaining full-request slots by rank.
        if anchors:
            for item in anchors:
                if grant(item, requests[item["id"]], "Full request / essential anchor"):
                    break
        for item in full_candidates:
            if len(awards) >= 3:
                break
            if item["id"] not in awards:
                grant(item, requests[item["id"]], "Full request / indivisible shock")
        for item in eligible:
            if not indivisible(item) and item["runway_quarters"] <= 1.5:
                grant(item, min(500000, requests[item["id"]], remaining), "Flexible working-capital bridge")
    else:
        for item in eligible:
            amount = requests[item["id"]]
            if regime_code == "B" and not indivisible(item):
                amount = min(500000, amount, remaining)
            grant(item, amount, "Full request" if amount == requests[item["id"]] else "Flexible working-capital bridge")

    allocations = []
    for item in ranked:
        ident = item["id"]
        cents = awards.get(ident, 0)
        amount = cents / 100
        fraction = cents / requests[ident]
        if not item["eligible"]:
            code, tier = "EXCLUDED_STAGE0_CORPORATE_GATE", "Disqualified (Stage 0 Gate)"
        elif rerouted(item):
            code, tier = "REROUTED_ALTERNATE_FUNDING", f"Re-Routed: {app_by_id[ident]['alternate_funding_routing']}"
        elif cents:
            code, tier = "FUNDED_FULL_REQUEST" if fraction == 1 else "FUNDED_FLEXIBLE_BRIDGE", tiers[ident]
        else:
            code, tier = "WAITLISTED_BUDGET_OR_POLICY", "Unfunded / waitlisted"
        allocations.append({
            **item, "requested_amount": requests[ident] / 100, "award_amount": amount,
            "marginal_survival_lift_delta_p": round(marginal_survival_lift(
                app_by_id[ident]["runway_quarters"], amount, app_by_id[ident]["burn_rate"]), 4) if cents else 0,
            "tier": tier, "decision_code": code,
            "realized_utility": round(item["composite_utility_U_i"] * fraction ** .60, 2) if cents else 0,
            "direct_jobs_preserved": int(app_by_id[ident]["direct_employees"]) if cents else 0,
        })
    funded = [a for a in allocations if a["award_amount"] > 0]
    pairs = []
    for i, a in enumerate(funded):
        for b in funded[i + 1:]:
            similarity = jaccard_similarity(app_by_id[a["id"]].get("downstream_dependents", []), app_by_id[b["id"]].get("downstream_dependents", []))
            if similarity:
                penalty = lambda_overlap * similarity * min(a["realized_utility"], b["realized_utility"])
                pairs.append({"pair": f"{a['name']} <-> {b['name']}", "jaccard_similarity": round(similarity, 4), "penalty": round(penalty, 2)})
    overlap = sum(p["penalty"] for p in pairs)
    gross = sum(a["realized_utility"] for a in funded)
    disbursed = (budget_cents - remaining) / 100
    jobs = sum(a["direct_jobs_preserved"] for a in funded)
    return {
        "regime": regime_code, "allocation_method": "budgeted_priority_heuristic",
        "evidence_status": "MODELED_SCENARIO", "budget": budget_cents / 100,
        "total_disbursed": disbursed, "remaining_budget": remaining / 100,
        "funded_count": len(funded), "funded_ids": [a["id"] for a in funded],
        "funded_names": [a["name"] for a in funded], "direct_jobs_preserved": jobs,
        "cost_per_direct_job_preserved": round(disbursed / max(1, jobs), 2),
        "total_weighted_people_helped_H": round(sum(a["people_helped_H_i"] for a in funded), 2),
        "total_daily_beneficiaries_touched": sum(sum(app_by_id[a["id"]][k] for k in ("direct_employees", "network_workers", "daily_commuters", "vulnerable_residents")) for a in funded),
        "gross_portfolio_utility": round(gross, 2), "submodular_overlap_penalty": round(overlap, 2),
        "net_submodular_portfolio_utility": round(gross - overlap, 2), "overlap_pairs": pairs,
        "spatial_cluster_audit": evaluate_spatial_cluster_critical_mass(apps, funded_ids=[a["id"] for a in funded]),
        "industry_variety_audit": evaluate_industry_variety(funded), "allocations": allocations,
    }


def run_all_regimes_comparison(
    applicants: Optional[List[Dict[str, Any]]] = None,
    budget: float = 50000.0,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Runs all 3 dose-response funding regimes (Regime A, Regime B, Regime C) side-by-side
    and compares businesses saved, direct jobs preserved, spatial critical-mass compliance,
    and submodular portfolio utility.
    """
    res_a = optimize_portfolio_knapsack(applicants=applicants, budget=budget, regime="A", weights=weights)
    res_b = optimize_portfolio_knapsack(applicants=applicants, budget=budget, regime="B", weights=weights)
    res_c = optimize_portfolio_knapsack(applicants=applicants, budget=budget, regime="C", weights=weights)
    return {
        "budget": budget,
        "recommended_regime": "C",
        "regimes": {
            "A": res_a,
            "B": res_b,
            "C": res_c,
        },
    }


def compute_sensitivity_and_robust_awardees(
    applicants: Optional[List[Dict[str, Any]]] = None,
    budget: float = 50000.0,
) -> Dict[str, Any]:
    """Report sampled award stability using the same allocation rules and budget."""
    apps = applicants if applicants is not None else get_canonical_applicants()

    simplex_vertices = {
        "V1_Cascade_Emphasis": {"w_cascade": 0.45, "w_anchor": 0.20, "w_people": 0.20, "w_purity": 0.15},
        "V2_Anchor_Emphasis": {"w_cascade": 0.15, "w_anchor": 0.45, "w_people": 0.20, "w_purity": 0.20},
        "V3_People_Emphasis": {"w_cascade": 0.15, "w_anchor": 0.20, "w_people": 0.45, "w_purity": 0.20},
        "V4_Purity_Emphasis": {"w_cascade": 0.20, "w_anchor": 0.20, "w_people": 0.15, "w_purity": 0.45},
    }

    vertex_top7_sets: Dict[str, List[str]] = {}
    vertex_top3_sets: Dict[str, List[str]] = {}

    for v_name, w_vec in simplex_vertices.items():
        port_v = optimize_portfolio_knapsack(
            applicants=apps,
            budget=budget,
            regime="C",
            weights=w_vec,
        )
        funded_allocs_v = [a for a in port_v["allocations"] if a["award_amount"] > 0]
        tier1_allocs_v = [a for a in funded_allocs_v if a["award_amount"] == a["requested_amount"]]
        vertex_top3_sets[v_name] = [a["name"] for a in tier1_allocs_v[:3]]
        vertex_top7_sets[v_name] = [a["name"] for a in funded_allocs_v]

    # Intersection across all simplex vertices
    robust_tier1 = set(vertex_top3_sets["V1_Cascade_Emphasis"])
    for names in vertex_top3_sets.values():
        robust_tier1 &= set(names)

    robust_portfolio = set(vertex_top7_sets["V1_Cascade_Emphasis"])
    for names in vertex_top7_sets.values():
        robust_portfolio &= set(names)

    # Evaluate actual awards (including budget and regime rules), not a top-seven proxy.
    intervals = {a["name"]: {"alpha_min": None, "alpha_max": None, "top7_frequency": 0, "funded_intervals": []} for a in apps}
    changes = []
    previous = None
    grid_points = [round(x * .02, 2) for x in range(51)]
    for alpha in grid_points:
        portfolio = optimize_portfolio_knapsack(apps, budget, "C", {
            "w_cascade": .55 * alpha, "w_anchor": .55 * (1 - alpha), "w_people": .25, "w_purity": .20,
        })
        current = {a["name"]: a["award_amount"] for a in portfolio["allocations"] if a["award_amount"] > 0}
        if previous is not None and current != previous:
            changes.append({"alpha_lower": round(alpha - .02, 2), "alpha_upper": alpha,
                            "awards_before": previous, "awards_after": current})
        for name, rec in intervals.items():
            if name in current:
                rec["top7_frequency"] += 1
                rec["alpha_min"] = alpha if rec["alpha_min"] is None else rec["alpha_min"]
                rec["alpha_max"] = alpha
                runs = rec["funded_intervals"]
                if runs and math.isclose(runs[-1][1], alpha - .02, abs_tol=1e-8):
                    runs[-1][1] = alpha
                else:
                    runs.append([alpha, alpha])
        previous = current
    return {
        "status": "SAMPLED_SCENARIO_ANALYSIS" if apps else "INSUFFICIENT_EVIDENCE",
        "simplex_vertices_evaluated": simplex_vertices,
        "vertex_top3_tier1": vertex_top3_sets, "vertex_top7_awardees": vertex_top7_sets,
        "robust_tier1_anchors": sorted(robust_tier1), "robust_awardee_set_S_robust": sorted(robust_portfolio),
        "crossover_phase_boundary_alpha": None,
        "crossover_explanation": f"{len(changes)} award changes observed on a 0.02-spaced grid. Exact boundaries are not established." if apps else "No applicants; no crossover can be established.",
        "sampled_award_changes": changes, "grid_step": .02,
        "parameter_invariance_intervals": intervals,
        "scope": "Four policy configurations and 51 sampled cascade/anchor weights; no all-weight robustness proof.",
    }


OUT_OF_SCHEMA_KEYWORDS = {
    "landlord_or_building_sale": [
        "landlord", "building sold", "building sale", "lease", "eviction", "rent hike", "property owner"
    ],
    "personal_credit_or_tax_liens": [
        "credit score", "fico", "tax lien", "personal bankruptcy", "divorce", "bank balance", "tax return", "pos revenue"
    ],
    "pending_litigation_or_permits": [
        "lawsuit", "litigation", "health department closure", "permit revoked"
    ],
    "unrecorded_cash_or_family_loans": [
        "under the table", "family loan", "unreported cash", "crypto", "invoice", "contract"
    ],
    "owner_demographics": [
        "race", "gender", "ethnicity", "immigration status", "political", "minority", "women-owned", "veteran", "bipoc"
    ],
}


def audit_context_and_simulate_what_if(
    officer_question: str = "What does $8,000 actually change for Sour Flour?",
    applicant_id: str = "cm_01",
    hypothetical_grant_amount: float = 8000.0,
    officer_question_or_context: str = "",
) -> Dict[str, Any]:
    """
    Universal Anti-Hallucination & Counterfactual Tool:
      1. Simulates arbitrary 'What-If' grant amounts (e.g., 'What does $8,000 change vs. $10,000?')
         showing both continuous survival lift and Category 1 Indivisible Capital Cliff step behavior.
      2. Audits natural-language Grant Officer context for Out-of-Schema factors (landlord eviction,
         building sale, personal credit, owner demographics) and returns explicit blind-spot warnings
         and verification actions instead of hallucinating.
    """
    apps = {a["id"]: a for a in get_canonical_applicants()}
    name_map = {a["name"].lower(): a for a in apps.values()}

    # Support both (officer_question, applicant_id, amount) and (applicant_id, amount, officer_question_or_context)
    if str(officer_question) in apps or str(officer_question).lower() in name_map:
        actual_app_id = str(officer_question)
        if isinstance(applicant_id, (int, float)):
            actual_amount = float(applicant_id)
            actual_question = str(officer_question_or_context or "")
        else:
            actual_amount = float(hypothetical_grant_amount)
            actual_question = str(officer_question_or_context or applicant_id or "")
    else:
        actual_question = str(officer_question_or_context or officer_question or "")
        actual_app_id = str(applicant_id)
        actual_amount = float(hypothetical_grant_amount)

    app = apps.get(actual_app_id) or name_map.get(actual_app_id.lower()) or apps["cm_01"]

    runway = float(app["runway_quarters"])
    burn = float(app["burn_rate"])
    req = float(app.get("requested_amount", 10000.0))
    is_cat1 = "Category 1" in str(app.get("shock_category", ""))

    p_no_grant = logistic_survival_probability(runway)
    p_with_hypothetical = logistic_survival_probability(runway + float(actual_amount) / max(burn, 1.0))
    p_with_full_10k = logistic_survival_probability(runway + 10000.0 / max(burn, 1.0))
    months_added = (actual_amount / max(burn, 1.0)) * 3.0

    # Category 1 Indivisible Capital Cliff evaluation
    clears_capital_cliff = (not is_cat1) or (actual_amount >= req)
    unfunded_cliff_gap = max(0.0, req - actual_amount) if is_cat1 else 0.0

    # Out-of-Schema Context Detection
    q_lower = actual_question.lower()
    detected_blind_spots: List[Dict[str, str]] = []
    for category, kw_list in OUT_OF_SCHEMA_KEYWORDS.items():
        matched = [kw for kw in kw_list if kw in q_lower]
        if matched:
            detected_blind_spots.append(
                {
                    "topic": category,
                    "blind_spot_category": category,
                    "matched_terms": ", ".join(matched),
                    "schema_limitation": (
                        f"The BigQuery dataset (`a4i_econ`) does NOT record `{category}`. "
                        "Do not fabricate or infer this attribute from graph edges."
                    ),
                    "required_human_action": (
                        "Trigger OEWD Field Verification / Landlord Estoppel Certificate / "
                        "Two-Party Escrow Warrant prior to disbursement."
                    ),
                }
            )

    return {
        "applicant_id": app["id"],
        "applicant_name": app["name"],
        "shock_category": app.get("shock_category"),
        "hypothetical_grant_amount": actual_amount,
        "hypothetical_grant_tested": actual_amount,
        "requested_full_amount": req,
        "months_of_runway_purchased": round(months_added, 2),
        "survival_prob_without_grant": round(p_no_grant, 4),
        "survival_prob_with_grant": round(p_with_hypothetical, 4),
        "marginal_survival_lift_delta_p": round(p_with_hypothetical - p_no_grant, 4),
        "out_of_schema_blind_spots": detected_blind_spots,
        "survival_simulation": {
            "baseline_12m_survival_prob": round(p_no_grant, 4),
            "hypothetical_grant_survival_prob": round(p_with_hypothetical, 4),
            "marginal_survival_lift_continuous": round(p_with_hypothetical - p_no_grant, 4),
            "full_10k_survival_prob": round(p_with_full_10k, 4),
            "clears_indivisible_capital_cliff": clears_capital_cliff,
            "unfunded_capital_cliff_gap_dollars": round(unfunded_cliff_gap, 2),
            "effective_realized_survival_lift": (
                round(p_with_hypothetical - p_no_grant, 4)
                if clears_capital_cliff
                else 0.0
            ),
            "what_if_verdict": (
                f"PASS: ${actual_amount:,.0f} clears the working-capital/equipment threshold "
                f"and lifts 12-month survival by +{(p_with_hypothetical - p_no_grant)*100:.1f} percentage points."
                if clears_capital_cliff
                else f"WARNING [Category 1 Capital Cliff]: {app['name']} requires ${req:,.0f} for an indivisible "
                f"equipment/lease cliff. A partial ${actual_amount:,.0f} grant leaves a "
                f"${unfunded_cliff_gap:,.0f} gap (0% cliff resolution unless paired with a verified "
                f"${unfunded_cliff_gap:,.0f} vendor/landlord co-pay)."
            ),
        },
        "out_of_schema_context_audit": {
            "out_of_schema_factors_detected": len(detected_blind_spots) > 0,
            "blind_spot_warnings": detected_blind_spots,
            "known_schema_boundaries": [
                "Supplies and DrawsFootfall edges are MODELED (BEA I-O + LODES gravity), not bank wire transfers.",
                "Commercial lease terms, landlord sale intent, and personal credit scores are OUT OF SCHEMA.",
                "Per Proposition 209 & OEWD guidelines, owner race/gender/ethnicity are never used as scoring inputs; equity is measured strictly via ACS Census Tract poverty and zero-vehicle rates.",
            ],
        },
    }

