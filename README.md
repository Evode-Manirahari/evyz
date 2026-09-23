# EVYZ

EVYZ helps specialist clinics monitor patients between visits. It compares each patient with their own recent measurements and shows which patients changed, and what changed, so the care team can decide who to review.

The first version does not diagnose. The full direction is [Product Blueprint v3.1](docs/product-blueprint-v3.1.md).

## What runs today

Phase 0 is the engine on one public dataset. One unusual day is not an event. An event is two or more signals outside the personal range for at least two days, or one strong signal for at least two days.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python scripts/download_wearableqa.py
pytest
python scripts/run_phase0.py
```

Results land in `data/processed/`.

The local screen reads that same history and asks what happened around an event:

```bash
pip install -e ".[dev,api]"
python scripts/run_screen.py
```

Open http://127.0.0.1:8000/?user=user_131 . Labels are written to `data/processed/feedback.jsonl`. This screen is for reading one history. The clinic review queue is later.

## One real history

Use whichever source is actually available. Put tokens in `.env` and do not commit that file.

```bash
python scripts/run_oura.py
python scripts/run_whoop.py
python scripts/run_fitbit.py
python scripts/run_garmin.py --file summaries.json
python scripts/run_healthkit.py --export export.xml
```

Apple Health is an export from the iPhone Health app. Oura, WHOOP, and Fitbit need a token from that person's account. Field mapping is in [Data sources](docs/data-sources.md).

## Docs

- [Product](docs/product.md)
- [Blueprint v3.1](docs/product-blueprint-v3.1.md)
- [Architecture](docs/architecture.md)
- [Data sources](docs/data-sources.md)
- [Hardware](docs/hardware.md)
