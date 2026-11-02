"""Authenticated gateway and console. Source review is the default, scenarios are explicit."""
import hmac
import ipaddress
import json
import logging
import os
from pathlib import Path
from urllib.parse import urlsplit
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from server.evidence import EvidenceConflict, EvidenceReview, EvidenceStore, EvidenceSubmission, evidence_summary, create_evidence_store

BASE_DIR = Path(__file__).resolve().parent.parent
AGENT_RUNTIME_RESOURCE = os.environ.get('AGENT_RUNTIME_RESOURCE') or os.environ.get('AGENT_RUNTIME_ID')
PROJECT_ID = os.environ.get('PROJECT_ID') or os.environ.get('GOOGLE_CLOUD_PROJECT', 'local')
REGION = os.environ.get('REGION', 'us-central1')
logger = logging.getLogger(__name__)
app = FastAPI(title='Central Market micro-grant review', docs_url=None, redoc_url=None)
store = create_evidence_store()


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError):
    # Do not echo financial inputs, tokens, or non-finite JSON values in errors.
    return JSONResponse(status_code=422, content={
        'detail': [{'loc': list(e['loc']), 'msg': e['msg'], 'type': e['type']} for e in exc.errors()]})


def require_access(request: Request):
    configured = os.environ.get('RELIEF_API_TOKEN', '')
    if configured:
        supplied = request.headers.get('authorization', '')
        if not supplied.startswith('Bearer ') or not hmac.compare_digest(supplied[7:].encode('utf-8'), configured.encode('utf-8')):
            raise HTTPException(401, 'Enter the configured access token', headers={'WWW-Authenticate': 'Bearer'})
        return 'authenticated_officer'
    # A missing deployment secret must never expose applicant records.
    host = request.client.host if request.client else ''
    try:
        loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        loopback = False
    requested_host = request.url.hostname or ''
    if loopback and requested_host not in ('localhost', '127.0.0.1', '::1'):
        raise HTTPException(403, 'Local access requires a loopback Host header')
    if not loopback or os.environ.get('K_SERVICE'):
        raise HTTPException(503, 'Server access token is not configured')
    return 'local_officer'


class AgentRunRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, strict=True)
    prompt: str = Field(default='Review the portfolio', max_length=4000)
    mode: Literal['local_csv', 'canonical', 'bigquery'] = 'local_csv'
    budget: float = Field(default=50000, ge=0, le=10_000_000)
    preferred_regime: Literal['A', 'B', 'C'] = 'C'
    weights: dict[str, float] | None = None
    applicants: list[dict[str, Any]] | None = Field(default=None, max_length=500)

    @model_validator(mode='after')
    def validate_inputs(self):
        from tools.scoring_engine import _money_cents
        _money_cents(self.budget, 'budget')
        if self.applicants is not None and self.mode != 'canonical':
            raise ValueError('Custom applicants require explicit canonical scenario mode')
        if self.weights is not None:
            import math
            keys = {'w_cascade', 'w_anchor', 'w_people', 'w_purity'}
            if set(self.weights) != keys or any(not math.isfinite(v) or not 0 <= v <= 1 for v in self.weights.values()) or not math.isclose(sum(self.weights.values()), 1, abs_tol=1e-8):
                raise ValueError('Supply four nonnegative finite weights summing to one')
        return self


class ChatRequest(AgentRunRequest):
    action: Literal['portfolio', 'trace', 'compare', 'what_if', 'variety'] = 'portfolio'
    business_ids: list[str] = Field(default_factory=list, max_length=2)
    max_hops: int = Field(default=2, ge=1, le=8)
    direction: Literal['downstream', 'upstream'] = 'downstream'
    grant_amount: float = Field(default=8000, ge=0, le=1_000_000)

    @model_validator(mode='after')
    def validate_tool_inputs(self):
        from tools.scoring_engine import _money_cents
        _money_cents(self.grant_amount, 'grant_amount')
        if self.action == 'compare' and len(set(self.business_ids)) != len(self.business_ids):
            raise ValueError('Select two distinct business locations')
        return self


def load_apps(mode):
    from tools.bigquery_connector import load_corridor_applicants
    apps, source = load_corridor_applicants(mode, project_id=None if PROJECT_ID == 'local' else PROJECT_ID)
    return apps, source


