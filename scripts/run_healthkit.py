"""Run the daily pipeline on an Apple Health export.xml.

On iPhone: Health app, profile photo, Export All Health Data. Unzip the
export and pass the export.xml path.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.healthkit.normalize import health_export_to_daily
from integrations.output import publish


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, required=True, help="Path to export.xml")
    parser.add_argument("--user", default="healthkit")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "processed" / "healthkit")
    args = parser.parse_args()
    if not args.export.exists():
        sys.exit(f"Export not found at {args.export}.")
    daily = health_export_to_daily(args.user, args.export)
    results = publish(
        daily,
        out=args.out,
        heading="APPLE HEALTH",
        note="Heart-rate variability is Apple's SDNN. Wrist temperature is the change from baseline.",
        events_file="data/processed/healthkit/events.csv",
    )
    if not results:
        sys.exit("The export did not contain resting heart rate, sleep, or steps.")


if __name__ == "__main__":
    main()
