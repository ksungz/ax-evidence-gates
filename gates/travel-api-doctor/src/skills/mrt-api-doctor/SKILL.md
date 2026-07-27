---
name: mrt-api-doctor
description: Review MyRealTrip marketing-partner Open API/MCP integration code against pitfalls documented in the public developer docs, verify the rule quotes against the current docs bundle, and probe the public MCP endpoint without an API key. This is an integration-code quality tool, not a travel recommender.
---

# MRT API Doctor

Use this skill when a user is writing, reviewing, or debugging integration code for the MyRealTrip marketing-partner Open API or MCP, or asks why a MyRealTrip API call fails (401/429/500, empty results, wrong page).

This skill is not a travel recommender and does not call product-search APIs. It is an integration-code quality tool grounded only in the public developer docs (docs.myrealtrip.com). Demos and tests must work without real API keys, account data, or private APIs.

## Knowledge Boundary

Every finding must be backed by a rule in `rules/pitfalls.json`, which quotes the public developer docs verbatim. Do not invent endpoints, field names, hosts, or limits that are not in that registry or in the docs. If asked about behavior the docs do not cover, say the docs do not cover it.

Key documented pitfalls (full quotes in `rules/pitfalls.json`):

- Tour (TNA) search pagination is 1-based with response field `perPage`; accommodation and flight search are 0-based with response field `size`.
- Flight parameters named `fromCityCode`/`toCityCode` actually take an airport code (`airport.code`, e.g. ICN), not a city code (e.g. SEL).
- `/v1/mylink` `targetUrl` over 2,000 characters returns a 500 error.
- `/v1/reservations` max `pageSize` is 300; lookback window is 6 months (non-flight) and 1 month (flight), else 400.
- Per-API rate limits per minute; 429 on excess; monitor `X-RateLimit-Remaining`; docs recommend up to 3 retries.
- `Authorization: Bearer <API_KEY>` — a missing `Bearer` prefix is a documented common cause of 401.
- Reissuing an API key immediately expires the old key.
- Some linked TNA products intermittently return empty detail/option/calendar results; handle empties as a normal flow.

## Quick Demo

When the user sends only "마이리얼트립 API 연동 코드 점검 데모 보여줘" or asks for a demo without providing code, run from the plugin root:

```bash
python3 scripts/integration_lint.py examples/bad_integration.py
```

Show the Korean summary output as-is (it includes severity, file:line, fix, and the doc quote for each finding). Then mention that `examples/good_integration.py` passes clean:

```bash
python3 scripts/integration_lint.py examples/good_integration.py
```

## Rule Evidence Workflow

When the user asks whether the rule quotes are still grounded in public docs, run:

```bash
python3 scripts/verify_rules.py
```

The verifier fetches `https://docs.myrealtrip.com/`, parses the current `assets/index-*.js` script path from the homepage HTML, downloads the bundle, strips HTML tags/entities, normalizes whitespace, and checks each `docQuote`. Do not hardcode a bundle filename. If it fails because of network access or changed docs, report the failure plainly and say the rule registry may need an update.

## Lint Workflow

1. Identify the files or directory containing MyRealTrip integration code (the linter scans `.py .js .jsx .ts .tsx .mjs .cjs`).
2. Run:

```bash
python3 scripts/integration_lint.py <path>... --format korean-summary
```

3. Report findings in Korean, keeping each finding's `조치` (fix) and `근거` (doc quote). Findings are heuristic: tell the user to confirm against the quoted doc text, and treat `참고` (info) items as reminders, not defects.
4. Exit code 1 means at least one `오류` (error) finding; suggest fixing errors before release. Use `--format json` when the user wants machine-readable output.

## MCP Probe Workflow

When the user asks whether the MyRealTrip MCP endpoint is up, or wants to see its tools before integrating:

```bash
python3 scripts/mcp_probe.py
```

This performs JSON-RPC `initialize` and `tools/list` against `https://mcp-servers.myrealtrip.com/mcp` without an API key and prints the tool list. Use `--json` for structured output. If it fails, report the error verbatim — do not guess about server status.

## Q&A Workflow

When the user asks a question like "왜 mylink가 500을 반환하지?" or "투어 검색 페이지가 왜 밀리지?", answer from `rules/pitfalls.json`: quote the matching `docQuote`, then give the `fix`. If no rule matches, say the public docs do not document that case and suggest contacting marketing_partner@myrealtrip.com with the error response body, as the docs instruct.

## Fixtures

`fixtures/` contains synthetic samples (clearly marked `_synthetic`) that demonstrate the documented conventions: `tna_search.response.json` (1-based, `perPage`), `stay_search.response.json` (0-based, `size`), `airport_autocomplete.response.json` (`airport.code` vs `city.code`), and `errors.sample.json` (documented error cases). Use them to explain conventions without an API key. Never present them as real API responses.

## Output

Answer user-facing summaries in Korean. Keep the doc quotes verbatim — they are the evidence. For developer-facing output, prefer the script's JSON. Do not claim affiliation with MyRealTrip or imply access to internal systems; this is an independent tool based on public documentation.