def source_result(apps, source):
    from tools.resilience_analysis import industry_variety
    states = store.all_states()
    reviewed = []
    for a in apps:
        record = states.get(a['id'], {'status': 'MISSING', 'version': 0})
        reviewed.append({**a, 'intake': evidence_summary(record)})
    readiness = {}
    if source.startswith('LOCAL_REVIEW'):
        audit = json.loads((BASE_DIR / 'data/task_2_3_review.json').read_text())
        readiness = {'rates': audit['audit']['rates_status'],
                     'possible_duplicate_filing_groups': len(audit['audit']['same_name_legal_address_candidates']),
                     'counting_unit': audit['audit']['counting_unit']}
    return {'status': 'EVIDENCE_ONLY', 'source': source, 'applicants': reviewed,
            'data_readiness': readiness,
            'industry_variety': industry_variety(apps),
            'message': 'Modeled exposure and reviewed intake do not establish grant effectiveness. No awards computed.',
            'report_markdown': '# Source evidence review\n\nNo awards approved.\n\n' + ('Data readiness: ' + json.dumps(readiness) + '\n\n' if readiness else '') + '\n'.join(
                f"- {a['name']}: intake {a['intake']['status']}; missing: {', '.join(a['intake']['missing_decision_inputs'])}" for a in reviewed)}


@app.get('/healthz')
def healthz():
    return {'status': 'healthy', 'backend': 'agent_runtime' if AGENT_RUNTIME_RESOURCE else 'local_orchestrator',
            'access': 'token' if os.environ.get('RELIEF_API_TOKEN') else 'loopback_only',
            'evidence_storage': 'gcs' if os.environ.get('EVIDENCE_GCS_BUCKET') else 'local_sqlite'}


@app.post('/api/agent/run', dependencies=[Depends(require_access)])
def run_agent(req: AgentRunRequest):
    try:
        apps, source = (req.applicants, 'SUPPLIED_SCENARIO') if req.applicants is not None else load_apps(req.mode)
        if req.mode != 'canonical':
            return {'success': True, 'source': source, 'data': source_result(apps, source)}
        if AGENT_RUNTIME_RESOURCE:
            try:
                import vertexai
                from vertexai.preview import reasoning_engines
                vertexai.init(project=PROJECT_ID, location=REGION)
                result = reasoning_engines.ReasoningEngine(AGENT_RUNTIME_RESOURCE).query(
                    prompt=req.prompt, applicants=apps, budget=req.budget,
                    preferred_regime=req.preferred_regime, weights=req.weights)
            except Exception:
                logger.exception('Configured remote runtime failed')
                raise HTTPException(502, 'Configured agent runtime is unavailable; no local substitution was performed')
            return {'success': True, 'source': 'agent_runtime', 'data': result}
        from agents.regime_orchestrator_agent import RegimeStressTestOrchestratorAgent
        result = RegimeStressTestOrchestratorAgent().run_pipeline(
            applicants=apps, budget=req.budget, preferred_regime=req.preferred_regime, weights=req.weights)
        return {'success': True, 'source': source, 'data': result}
    except HTTPException:
        raise
    except (ValueError, KeyError, TypeError, OverflowError) as exc:
        raise HTTPException(422, f'Invalid analysis inputs: {exc}') from exc
    except Exception:
        logger.exception('Analysis failed')
        raise HTTPException(503, 'Analysis source is unavailable')


@app.get('/api/corridor/applicants', dependencies=[Depends(require_access)])
def get_corridor_applicants(mode: Literal['local_csv', 'canonical', 'bigquery'] = 'local_csv'):
    try:
        apps, source = load_apps(mode)
        return {'success': True, 'source': source, 'count': len(apps), 'applicants': apps}
    except Exception:
        logger.exception('Applicant source unavailable')
        raise HTTPException(503, 'Applicant source unavailable')


def ensure_business(business_id):
    from tools.resilience_analysis import find_corridor_businesses
    found = find_corridor_businesses(business_id)
    if not any(a['business_id'] == business_id for a in found.get('matches', [])):
        raise HTTPException(404, 'Unknown registry location ID')


@app.get('/api/evidence/{business_id}', dependencies=[Depends(require_access)])
def get_evidence(business_id: str):
    ensure_business(business_id)
    record = store.get(business_id)
    return {**record, 'assessment': evidence_summary(record)}


@app.put('/api/evidence/{business_id}')
def save_evidence(business_id: str, submission: EvidenceSubmission, actor=Depends(require_access)):
    ensure_business(business_id)
    try:
        record = store.append(business_id, submission.version, 'submitted', submission.model_dump(), actor)
        return {**record, 'assessment': evidence_summary(record)}
    except EvidenceConflict as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post('/api/evidence/{business_id}/review')
