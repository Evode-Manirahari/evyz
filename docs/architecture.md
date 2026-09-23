# Architecture

Version: Product Blueprint v3.1. The product direction is in [product.md](product.md).

EVYZ keeps a time-ordered record for each patient and compares new measurements with that patient's own recent history. The product question is which patients changed enough that a care team should review them, and what changed.

## Loop

```text
CONNECT
   ↓
COLLECT
   ↓
NORMALIZE
   ↓
CHECK QUALITY
   ↓
LEARN PERSONAL NORMAL
   ↓
CALCULATE PERSONALIZED FEATURES
   ↓
DETECT CHANGE
   ↓
COMBINE MULTIPLE SIGNALS
   ↓
CREATE EVENT
   ↓
EXPLAIN
   ↓
USER FEEDBACK
   ↓
LEARN
```

Phase 0 implements normalization through explanation on a public dataset. The local screen shows one history and stores the person's label for an event. Live adapters exist for Oura, WHOOP, Fitbit, Garmin, and an Apple Health export. The next use of those adapters is one real history, not more providers. The clinician review queue comes after that history has been labeled.

## Canonical day

Every provider is translated into one daily row before any baseline is calculated.

```text
user_id
date
resting_hr
hrv
sleep_minutes
steps
respiratory_rate
skin_temperature_delta
source
```

Missing columns stay missing. Heart-rate variability is stored as `hrv` with the source's own units. EVYZ does not assume two devices compute HRV the same way.

The long-term measurement record is the same idea at a timestamp:

```text
user_id, timestamp, metric, value, unit, source, measurement_context
```

## Engines

Quality rejects implausible values, duplicate days, and histories that are too short. The result in that case is "Insufficient data."

The baseline is a rolling 28-day median, with the 10th and 90th percentiles and the median absolute deviation. The current day is not part of its own baseline. A gap longer than three days starts a new timeline so old history is not treated as recent.

Personalized features are the absolute difference, the percent change when the baseline is far enough from zero, the robust z-score, a 3-day slope, and the count of consecutive abnormal days.

Detection is two-sided. A day is unusual when the robust z-score reaches 2, and strong when it reaches 3. Those thresholds live in `PipelineConfig`.

Events use two rules:

- two or more signals are unusual on the same days for at least two days
- one signal is strong for at least two days

The explanation names the signals, the recent range, the size of the change, the start date, and the duration. It does not produce a score, and it does not name a disease.

The person can label an event as sick, poor sleep, stress, hard workout, travel, medication change, treatment side effect, nothing noticeable, or other. Clinician labels are specified and not collected yet.

## Repository

```text
core/            normalization, quality, baseline, features, detection, events, insights, feedback
integrations/    Oura, WHOOP, Fitbit, Garmin, and Apple Health export
apps/api/        local screen and status endpoint, on the public history
db/models/       the five tables, not deployed
data/            local datasets, not committed
scripts/         download and phase-0 run
tests/
docs/
```

## What phase 0 deliberately leaves out

A multi-user OAuth server, the Expo phone app, the clinician review queue, PostgreSQL as a running service, an LLM, and hardware. Each live adapter runs the same pipeline once a token or an Apple Health export is present.

An LLM, when one is added, may only rephrase a structured finding the statistical layer already produced.
