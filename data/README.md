# Local data

Datasets are not committed.

## WearableQA

| | |
| --- | --- |
| Name | WearableQA structured split |
| Source | https://huggingface.co/datasets/facebook/WearableQA |
| License | CC BY-NC 4.0 |
| Path | `data/raw/wearableqa/structured.parquet` |
| Download | `python scripts/download_wearableqa.py` |

Preprocessing is `core/normalization/wearableqa.py`: map daily fields into the EVYZ schema, convert sleep to minutes, and drop duplicate days. Phase 0 then writes `data/processed/timelines.csv`, `events.csv`, and `phase0_summary.txt`.

Do not redistribute this file. The license does not allow commercial use of the dataset.
