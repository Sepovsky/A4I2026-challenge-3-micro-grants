# Community Economic Resilience & Micro-Grants

Helping grant officers explore where small-business relief could reduce harm
across a neighborhood.

This research prototype focuses on San Francisco’s Central Market corridor. It
combines a modeled business network, historical loan data and applicant evidence
to explain funding scenarios.

## What you can do

- **Follow the connections:** trace how disruptions could affect suppliers and buyers.
- **Review evidence:** save applicant financial and ownership information with a versioned review history.
- **Compare strategies:** explore full grants, smaller working-capital grants and a hybrid approach.
- **Understand the result:** inspect assumptions, sensitivity checks and draft reports.

## How it works

One coordinator works with three specialist agents covering supply relationships,
financial condition and eligibility, and neighborhood impact. Shared Python tools
perform the calculations.

We keep **business exposure**, **historical industry risk** and **assumed grant
effectiveness** separate.

<details>
<summary>See the architecture and approach diagrams</summary>

![Agent architecture: coordinator, three specialists, shared tools and draft reports.](docs/diagrams/agent-architecture.svg)

![Our approach: source evidence and a separate illustrative funding scenario.](docs/diagrams/grant-review-approach.svg)

[Detailed architecture and editable outlines](docs/TECHNICAL_GUIDE.md#agent-architecture)

</details>

## Try it locally

With Python 3.12 or later, run:

```sh
python3 -m pip install -r server/requirements.txt
python3 -m uvicorn server.app:app --host 127.0.0.1 --port 8080 --no-proxy-headers
```

Open the [review console](http://127.0.0.1:8080). It starts in source-evidence mode;
select the illustrative scenario to explore proposed awards.

## Project status

The local review covers **232 registry records and 293 modeled supply links**.
Source-evidence mode provides findings without computing grant awards. Scenario
finances and grant effects are assumptions, and reports remain drafts.
Live cloud validation and the canonical industry-rate export are pending.

## Explore further

- [Technical guide](docs/TECHNICAL_GUIDE.md): implementation, setup, testing, deployment and limitations.
- [Source audit](data/TASK_2_3_REVIEW.md): data quality, coverage and findings.
- [Agent entrypoints](agent/README.md): the four agents and execution modes.
- [License](LICENSE).
