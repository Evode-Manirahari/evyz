# Product

Version: Product Blueprint v3.1. The full note is [product-blueprint-v3.1.md](product-blueprint-v3.1.md).

EVYZ helps specialist clinics monitor patients between visits. It keeps a time-ordered record for each patient, compares new measurements with that patient's own recent history, and shows the care team which patients changed and what changed.

The first version does not diagnose. It answers: which patients changed enough that someone should review them today?

## First product

The first product is a clinician review queue. A clinic may be watching hundreds of patients outside the hospital. No one can inspect every heart rate, heart-rate variability, sleep, activity, symptom, and treatment history every day. EVYZ reduces that to a short list.

```text
PATIENTS TODAY

Patient 031     REVIEW
Patient 042     STABLE
```

Opening a patient shows the measurements that moved, the personal range, how long the change has lasted, any symptom the patient reported, and where that sits relative to treatment. The clinician decides what it means.

That queue is not built yet.

## What is built

Phase 0 is the engine on a public dataset: a daily history, a 28-day personal baseline, a sustained change, and a plain-language explanation. The local screen lets one history be read and labeled. It is a way to inspect the engine. It is not the clinic product.

## What comes next, in order

1. One real wearable history, from Oura, WHOOP, or an Apple Watch export.
2. Run that history through the engine that already exists.
3. Ask that person whether an event matched something that actually happened.

In parallel, talk to one kind of specialist. The candidates are oncology treatment monitoring, autoimmune flare monitoring, and respiratory or home-therapy monitoring. Choose one. The answer decides the first clinical workflow.

Symptoms, medication changes, and treatment dates come after one live history works. A specialist reviewing real events comes after that. Ten to twenty patients come after one specialist has used it.

## Labels

The person can say what happened:

sick, poor sleep, stress, hard workout, travel, medication change, treatment side effect, nothing noticeable, other.

Clinician labels come later: useful event, not clinically important, expected after treatment, needs follow-up, measurement problem, unknown.

## Boundary

A good statement names the measurements, the personal range, the dates, and the duration.

A bad statement says the patient is developing pneumonia, or that a treatment is causing cardiotoxicity.

EVYZ shows evidence. The clinician interprets it.

## Business

The first buyer is a clinic, a hospital program, or a similar group that already follows patients between visits. Prove that a clinic wants the list before pricing it. Hardware waits until live use shows a measurement the existing devices do not expose.
