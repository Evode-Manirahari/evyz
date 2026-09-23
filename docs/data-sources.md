# Data sources

Phase 0 uses one public dataset as a bootstrap. The next dataset depends on the specialty. If that specialty is oncology, PULSE is the candidate, because it ties wearable days to cancer treatment. Do not add another public file until that choice is made.

Live adapters already exist. The next use of one of them is a single consented history.

## Chosen dataset: WearableQA

[facebook/WearableQA](https://huggingface.co/datasets/facebook/WearableQA) is a benchmark of daily wearable histories from 200 real people, with up to about 500 days each. The structured split stores each day with its measurements, which is what the loader reads.

| | |
| --- | --- |
| Name | WearableQA |
| Source | https://huggingface.co/datasets/facebook/WearableQA |
| Paper | https://arxiv.org/abs/2609.05405 |
| License | CC BY-NC 4.0 |
| Local path | `data/raw/wearableqa/structured.parquet` |
| Download | `python scripts/download_wearableqa.py` |

Signals used when they are present:

```text
resting heart rate  → resting_hr
heart-rate variability → hrv
sleep → sleep_minutes
steps → steps
```

Respiratory rate and skin-temperature delta are in the EVYZ schema and are left empty for this dataset. The file does not identify the watch brand, so HRV is not renamed to RMSSD.

The loader ignores question text, multiple-choice answers, demographics, and blood panels. Those are not wearable measurements, and the benchmark's health questions include diagnostic interpretations EVYZ does not make.

Each benchmark question repeats that person's daily history. The loader keeps the longest history per person, about 500 days, and ignores the question. A gap longer than three days starts a separate timeline.

This dataset is a bootstrap. The license is non-commercial, so it must stay on disk for development and must not ship inside the product. It is not the moat.

## Not used yet: CovIdentify

[CovIdentify](https://physionet.org/content/covidentify/1.0.0/) is the better match for later evaluation because it pairs longitudinal wearable days with symptom and test surveys. The files require a PhysioNet credential and a data-use agreement, so they are not the first local dataset. When that access exists, it should become the second adapter, behind the same canonical schema.

## Live sources

Each adapter emits the same daily schema. A missing field stays missing. Scores such as recovery, strain, stress, and heart-rate zones are not measurements.

Oura, WHOOP, and Fitbit pull with a bearer token. Garmin reads a Health API webhook payload, or pulls with `GARMIN_ACCESS_TOKEN` after Garmin approves the app. Apple Health reads `export.xml` from the iPhone Health app (profile photo, Export All Health Data). None of these scripts invent days when the token or the file is absent.

| Provider | Command | What becomes the daily row |
| --- | --- | --- |
| Oura | `python scripts/run_oura.py` | lowest heart rate, average HRV, sleep seconds, breath, steps, temperature deviation |
| WHOOP | `python scripts/run_whoop.py` | resting heart rate, RMSSD, sleep stages, respiratory rate. No steps. Absolute skin temperature is left empty. |
| Fitbit | `python scripts/run_fitbit.py` | resting heart rate, daily RMSSD, main sleep, steps, breathing rate, nightly temperature change |
| Garmin | `python scripts/run_garmin.py --file summaries.json` | resting heart rate, steps, deep+light+REM, last night HRV, sleep respiration, skin-temperature deviation |
| Apple Health | `python scripts/run_healthkit.py --export export.xml` | resting heart rate, SDNN, asleep stages, watch steps, respiratory rate, wrist-temperature change |

WHOOP needs `read:recovery` and `read:sleep` only. The nap is not the night. Apple Health prefers the Watch when the iPhone recorded the same day, and time in bed is not counted as sleep.

## Oura details

Oura can use a personal access token with only the daily scope: https://cloud.ouraring.com/personal-access-tokens . Set `OURA_ACCESS_TOKEN`. The token is a header, not a URL.

When several Oura sleep documents share a date, the `long_sleep` document is the night. A nap does not replace it. Readiness contributor values are scores from 1 to 100, so they are not copied into heart rate or heart-rate variability. HRV stays in the `hrv` column, because WHOOP's RMSSD, Fitbit's RMSSD, Garmin's overnight average, and Apple's SDNN are not the same calculation.

Android Health Connect is still unbuilt. Official APIs and consented exports only. Do not scrape wearable accounts.

## Preprocessing

```text
read sensor_history
   ↓
rename into the canonical columns
   ↓
convert sleep hours to minutes when the values are on an hour scale
   ↓
collapse duplicate user-days
   ↓
drop implausible values
   ↓
split long calendar gaps
```
