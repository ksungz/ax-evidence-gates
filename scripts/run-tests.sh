#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[1/3] Travel Booking Evidence Gate"
python3 -m unittest discover \
  -s "$ROOT_DIR/gates/travel-booking/src/tests" \
  -v

echo
echo "[2/3] Commerce Listing Preflight"
PYTHONPATH="$ROOT_DIR/gates/commerce-listing/src" \
  python3 -m unittest discover \
  -s "$ROOT_DIR/gates/commerce-listing/src/tests" \
  -v

echo
echo "[3/3] Investment Answer Gate"
PYTHONPATH="$ROOT_DIR/gates/investment-answer/src" \
  python3 -m unittest discover \
  -s "$ROOT_DIR/gates/investment-answer/tests" \
  -v

echo
echo "All 33 tests passed."
