"""Evidence-aware scenario checks and draft reports. These do not approve awards."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from tools.scoring_engine import (
    compute_sensitivity_and_robust_awardees, evaluate_spatial_cluster_critical_mass,
    get_canonical_applicants, optimize_portfolio_knapsack,
)


def evaluate_red_team_compliance(
    portfolio_result: Optional[Dict[str, Any]] = None,
    applicants: Optional[List[Dict[str, Any]]] = None,
    adk_dir: Optional[str] = None,
) -> Dict[str, Any]:
    apps = applicants if applicants is not None else get_canonical_applicants()
    by_id = {a['id']: a for a in apps}
    portfolio = portfolio_result if portfolio_result is not None else optimize_portfolio_knapsack(apps)
    allocations = portfolio['allocations']
    funded = [a for a in allocations if a['award_amount'] > 0]
    spatial = portfolio.get('spatial_cluster_audit') or evaluate_spatial_cluster_critical_mass(apps, portfolio['funded_ids'])
    sensitivity = compute_sensitivity_and_robust_awardees(apps, portfolio['budget'])
    vectors = []

    def check(number, title, condition, rule, proof):
        vectors.append({'vector_number': number, 'title': title,
                        'status': 'REVIEW_REQUIRED' if condition is None else ('PASS' if condition else 'FAIL'),
                        'rule_enforced': rule, 'portfolio_proof': proof})

    check(1, 'Supply provenance', None,
          'Modeled links require separate vendor evidence before disbursement.',
          f"{sum(bool(a.get('provenance_status')) for a in allocations)}/{len(allocations)} applicants have provenance labels. Labels do not verify documents.")
    thetas = [float(by_id[a['id']].get('substitutability_theta', .5)) for a in funded]
    check(2, 'Substitution assumptions', all(0 <= t <= .8 for t in thetas) if funded else None,
          'Scenario substitution discounts must be in [0, 0.8].',
          f"{len(thetas)} funded scenario inputs checked; substitutability is not independently measured.")
    check(3, 'Financial and payment verification', None,
          'Review current financial statements and payment instructions.',
          f"{len(funded)} modeled awards require financial and payment review. No bank or warrant verification is inferred from runway.")
    check(4, 'Runway policy range', all(.25 <= a['runway_quarters'] < 4 for a in funded) if funded else None,
          'Check the scenario triage interval [0.25, 4) quarters.',
          'Funded runways: ' + (', '.join(f"{a['name']}: {a['runway_quarters']:.2f}q" for a in funded) or 'none'))
    cliffs = [a for a in funded if 'Category 1' in str(by_id[a['id']].get('shock_category', ''))]
    valid_awards = all(0 <= a['award_amount'] <= float(by_id[a['id']]['requested_amount']) for a in allocations)
    valid_awards = valid_awards and all(a['award_amount'] == float(by_id[a['id']]['requested_amount']) for a in cliffs)
    valid_awards = valid_awards and sum(a['award_amount'] for a in allocations) <= portfolio['budget'] + 1e-8
    check(5, 'Budget, request caps and indivisible shocks', valid_awards,
          'Total awards stay within budget; no award exceeds its request; funded indivisible shocks receive the full request.',
          f"{len(cliffs)} funded indivisible requests checked; ${portfolio['total_disbursed']:,.2f} allocated from ${portfolio['budget']:,.2f}.")
    check(6, 'Spatial critical mass', spatial['all_clusters_compliant'] if funded else None,
          'Audit cluster counts and the straight-line radius proxy; this is not measured pedestrian access.',
          '; '.join(f"{c['cluster_name']}: {c['funded_storefront_count']} funded, {c['max_inter_storefront_walk_meters']:.0f}m maximum separation, compliant={c['critical_mass_satisfied']}" for c in spatial['clusters']) or 'No clusters.')
    anchors = [a['name'] for a in funded if a['s_cascade'] == 0 and a['s_anchor'] >= 85]
    check(7, 'Essential service representation', bool(anchors) if funded else None,
          'Report whether a high-anchor, zero-cascade applicant is funded; no service coverage is presumed.',
          'Funded zero-cascade anchors: ' + (', '.join(anchors) or 'none'))
    excluded = [a for a in allocations if not a['eligible']]
    check(8, 'Eligibility policy gate', all(a['award_amount'] == 0 for a in excluded),
          'Applicants failing the supplied eligibility policy receive zero. Ownership documents require separate review.',
          f"{len(excluded)} excluded: " + (', '.join(a['name'] for a in excluded) or 'none'))
    check(9, 'Unapplied supplier evidence', None,
          'Supplier outreach requires identifiable source records and confirmed relationships.',
          'No source-verified supplier outreach is certified by this scenario report.')
    check(10, 'Sampled weight sensitivity', sensitivity['status'] == 'SAMPLED_SCENARIO_ANALYSIS' if apps else None,
          'Compare actual funded portfolios under four configurations and 51 sampled weights.',
          sensitivity['crossover_explanation'] + ' Robust in the four sampled configurations: ' + (', '.join(sensitivity['robust_awardee_set_S_robust']) or 'none'))
    artifacts = [
        ('Eligibility and ownership', 'Current registration and ownership evidence'),
        ('Financial condition', 'Cash, operating burn, debt and payroll evidence'),
        ('Vendor or essential service evidence', 'Recurring vendor invoices or essential service certification'),
        ('Shock and spatial review', 'Shock quote, request amount and location review'),
        ('Payment authorization', 'Approved payment instructions and reviewer authorization'),
    ]
    checklist = [{'step': title, 'target_vectors': 'Document review', 'required_artifact': artifact,
                  'gate_type': 'Pre-disbursement review', 'verified': False, 'status': 'REVIEW_REQUIRED'}
                 for title, artifact in artifacts]
    return {
        'overall_compliance_passed': False,
        'audit_scope': 'MODELED_SCENARIO_CHECKS; not a documentary audit or award authorization',
        'scenario_checks_passed': all(v['status'] != 'FAIL' for v in vectors),
        'vectors_passed_count': sum(v['status'] == 'PASS' for v in vectors),
        'total_vectors_checked': len(vectors), 'vector_checks': vectors,
        'field_protocol_checklist': checklist, 'bottleneck_alerts': [],
        'spatial_cluster_audit': spatial, 'sensitivity_summary': sensitivity,
        'portfolio_summary': {key: portfolio[key] for key in (
            'regime', 'budget', 'total_disbursed', 'funded_count', 'direct_jobs_preserved',
            'cost_per_direct_job_preserved', 'total_daily_beneficiaries_touched', 'net_submodular_portfolio_utility')},
    }


def _cell(value: Any) -> str:
    return str(value).replace('|', r'\|').replace('\n', ' ')


def format_red_team_compliance_report_markdown(
    portfolio_result: Optional[Dict[str, Any]] = None,
    applicants: Optional[List[Dict[str, Any]]] = None,
    adk_dir: Optional[str] = None,
) -> str:
    apps = applicants if applicants is not None else get_canonical_applicants()
    portfolio = portfolio_result if portfolio_result is not None else optimize_portfolio_knapsack(apps)
    audit = evaluate_red_team_compliance(portfolio, apps, adk_dir)
    lines = [
        '# Draft scenario analysis — Central Market micro-grants', '',
        'Modeled inputs and assumed grant effects. This report does not approve awards, certify invoices or establish jobs saved.', '',
        f"Regime {portfolio['regime']} · Budget ${portfolio['budget']:,.2f} · Proposed awards ${portfolio['total_disbursed']:,.2f} · Unallocated ${portfolio['remaining_budget']:,.2f}",
        f"{portfolio['funded_count']} modeled awards; {portfolio['direct_jobs_preserved']} associated scenario FTEs (not measured jobs preserved).", '',
        '| Applicant | Request | Proposed award | Decision |', '|---|---:|---:|---|',
    ]
    for a in portfolio['allocations']:
        lines.append(f"| {_cell(a['name'])} | ${a['requested_amount']:,.2f} | ${a['award_amount']:,.2f} | {_cell(a['tier'])} |")
    lines += ['', '## Scenario checks', '', '| Check | Status | Observed result |', '|---|---|---|']
    for v in audit['vector_checks']:
        lines.append(f"| {_cell(v['title'])} | {v['status']} | {_cell(v['portfolio_proof'])} |")
    lines += ['', '## Required document review', '']
    for step in audit['field_protocol_checklist']:
        lines.append(f"- [ ] {step['step']}: {step['required_artifact']}")
    lines += ['', audit['sensitivity_summary']['scope']]
    return '\n'.join(lines)
