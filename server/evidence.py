"""Versioned applicant evidence reviews; never convert assumptions into observations."""
from __future__ import annotations
import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager
from hashlib import sha256
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceSubmission(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, strict=True)
    version: int = Field(default=0, ge=0)
    cash: float = Field(ge=0, le=1_000_000_000)
    quarterly_operating_burn: float = Field(gt=0, le=1_000_000_000)
    monthly_debt_payment: float | None = Field(default=None, ge=0, le=1_000_000_000)
    direct_employees: int = Field(ge=0, le=100000)
    location_count: int = Field(ge=1, le=100000)
    institutional_ownership_pct: float = Field(ge=0, le=100)
    storefront_certified: bool
    requested_amount: float = Field(gt=0, le=1_000_000)
    shock_category: Literal['indivisible', 'flexible']
    financial_reference: str = Field(min_length=1, max_length=500)
    ownership_reference: str = Field(min_length=1, max_length=500)
    vendor_reference: str = Field(default='', max_length=500)
    notes: str = Field(default='', max_length=2000)
    # References identify documents held by the officer; document contents are not uploaded.

    @model_validator(mode='after')
    def references_are_nonblank(self):
        if not self.financial_reference.strip() or not self.ownership_reference.strip():
            raise ValueError('Financial and ownership references must not be blank')
        from tools.scoring_engine import _money_cents
        for key in ('cash', 'quarterly_operating_burn', 'monthly_debt_payment', 'requested_amount'):
            if getattr(self, key) is not None:
                _money_cents(getattr(self, key), key)
        return self


class EvidenceReview(BaseModel):
    model_config = ConfigDict(extra='forbid')
    version: int = Field(ge=1)
    decision: Literal['verified', 'rejected']
    reviewer: str = Field(min_length=1, max_length=120)
    notes: str = Field(min_length=1, max_length=2000)

    @model_validator(mode='after')
    def nonblank(self):
        if not self.reviewer.strip() or not self.notes.strip():
            raise ValueError('Reviewer and review notes must not be blank')
        return self


class EvidenceConflict(ValueError):
    pass


class EvidenceStore:
    """Append-only revisions with optimistic locking; configure a persistent volume in cloud."""
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get('EVIDENCE_DB_PATH', 'var/evidence.sqlite3'))

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        db = sqlite3.connect(self.path, timeout=10)
        os.chmod(self.path, 0o600)
        db.row_factory = sqlite3.Row
        try:
            with db:
                db.execute('''CREATE TABLE IF NOT EXISTS evidence_events (
                    business_id TEXT NOT NULL, version INTEGER NOT NULL, event TEXT NOT NULL,
                    payload TEXT NOT NULL, actor TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                    PRIMARY KEY (business_id, version))''')
                yield db
        finally:
            db.close()

    def get(self, business_id):
        with self.connect() as db:
            rows = db.execute('SELECT * FROM evidence_events WHERE business_id=? ORDER BY version', (business_id,)).fetchall()
        return _state(business_id, rows)

    def all_states(self):
        with self.connect() as db:
            rows = db.execute('SELECT * FROM evidence_events ORDER BY business_id, version').fetchall()
        groups = {}
        for row in rows:
            groups.setdefault(row['business_id'], []).append(row)
        return {bid: _state(bid, events) for bid, events in groups.items()}

    def append(self, business_id, version, event, payload, actor):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current = db.execute('SELECT COALESCE(MAX(version),0) FROM evidence_events WHERE business_id=?', (business_id,)).fetchone()[0]
            if current != version:
                raise EvidenceConflict('Evidence changed; reload before saving or reviewing')
            if event == 'reviewed':
                prior = db.execute('SELECT event FROM evidence_events WHERE business_id=? ORDER BY version DESC LIMIT 1', (business_id,)).fetchone()
                if not prior or prior['event'] != 'submitted':
                    raise EvidenceConflict('Only a pending submission can be reviewed')
            db.execute('INSERT INTO evidence_events (business_id,version,event,payload,actor) VALUES (?,?,?,?,?)',
                       (business_id, current + 1, event, json.dumps(payload, allow_nan=False), actor))
        return self.get(business_id)


