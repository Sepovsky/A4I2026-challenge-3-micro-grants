import importlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
    from server.evidence import EvidenceStore
    gateway = importlib.import_module('server.app')
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

BID = '1088753-08-161'


def submission():
    return dict(version=0, cash=12000, quarterly_operating_burn=30000, monthly_debt_payment=None,
                direct_employees=5, location_count=1, institutional_ownership_pct=0,
                storefront_certified=True, requested_amount=10000, shock_category='indivisible',
                financial_reference='Officer vault: bank-statement-01', ownership_reference='Officer vault: ownership-01',
                vendor_reference='', notes='Submitted for documentary review')


@unittest.skipUnless(AVAILABLE, 'Install server requirements and httpx for gateway tests')
class GatewayIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'RELIEF_API_TOKEN': '', 'K_SERVICE': ''})
        self.env.start()
        self.store = patch.object(gateway, 'store', EvidenceStore(Path(self.temp.name) / 'evidence.sqlite3'))
        self.store.start()
        self.runtime = patch.object(gateway, 'AGENT_RUNTIME_RESOURCE', None); self.runtime.start()
        self.client = TestClient(gateway.app, base_url='http://127.0.0.1', client=('127.0.0.1', 50000))

    def tearDown(self):
        self.client.close(); self.runtime.stop(); self.store.stop(); self.env.stop(); self.temp.cleanup()

    def test_default_is_source_evidence_and_static_console_uses_api(self):
        response = self.client.post('/api/agent/run', json={})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()['data']
        self.assertEqual(data['status'], 'EVIDENCE_ONLY')
        self.assertEqual(len(data['applicants']), 232)
        self.assertNotIn('selected_portfolio', data)
        self.assertNotIn('cash', data['applicants'][0])
        self.assertEqual(self.client.get('/').status_code, 200)
        script = self.client.get('/js/app.js').text
        self.assertIn('/api/agent/run', script)
        self.assertNotIn('APPLICANTS_DATA', script)
        self.assertNotIn('innerHTML', script)

    def test_api_rejects_invalid_budget_regime_weights_and_implicit_scenarios(self):
        for body in ({'budget': -1}, {'budget': 1e15}, {'budget': .001}, {'preferred_regime': 'Z'},
                     {'weights': {'w_cascade': 1}}, {'applicants': []}, {'mode': 'unknown'}):
            with self.subTest(body=body):
                self.assertEqual(self.client.post('/api/agent/run', json=body).status_code, 422)

    def test_nonfinite_and_boolean_inputs_are_rejected_without_echoing_data(self):
        for payload in ('{"budget":NaN}', '{"budget":Infinity}', '{"budget":true}'):
            response = self.client.post('/api/agent/run', content=payload, headers={'Content-Type': 'application/json'})
            self.assertEqual(response.status_code, 422, response.text)
            self.assertNotIn('"input"', response.text)

    def test_tls_termination_is_allowed_but_rebound_local_hosts_are_not(self):
        self.assertEqual(self.client.get('/api/corridor/applicants', headers={'Host': 'attacker.example'}).status_code, 403)
        with patch.dict(os.environ, {'RELIEF_API_TOKEN': 'token', 'K_SERVICE': 'cloud-run'}):
            response = self.client.post('/api/agent/run', json={}, headers={
                'Authorization': 'Bearer token', 'Host': 'review.example', 'Origin': 'https://review.example'})
            self.assertEqual(response.status_code, 200, response.text)

    def test_scenario_awards_and_report_share_the_same_backend_result(self):
        response = self.client.post('/api/agent/run', json={'mode': 'canonical', 'budget': 5000})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()['data']; portfolio = data['selected_portfolio']
        for a in portfolio['allocations']:
            if 'Category 1' in a['shock_category']:
                self.assertEqual(a['award_amount'], 0)
        self.assertIn('$5,000.00', data['red_team_compliance_report_markdown'])
        self.assertEqual(portfolio['total_disbursed'], data['regimes_comparison']['regimes']['C']['total_disbursed'])

    def test_source_paths_and_what_if_remain_grounded(self):
        data = self.client.post('/api/chat', json={'action': 'trace', 'business_ids': [BID], 'max_hops': 6}).json()
        self.assertEqual(data['execution'], 'DETERMINISTIC_BACKEND')
        self.assertEqual(data['result'][0]['status'], 'OK')
        self.assertEqual(data['result'][0]['endpoints'][0]['named_path'][0]['name'], 'Sour Flour')
        data = self.client.post('/api/chat', json={'action': 'what_if', 'business_ids': [BID]}).json()
        self.assertEqual(data['result']['status'], 'EVIDENCE_ONLY')
        self.assertNotIn('assumed_survival_lift', data['result'])

    def test_evidence_is_versioned_reviewed_and_persisted_without_award_approval(self):
        path = f'/api/evidence/{BID}'
        self.assertEqual(self.client.get(path).json()['status'], 'MISSING')
        saved = self.client.put(path, json=submission())
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(saved.json()['status'], 'PENDING_REVIEW')
        self.assertEqual(self.client.put(path, json=submission()).status_code, 409)
        review = dict(version=1, decision='verified', reviewer='Test officer', notes='References inspected against documents')
        result = self.client.post(path + '/review', json=review)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()['assessment']['financial_runway_quarters'], .4)
        self.assertFalse(result.json()['assessment']['decision_ready'])
        reopened = EvidenceStore(gateway.store.path).get(BID)
        self.assertEqual(reopened['status'], 'VERIFIED_INTAKE')
        self.assertEqual(len(reopened['history']), 2)
        self.assertEqual(self.client.post(path + '/review', json={**review, 'version': 2}).status_code, 409)
        body = submission(); body['version'] = 2; body['cash'] = 15000
        edited = self.client.put(path, json=body).json()
        self.assertEqual(edited['status'], 'PENDING_REVIEW')
        self.assertNotIn('financial_runway_quarters', edited['assessment'])
        current = self.client.post('/api/agent/run', json={}).json()['data']
        self.assertEqual(next(a for a in current['applicants'] if a['id'] == BID)['intake']['version'], 3)
        self.assertEqual(current['status'], 'EVIDENCE_ONLY')

    def test_invalid_evidence_and_unknown_registry_ids_are_rejected(self):
        for updates in ({'cash': -1}, {'quarterly_operating_burn': 0}, {'financial_reference': '  '},
                        {'decision_ready': True}, {'cash': .001}):
            self.assertEqual(self.client.put(f'/api/evidence/{BID}', json={**submission(), **updates}).status_code, 422)
        self.assertEqual(self.client.put('/api/evidence/cm_01', json=submission()).status_code, 404)
        self.assertEqual(self.client.post(f'/api/evidence/{BID}/review', json=dict(version=1, decision='verified', reviewer='X', notes='Reviewed')).status_code, 409)

    def test_token_auth_and_cross_origin_protection(self):
        with patch.dict(os.environ, {'RELIEF_API_TOKEN': 'test-officer-token'}):
            self.assertEqual(self.client.get('/api/corridor/applicants').status_code, 401)
            self.assertEqual(self.client.get('/api/corridor/applicants', headers={'Authorization': 'Bearer wrong'}).status_code, 401)
            self.assertEqual(self.client.get('/api/corridor/applicants', headers={'Authorization': 'Bearer test-officer-token'}).status_code, 200)
            self.assertEqual(self.client.post('/api/agent/run', json={}, headers={'Origin': 'https://external.example', 'Authorization': 'Bearer test-officer-token'}).status_code, 403)
        remote = TestClient(gateway.app, base_url='http://127.0.0.1', client=('198.51.100.1', 50000))
        self.assertEqual(remote.get('/api/corridor/applicants', headers={'X-Forwarded-For': '127.0.0.1'}).status_code, 503)
        remote.close()
        with patch.dict(os.environ, {'K_SERVICE': 'deployed-service'}):
            self.assertEqual(self.client.get('/api/corridor/applicants').status_code, 503)

    def test_remote_receives_selected_applicants_and_failure_is_not_silently_substituted(self):
        vertex = ModuleType('vertexai'); vertex.init = lambda **kwargs: None
        remote_query = unittest.mock.Mock(return_value={'status': 'REMOTE_RESULT'})
        preview = ModuleType('vertexai.preview')
        preview.reasoning_engines = SimpleNamespace(ReasoningEngine=lambda resource: SimpleNamespace(query=remote_query))
        with patch.object(gateway, 'AGENT_RUNTIME_RESOURCE', 'test-resource'), patch.dict('sys.modules', {'vertexai': vertex, 'vertexai.preview': preview}):
            response = self.client.post('/api/agent/run', json={'mode': 'canonical'})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(len(remote_query.call_args.kwargs['applicants']), 11)
            remote_query.side_effect = RuntimeError('do not expose secret error')
            with self.assertLogs(gateway.logger, level='ERROR'):
                response = self.client.post('/api/agent/run', json={'mode': 'canonical'})
            self.assertEqual(response.status_code, 502)
            self.assertNotIn('secret error', response.text)


