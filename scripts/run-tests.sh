#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[1/4] Travel Booking Evidence Gate"
python3 -m unittest discover \
  -s "$ROOT_DIR/gates/travel-booking/src/tests" \
  -v

echo
echo "[2/4] Commerce Listing Preflight"
PYTHONPATH="$ROOT_DIR/gates/commerce-listing/src" \
  python3 -m unittest discover \
  -s "$ROOT_DIR/gates/commerce-listing/src/tests" \
  -v

echo
echo "[3/4] Investment Answer Gate"
PYTHONPATH="$ROOT_DIR/gates/investment-answer/src" \
  python3 -m unittest discover \
  -s "$ROOT_DIR/gates/investment-answer/tests" \
  -v

echo
echo "[4/4] Investment Answer Review Workflow"
PYTHONPATH="$ROOT_DIR/gates/investment-answer/src:$ROOT_DIR/workflows/investment-answer-review/src" \
  python3 -m unittest discover \
  -s "$ROOT_DIR/workflows/investment-answer-review/tests" \
  -v

echo
echo "All 39 tests passed."