def review_evidence(business_id: str, review: EvidenceReview, actor=Depends(require_access)):
    ensure_business(business_id)
    try:
        record = store.append(business_id, review.version, 'reviewed', review.model_dump(), f'{actor}:{review.reviewer}')
        return {**record, 'assessment': evidence_summary(record)}
    except EvidenceConflict as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post('/api/chat', dependencies=[Depends(require_access)])
def chat(req: ChatRequest):
    """A deterministic tool console, explicitly labeled; no canned or model-authored claims."""
    from tools.resilience_analysis import analyze_corridor_impact, review_industry_variety
    from tools.scoring_engine import marginal_survival_lift
    if req.action == 'portfolio':
        result = run_agent(AgentRunRequest(**req.model_dump(include=set(AgentRunRequest.model_fields))))
        return {'execution': 'DETERMINISTIC_BACKEND', 'tool': 'run_pipeline', 'result': result['data']}
    if req.action == 'variety':
        return {'execution': 'DETERMINISTIC_BACKEND', 'tool': 'review_industry_variety', 'result': review_industry_variety()}
    count = 2 if req.action == 'compare' else 1
    if len(req.business_ids) != count:
        raise HTTPException(422, f'Select {count} business location(s) for this action')
    if req.action == 'what_if':
        apps, _ = load_apps(req.mode)
        selected = next((a for a in apps if a['id'] == req.business_ids[0]), None)
        if selected is None:
            raise HTTPException(404, 'Unknown applicant ID in selected mode')
        if req.mode != 'canonical':
            result = {'status': 'EVIDENCE_ONLY', 'message': 'Grant effectiveness is not validated for source records; no survival lift estimated.'}
        else:
            amount = min(req.grant_amount, selected['requested_amount'])
            cliff = 'Category 1' in selected['shock_category']
            result = {'status': 'MODELED_SCENARIO', 'business': selected['name'], 'grant_amount': amount,
                      'request_capped': amount != req.grant_amount,
                      'shock_fully_covered': amount >= selected['requested_amount'],
                      'assumed_survival_lift': 0 if cliff and amount < selected['requested_amount'] else marginal_survival_lift(selected['runway_quarters'], amount, selected['burn_rate']),
                      'note': 'Scenario assumptions; not measured grant effectiveness.'}
        return {'execution': 'DETERMINISTIC_BACKEND', 'tool': 'grant_what_if', 'result': result}
    if req.mode == 'canonical':
        raise HTTPException(422, 'Select source evidence mode to trace registry graph paths')
    if req.mode == 'bigquery':
        if req.direction != 'downstream':
            raise HTTPException(422, 'Cloud named paths currently support downstream supply exposure; use local evidence for reverse traversal')
        from tools.bigquery_connector import BigQueryGraphConnector
        connector = BigQueryGraphConnector(project_id=None if PROJECT_ID == 'local' else PROJECT_ID)
        try:
            paths = connector.query_gql_shortest_paths(limit=1000, max_hops=req.max_hops, business_ids=req.business_ids)
            result = {'status': 'EVIDENCE_ONLY', 'gql_executed': True, 'max_hops': req.max_hops,
                      'comparison': [{'root': bid, 'paths': [p for p in paths if p['seed_id'] == bid]} for bid in req.business_ids],
                      'paths_may_be_truncated': len(paths) == 1000}
        except Exception:
            logger.exception('Cloud named path query failed')
            raise HTTPException(503, 'Cloud graph query failed; no local paths were substituted')
    else:
        apps, _ = load_apps('local_csv')
        names = {a['id']: a['name'] for a in apps}
        result = [analyze_corridor_impact(bid, req.max_hops, req.direction) for bid in req.business_ids]
        for trace in result:
            for endpoint in trace.get('endpoints', []):
                endpoint['named_path'] = [{'business_id': bid, 'name': names.get(bid, bid)} for bid in endpoint['path']]
    return {'execution': 'DETERMINISTIC_BACKEND', 'tool': 'analyze_corridor_impact' if req.mode == 'local_csv' else 'query_gql_shortest_paths', 'result': result}


@app.middleware('http')
async def security_headers(request: Request, call_next):
    # Reject cross-origin mutations even on loopback; tokens stay in browser memory.
    origin = request.headers.get('origin')
    # Compare host and port, allowing TLS termination at the private Cloud Run ingress.
    if request.method in ('POST', 'PUT', 'DELETE') and origin:
        parsed_origin = urlsplit(origin)
        if parsed_origin.scheme not in ('http', 'https') or parsed_origin.netloc.lower() != request.headers.get('host', '').lower():
            return Response('Cross-origin mutation rejected', status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


app.mount('/', StaticFiles(directory=BASE_DIR / 'ADK', html=True), name='console')