def _state(business_id, rows):
    state = {'business_id': business_id, 'version': 0, 'status': 'MISSING', 'submission': None, 'history': []}
    for row in rows:
        payload = json.loads(row['payload']) if isinstance(row['payload'], str) else row['payload']
        if row['event'] == 'submitted':
            state['submission'] = payload
            state['status'] = 'PENDING_REVIEW'
        else:
            state['status'] = 'VERIFIED_INTAKE' if payload['decision'] == 'verified' else 'REJECTED'
        state['version'] = row['version']
        state['history'].append({'version': row['version'], 'event': row['event'], 'actor': row['actor'],
                                 'created_at': row['created_at'], 'notes': payload.get('notes', '')})
    return state


class GcsEvidenceStore:
    """Atomic object updates with generation preconditions and a retained revision history.

    Use a private versioned bucket. Preconditions prevent concurrent reviewers from
    overwriting each other's submissions: https://cloud.google.com/storage/docs/request-preconditions
    """
    def __init__(self, bucket_name, client=None):
        self.bucket_name, self._client = bucket_name, client

    @property
    def client(self):
        if self._client is None:
            from google.cloud import storage
            self._client = storage.Client()
        return self._client

    def _read(self, business_id):
        from google.api_core.exceptions import NotFound, PreconditionFailed
        key = 'intake/' + sha256(business_id.encode()).hexdigest() + '.json'
        blob = self.client.bucket(self.bucket_name).blob(key)
        for _ in range(3):
            try:
                blob.reload(timeout=10)
                generation = int(blob.generation)
                data = json.loads(blob.download_as_text(if_generation_match=generation, timeout=10))
                if data['business_id'] != business_id:
                    raise ValueError('Evidence identifier mismatch')
                return blob, generation, data['events']
            except NotFound:
                return blob, 0, []
            except PreconditionFailed:
                continue
        raise EvidenceConflict('Evidence changed while reading; reload and retry')

    def get(self, business_id):
        return _state(business_id, self._read(business_id)[2])

    def all_states(self):
        states = {}
        for blob in self.client.list_blobs(self.bucket_name, prefix='intake/', timeout=10):
            data = json.loads(blob.download_as_text(if_generation_match=int(blob.generation), timeout=10))
            states[data['business_id']] = _state(data['business_id'], data['events'])
        return states

    def append(self, business_id, version, event, payload, actor):
        from google.api_core.exceptions import PreconditionFailed
        blob, generation, events = self._read(business_id)
        if (events[-1]['version'] if events else 0) != version:
            raise EvidenceConflict('Evidence changed; reload before saving or reviewing')
        if event == 'reviewed' and (not events or events[-1]['event'] != 'submitted'):
            raise EvidenceConflict('Only a pending submission can be reviewed')
        events.append({'version': version + 1, 'event': event, 'payload': payload, 'actor': actor,
                       'created_at': datetime.now(timezone.utc).isoformat()})
        try:
            blob.upload_from_string(json.dumps({'business_id': business_id, 'events': events}, allow_nan=False),
                                    content_type='application/json', if_generation_match=generation, timeout=10)
        except PreconditionFailed as exc:
            raise EvidenceConflict('Evidence changed; reload before saving or reviewing') from exc
        return _state(business_id, events)


def create_evidence_store():
    bucket = os.environ.get('EVIDENCE_GCS_BUCKET')
    if os.environ.get('K_SERVICE') and not bucket:
        raise RuntimeError('Cloud deployment requires EVIDENCE_GCS_BUCKET; local SQLite is not durable on Cloud Run')
    return GcsEvidenceStore(bucket) if bucket else EvidenceStore()


def evidence_summary(record):
    summary = {'status': record['status'], 'version': record['version'],
               'decision_ready': False, 'missing_decision_inputs': [
                   'validated grant-effect assumptions and model approval',
                   'canonical industry priors and service coverage where used'],
               'note': 'Reviewed intake is documentary evidence, not proof of grant effectiveness or an award approval.'}
    if record['status'] == 'VERIFIED_INTAKE':
        data = record['submission']
        summary['financial_runway_quarters'] = round(data['cash'] / data['quarterly_operating_burn'], 4)
        summary['intake_reviewed'] = True
        if data['monthly_debt_payment'] is None:
            summary['missing_decision_inputs'].append('current debt payments')
        if not data['vendor_reference'].strip():
            summary['missing_decision_inputs'].append('verified vendor evidence')
    else:
        summary['missing_decision_inputs'].append('reviewed current financial and ownership evidence')
    return summary
