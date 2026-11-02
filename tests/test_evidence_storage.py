"""Exercise the storage adapter's optimistic locking without cloud credentials."""
import json
import unittest
try:
    from google.api_core.exceptions import NotFound, PreconditionFailed
    from server.evidence import GcsEvidenceStore, EvidenceConflict
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


class FakeBlob:
    def __init__(self, client, name):
        self.client, self.name, self.generation = client, name, None

    def reload(self, **kwargs):
        if self.name not in self.client.objects:
            raise NotFound('Object not found')
        self.generation = self.client.objects[self.name][0]

    def download_as_text(self, if_generation_match, **kwargs):
        generation, text = self.client.objects[self.name]
        if generation != if_generation_match:
            raise PreconditionFailed('Generation changed')
        return text

    def upload_from_string(self, text, if_generation_match, **kwargs):
        self.client.preconditions.append(if_generation_match)
        current = self.client.objects.get(self.name, (0, ''))[0]
        if self.client.conflict:
            self.client.conflict = False
            raise PreconditionFailed('Concurrent write')
        if if_generation_match != current:
            raise PreconditionFailed('Generation changed')
        self.client.objects[self.name] = (current + 1, text)


class FakeClient:
    def __init__(self):
        self.objects, self.preconditions, self.conflict = {}, [], False

    def bucket(self, name): return self
    def blob(self, name): return FakeBlob(self, name)
    def list_blobs(self, bucket, prefix, **kwargs):
        blobs = [self.blob(name) for name in self.objects if name.startswith(prefix)]
        for blob in blobs: blob.reload()
        return blobs


@unittest.skipUnless(AVAILABLE, 'Install server requirements for Cloud Storage adapter checks')
class GcsEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeClient()
        self.store = GcsEvidenceStore('private-test-bucket', self.client)

    def test_create_review_reload_and_edit_retain_history(self):
        self.assertEqual(self.store.get('location')['version'], 0)
        result = self.store.append('location', 0, 'submitted', {'cash': 10}, 'officer')
        self.assertEqual(result['status'], 'PENDING_REVIEW')
        result = self.store.append('location', 1, 'reviewed', {'decision': 'verified'}, 'reviewer')
        self.assertEqual(result['status'], 'VERIFIED_INTAKE')
        result = self.store.append('location', 2, 'submitted', {'cash': 20}, 'officer')
        self.assertEqual(result['status'], 'PENDING_REVIEW')
        self.assertEqual(len(self.store.get('location')['history']), 3)
        self.assertEqual(self.client.preconditions, [0, 1, 2])
        self.assertEqual(self.store.all_states()['location']['version'], 3)

    def test_stale_version_and_concurrent_cloud_write_are_conflicts(self):
        self.store.append('location', 0, 'submitted', {}, 'officer')
        with self.assertRaises(EvidenceConflict):
            self.store.append('location', 0, 'submitted', {}, 'officer')
        self.client.conflict = True
        with self.assertRaises(EvidenceConflict):
            self.store.append('location', 1, 'reviewed', {'decision': 'verified'}, 'reviewer')
        self.assertEqual(self.store.get('location')['version'], 1)
        self.assertEqual(self.store.get('location')['status'], 'PENDING_REVIEW')

    def test_cloud_paths_filter_bound_ids_before_applying_limit(self):
        from unittest.mock import Mock
        from tools.bigquery_connector import BigQueryGraphConnector
        connector = BigQueryGraphConnector(project_id='test-project')
        connector._client = Mock()
        connector._client.query.return_value.result.return_value = []
        identifier = "location' OR TRUE --"
        connector.query_gql_shortest_paths(business_ids=[identifier], timeout=3)
        call = connector._client.query.call_args
        self.assertNotIn(identifier, call.args[0])
        self.assertLess(call.args[0].index('WHERE seed_id IN'), call.args[0].index('LIMIT'))
        self.assertEqual(call.kwargs['job_config'].query_parameters[0].values, [identifier])
        connector._client.query.return_value.result.assert_called_once_with(timeout=3)

    def test_review_requires_pending_submission(self):
        with self.assertRaises(EvidenceConflict):
            self.store.append('location', 0, 'reviewed', {'decision': 'verified'}, 'reviewer')
        self.store.append('location', 0, 'submitted', {}, 'officer')
        self.store.append('location', 1, 'reviewed', {'decision': 'rejected'}, 'reviewer')
        with self.assertRaises(EvidenceConflict):
            self.store.append('location', 2, 'reviewed', {'decision': 'verified'}, 'reviewer')
