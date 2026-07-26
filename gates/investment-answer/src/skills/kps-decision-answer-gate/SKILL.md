---
name: kps-decision-answer-gate
description: Use this skill to run the local KPS Decision Answer Gate on Markdown or JSON draft answers and summarize findings about risky investment wording, missing user context, missing public evidence URLs, and missing risk or limitation explanations. This is a reproducible sample-data QA gate, not investment advice or compliance certification.
---

# KPS Decision Answer Gate

Use this skill when the user asks to inspect a counseling or guidance draft answer, 상담 답변, UX copy, or fixture with KPS Decision Answer Gate.

## Purpose

This plugin is a local quality gate for sample Markdown/JSON counseling or guidance drafts based on public Kakao Pay Securities materials. It checks whether a draft answer helps a beginner investor move through a reasonable confirmation process instead of receiving a buy/sell conclusion.

It does not recommend securities, predict returns, decide suitability, certify legal compliance, call Kakao Pay Securities internal systems, or use accounts, private customer data, real-time quotes, or non-public APIs.

## How To Run

Prefer the repository-root command when the project folder is open:

```bash
python3 src/scripts/kps_gate.py check src/examples/bad-answer.md --format markdown
```

If Codex is operating from the plugin root itself, use:

```bash
python3 scripts/kps_gate.py check examples/bad-answer.md --format markdown
```

For JSON output:

```bash
python3 src/scripts/kps_gate.py check src/examples/better-answer.md --format json
```

For all bundled fixtures:

```bash
python3 src/scripts/kps_gate.py check src/examples --format markdown
```

## Reporting Rules

When reporting results:

- Say this is a sample-data-based quality review, not investment advice, legal judgment, suitability judgment, or compliance approval.
- Lead with high-severity findings, then missing context/evidence/risk explanation findings.
- Preserve the finding fields: `evidence_id`, `evidence_url`, `location`, and `suggestion`.
- Do not invent internal APIs, internal counseling systems, live market data, or account-specific capabilities.
- If the input is a direct investment question, frame the output as "검토 필요 신호" and "보완 제안" rather than a final answer to the investor.

## Expected Use

The default Try Chat prompts should naturally run one of the bundled fixtures. A good first response is to run the local command, summarize the finding count, and highlight the most important correction suggestions.