class DeploymentRegressionTests(unittest.TestCase):
    def test_deploy_preserves_dockerfile_and_uses_private_service_even_on_failure(self):
        root = Path(__file__).resolve().parents[1]
        original = (root / 'Dockerfile').read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            cli = Path(temp) / 'gcloud'
            cli.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$DEPLOY_ARGUMENTS"\nexit "$DEPLOY_EXIT"\n'); cli.chmod(0o755)
            env = {**os.environ, 'PATH': temp + os.pathsep + os.environ['PATH'], 'PROJECT_ID': 'test-project',
                   'SERVICE_ACCOUNT': 'test@example.invalid', 'API_TOKEN_SECRET': 'test-secret',
                   'EVIDENCE_GCS_BUCKET': 'test-evidence', 'DEPLOY_ARGUMENTS': str(Path(temp)/'args')}
            for code in (0, 1):
                result = subprocess.run(['bash', 'scripts/deploy.sh'], cwd=root, env={**env, 'DEPLOY_EXIT': str(code)}, capture_output=True)
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertEqual((root / 'Dockerfile').read_bytes(), original)
                args = (Path(temp)/'args').read_text()
                self.assertIn('--no-allow-unauthenticated', args)
                self.assertNotIn('--allow-unauthenticated', args)
                self.assertIn('EVIDENCE_GCS_BUCKET=test-evidence', args)
