# Data

Raw and processed data are **not committed** (see `.gitignore`). Download them locally:

| Folder | Content | Source |
|---|---|---|
| `data/raw/egms/` | EGMS Ortho vertical + east-west CSV tiles for Tyrol | [EGMS Explorer](https://egms.land.copernicus.eu/) (free account) |
| `data/raw/opencellid/` | `232.csv.gz` (Austria, MCC 232) | [OpenCellID](https://opencellid.org) (free token) |
| `data/processed/` | Parquet outputs: sites, motion and risk tables | generated |

## Pilot area: Tyrol (approximate WGS84 bounding box)
`min_lon=10.1, min_lat=46.6, max_lon=12.97, max_lat=47.75`

## Attribution
- Contains modified Copernicus Land Monitoring Service information (European Ground Motion Service).
- Cell data © OpenCellID / Unwired Labs, licensed CC BY-SA 4.0.
