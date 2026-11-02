#!/usr/bin/env bash
# One deployment entrypoint for the console; no public ADK development server.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
case "${1:-cloud_run}" in
  cloud_run) exec bash "$REPO_ROOT/scripts/deploy.sh" ;;
  agent_engine) exec python3 "$REPO_ROOT/scripts/deploy_agent_runtime.py" ;;
  *) echo 'Usage: bash deploy_cloud_run.sh [cloud_run|agent_engine]' >&2; exit 2 ;;
esac
