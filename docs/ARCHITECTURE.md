# InfraShield – Architecture & Design Decisions

This document explains *why* the system is built this way. It's written the way a Solutions Architect would present it to a customer: requirements first, then choices, then trade-offs.

## 1. Requirements

| # | Requirement | Type |
|---|---|---|
| R1 | Combine ground-motion measurements with network site locations for a region | Functional |
| R2 | Produce an explainable risk tier per site | Functional |
| R3 | Let non-GIS users ask questions in plain language | Functional |
| R4 | The LLM must never fabricate risk values, only explain computed ones | Trust |
| R5 | Run at near-zero cost when idle (portfolio project) | Cost |
| R6 | Swap the data source (e.g. a national InSAR product) without a rewrite | Extensibility |
| R7 | Fully reproducible deployment | Operations |

## 2. Key decisions

### D1 – Deterministic scoring, LLM only for explanation (R2, R4)
Risk tiers are computed in Python/SQL with fixed, documented thresholds. The agent receives the numbers through tools and turns them into language. This keeps results auditable. An engineer can always ask "why HIGH?" and get the exact points and velocities behind it.

*Trade-off:* rules are simpler than an ML model. That's deliberate: with no labelled "site damaged" dataset, a learned model would be unverifiable.

### D2 – One metric coordinate system: EPSG:3035 (R1)
EGMS Ortho products are delivered in **ETRS89-LAEA (EPSG:3035)**, a metric, equal-area projection for Europe. Site coordinates (WGS84 lat/lon) are reprojected once at ingest. All distance searches then work in metres, with no repeated distance calculations on a sphere.

### D3 – Use the EGMS *Ortho* product, both components (R1)
EGMS offers Basic, Calibrated and Ortho levels. Ortho gives **vertical and east-west** velocities on a 100 m grid, already decomposed from the satellite's viewing geometry. That matters in the Alps, where landslides move mostly *downslope*, which shows up as horizontal motion. Combining both components (√(v² + e²)) avoids missing them.

*Trade-off:* the 100 m grid is coarser than the Basic point data. That's acceptable, because cell site positions are themselves only approximate (see D4).

### D4 – Cluster cells into sites (R1)
A physical mast hosts many cells (several operators, 4G/5G, sectors). OpenCellID positions are crowd-sourced estimates. InfraShield clusters cells into approximate *sites* before scoring, so one mast isn't counted many times.

### D5 – Serverless data lake: S3 + Glue + Athena (R5, R7)
Data volume per region is modest (millions of rows), and queries are occasional. Athena's pay-per-query model costs nothing when idle, and it has built-in geospatial functions. Redshift would be over-sized for this workload.

### D6 – Agent on Bedrock AgentCore with tools behind Gateway (R3, R4)
- **AgentCore Runtime** hosts the Strands agent with session isolation, so no servers are needed.
- **AgentCore Gateway** exposes Lambda functions as MCP tools. Each tool runs a *parameterised* Athena query, so the model can never send free-form SQL to the data.
- **Observability** goes to CloudWatch for traces of every tool call.

*Trade-off:* text-to-SQL would be more flexible, but fixed tools give stronger guarantees for a risk use case. Text-to-SQL can be added later as a read-only "explore" tool.

### D7 – Pluggable sources (R6)
Each data source implements a small interface in `src/infrashield/sources/` and returns a standard table (`x`, `y` in EPSG:3035, `v_up`, `v_east`, metadata). Scoring and the agent depend only on that standard table.

### D8 – Local-first development
The same agent code runs against **Ollama** locally and **Bedrock** in AWS, switched via configuration. That allows fast iteration at zero cost and a clean demo path.

## 3. Cost estimate (pilot region, low traffic)

| Service | Expected monthly cost |
|---|---|
| S3 (a few GB) | < $1 |
| Glue (occasional runs) | ~$1–3 |
| Athena (small scans of partitioned Parquet) | < $1 |
| Lambda + AgentCore + Bedrock tokens (demo use) | a few $ |

*Estimates only. Validate them with the AWS Pricing Calculator before deploying.*

## 4. Security

- No credentials in the repo: `.env` is git-ignored, and AWS uses IAM roles with least privilege.
- Tools are read-only and parameterised, so no free-form SQL reaches the data.
- Only open, public data is used. No operator or employer data.

## 5. Future extensions

- Swiss national InSAR data source, once one is openly available
- Acceleration detection: flag sites where motion is *speeding up*, not just fast
- Real operator site inventory instead of OpenCellID
- Alerting when a new EGMS release changes a site's tier
