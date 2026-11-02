import copy
import math
import unittest
from tools.scoring_engine import (get_canonical_applicants, optimize_portfolio_knapsack,
                                  compute_sensitivity_and_robust_awardees, evaluate_spatial_cluster_critical_mass)
from tools.compliance_reporter import evaluate_red_team_compliance, format_red_team_compliance_report_markdown


class AllocationRegressionTests(unittest.TestCase):
    def test_indivisible_shocks_are_never_partially_funded(self):
        for regime in ('A', 'B', 'C'):
            for budget in (0, 1, 4999.99, 5000, 9999.99, 15000, 50000):
                apps = get_canonical_applicants()
                result = optimize_portfolio_knapsack(apps, budget, regime)
                by_id = {a['id']: a for a in apps}
                for award in result['allocations']:
                    if 'Category 1' in by_id[award['id']]['shock_category']:
                        self.assertIn(award['award_amount'], (0, by_id[award['id']]['requested_amount']))

    def test_variable_requests_respect_caps_and_budget_in_every_regime(self):
        for request in (1000, 1234.56, 10000, 20000):
            for regime in ('A', 'B', 'C'):
                for budget in (0, 500.01, 5000, 50000):
                    apps = get_canonical_applicants()
                    for a in apps:
                        a['requested_amount'] = request
                    original = copy.deepcopy(apps)
                    p = optimize_portfolio_knapsack(apps, budget, regime)
                    awards = [a['award_amount'] for a in p['allocations']]
                    self.assertTrue(all(0 <= a <= request for a in awards))
                    self.assertLessEqual(sum(awards), budget + 1e-8)
                    self.assertAlmostEqual(sum(awards) + p['remaining_budget'], budget)
                    self.assertEqual(apps, original)

    def test_default_scenario_still_has_seven_awards(self):
        result = optimize_portfolio_knapsack()
        self.assertEqual(result['total_disbursed'], 50000)
        self.assertEqual(result['funded_count'], 7)

    def test_invalid_inputs_fail_before_allocating(self):
        for value in (-1, math.nan, math.inf, True, .001):
            with self.subTest(budget=value), self.assertRaises(ValueError):
                optimize_portfolio_knapsack(budget=value)
        for regime in ('', 'UNKNOWN', 'AA'):
            with self.assertRaises(ValueError): optimize_portfolio_knapsack(regime=regime)
        for request in (0, -1, math.nan, math.inf, 1.001):
            apps = get_canonical_applicants(); apps[0]['requested_amount'] = request
            with self.assertRaises(ValueError): optimize_portfolio_knapsack(apps)
        apps = get_canonical_applicants()
        with self.assertRaises(ValueError): optimize_portfolio_knapsack(apps + [apps[0]])
        with self.assertRaises(ValueError): optimize_portfolio_knapsack(weights={'w_cascade': 1})

    def test_untyped_scenario_fields_cannot_bypass_numeric_or_boolean_gates(self):
        for updates in ({'equity_multiplier': math.nan}, {'eligible': 'false'},
                        {'location_count': 1.5}, {'direct_employees': 1e308},
                        {'shock_category': 'unknown'}, {'lat': 91}):
            apps = get_canonical_applicants(); apps[0].update(updates)
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                optimize_portfolio_knapsack(apps)

    def test_sensitivity_uses_budgeted_awards_and_reports_sampling(self):
        empty = compute_sensitivity_and_robust_awardees([])
        self.assertEqual(empty['status'], 'INSUFFICIENT_EVIDENCE')
        self.assertIsNone(empty['crossover_phase_boundary_alpha'])
        self.assertEqual(empty['sampled_award_changes'], [])
        self.assertNotIn('Grocer', empty['crossover_explanation'])
        no_budget = compute_sensitivity_and_robust_awardees(budget=0)
        self.assertEqual(no_budget['robust_awardee_set_S_robust'], [])
        self.assertTrue(all(a['top7_frequency'] == 0 for a in no_budget['parameter_invariance_intervals'].values()))

    def test_audit_does_not_certify_documents_or_fixture_names(self):
        apps = get_canonical_applicants()[:1]
        apps[0]['name'] = 'Independent test applicant'
        apps[0]['requested_amount'] = 1000
        p = optimize_portfolio_knapsack(apps, budget=1000)
        audit = evaluate_red_team_compliance(p, apps)
        self.assertFalse(audit['overall_compliance_passed'])
        self.assertTrue(all(not s['verified'] for s in audit['field_protocol_checklist']))
        cliff = next(v for v in audit['vector_checks'] if v['vector_number'] == 5)
        self.assertEqual(cliff['status'], 'PASS')
        report = format_red_team_compliance_report_markdown(p, apps)
        for stale in ('Cumaica', '0.72', 'All 7', '10/10 VECTORS'):
            self.assertNotIn(stale, report)
        self.assertIn('Independent test applicant', report)
        empty = evaluate_red_team_compliance(optimize_portfolio_knapsack([]), [])
        self.assertFalse(empty['overall_compliance_passed'])

    def test_spatial_count_does_not_hide_distant_or_missing_coordinates(self):
        apps = get_canonical_applicants()[:3]
        for i, a in enumerate(apps):
            a.update(cluster_id='test', cluster_vacancy_rate=.5, lat=37 + i, lon=-122)
        result = evaluate_spatial_cluster_critical_mass(apps, [a['id'] for a in apps])
        self.assertFalse(result['all_clusters_compliant'])
        for a in apps:
            a.pop('lat'); a.pop('lon')
        self.assertFalse(evaluate_spatial_cluster_critical_mass(apps, [a['id'] for a in apps])['all_clusters_compliant'])
