#!/usr/bin/env bash
# Local CI mirror — runs the exact same checks as .github/workflows/ci.yml
# Usage: ./scripts/ci-check.sh
set -euo pipefail

echo "=== ruff check ==="
uv run ruff check .

echo "=== ruff format --check ==="
uv run ruff format --check .

echo "=== mypy ==="
uv run mypy tame/ --ignore-missing-imports

echo "=== pytest ==="
uv run pytest tests/ --tb=short -v

echo "=== build ==="
uv build

echo ""
echo "All CI checks passed!"
