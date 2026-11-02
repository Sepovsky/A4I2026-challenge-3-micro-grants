"""Authenticated, read-only cloud graph smoke test. Never installs or replaces graph DDL.
Run after publishing the revised notebook/SQL: python scripts/cloud_smoke.py --project ID.
Queries can incur normal BigQuery query charges. Credentials and an existing graph are required.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.bigquery_connector import BigQueryGraphConnector, get_bq_enriched_corridor_sql


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--dataset', default='a4i_econ')
    parser.add_argument('--output', type=Path, default=Path('var/cloud-smoke.json'))
    args = parser.parse_args()
    # Validate identifiers before interpolating them.
    get_bq_enriched_corridor_sql(args.project, args.dataset)
    connector = BigQueryGraphConnector(project_id=args.project, dataset=args.dataset)
    gql = connector.query_gql_multihop_cascade(min_exposed=0, max_hops=2, timeout=60)
    dataset = f'`{args.project}.{args.dataset}'
    sql = f'''WITH paths AS (
      SELECT supplier_id AS seed, buyer_id AS destination FROM {dataset}.supplies_enriched`
      UNION DISTINCT
      SELECT a.supplier_id, b.buyer_id FROM {dataset}.supplies_enriched` a
      JOIN {dataset}.supplies_enriched` b ON a.buyer_id=b.supplier_id
    ), counts AS (
      SELECT seed AS business_id, COUNT(DISTINCT destination) AS exposed_businesses
      FROM paths WHERE seed != destination GROUP BY seed
    ) SELECT b.business_id, COALESCE(c.exposed_businesses,0) AS exposed_businesses
      FROM {dataset}.businesses_enriched` b LEFT JOIN counts c USING (business_id)'''
    table_job = connector._get_client().query(sql)
    table = [dict(r.items()) for r in table_job.result(timeout=60)]
    graph_counts = {r['business_id']: r['exposed_businesses'] for r in gql}
    table_counts = {r['business_id']: r['exposed_businesses'] for r in table}
    if not graph_counts or len(graph_counts) != len(gql) or len(table_counts) != len(table) or graph_counts != table_counts:
        raise RuntimeError('GQL and table traversal disagree, are empty or have duplicate business IDs')
    named = connector.query_gql_shortest_paths(limit=5, max_hops=2, timeout=60)
    if any(graph_counts.values()) and not named:
        raise RuntimeError('Reach exists but no named paths were returned')
    result = {'status': 'PASS', 'checked_at': datetime.now(timezone.utc).isoformat(),
              'project': args.project, 'dataset': args.dataset, 'registry_records': len(table),
              'gql_table_agreement': True, 'named_paths_returned': len(named),
              'table_query_job_id': table_job.job_id,
              'scope': 'Authenticated two-hop GQL/table agreement and named paths; not ADK, MCP or grant-effect validation'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
