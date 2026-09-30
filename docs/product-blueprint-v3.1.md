# EVYZ

## Product Blueprint v3.1

**Purpose:** Define exactly what EVYZ should build next.

**Rule:** No broad health claims. No generic “AI health platform.” No custom hardware until the software proves what data is missing.

---

# 1. What EVYZ Is

EVYZ is software for specialist clinics that monitor patients between visits.

EVYZ connects to wearable and home-health data, keeps a time-ordered record for each patient, compares new measurements with that patient’s own recent history, groups sustained changes into events, and shows the care team which patients changed and what changed.

EVYZ does not diagnose disease in the first version.

It answers:

> **Which patients changed enough that someone on the care team should review them today, and what changed?**

---

# 2. What EVYZ Is Not

EVYZ is not:

- another readiness score
- another sleep score
- another fitness tracker
- a chatbot that guesses diagnoses
- a replacement for a doctor
- a new bracelet in the first version
- a system that changes medication or oxygen settings on its own

Existing wearables already measure heart rate, HRV, sleep, activity, temperature, oxygen saturation, and other signals.

EVYZ starts by using those measurements instead of rebuilding the sensors.

---

# 3. First Product

The first product is a clinician review queue.

A clinic may have 100, 500, or 2,000 patients being monitored outside the hospital.

The problem is not that the clinic has no data.

The problem is that no person can manually inspect every patient’s heart rate, HRV, sleep, activity, oxygenation, symptoms, and treatment history every day.

EVYZ reduces that data into a short list of patients whose measurements changed enough to review.

Example:

```text
PATIENTS TODAY

Patient 031     REVIEW
Patient 042     STABLE
Patient 057     REVIEW
Patient 061     STABLE
```

Clicking **Patient 031** should show:

```text
WHAT CHANGED

Resting heart rate
Baseline: 58–62 bpm
Current: 69 bpm
Duration: 3 days

HRV
Baseline: 48–62 ms
Current: 37 ms
Duration: 3 days

Activity
Baseline: 6,800 steps/day
Current: 3,900 steps/day
Duration: 4 days

Symptoms
Patient reports more fatigue since Monday.

Treatment context
Last treatment: 5 days ago.
```

The clinician decides what the change means.

---

# 4. Product Boundary

EVYZ should report measurements and patterns that can be traced back to the source data.

Good output:

> Resting heart rate has stayed above this patient’s recent range for three days. HRV and daily activity also moved below their recent ranges during the same period.

Bad output:

> The patient is developing pneumonia.

Good output:

> This patient’s measurements changed after treatment cycle 3 more than they did after cycles 1 and 2.

Bad output:

> The treatment is causing cardiotoxicity.

The first version shows evidence. The clinician interprets it.

---

# 5. Data EVYZ Uses

EVYZ should accept four categories of information.

## A. Wearable measurements

Examples:

- resting heart rate
- heart-rate variability
- respiratory rate
- sleep duration
- activity / steps
- temperature
- oxygen saturation when available

Possible sources:

- Apple HealthKit
- Oura
- WHOOP
- Fitbit
- Garmin

## B. Home medical-device measurements

Examples:

- pulse oximeter
- blood-pressure cuff
- connected scale
- glucose monitor
- oxygen concentrator
- CPAP device

EVYZ should only add a device when it matters for the first clinical workflow.

## C. Patient-reported information

Examples:

- breathlessness
- fatigue
- pain
- dizziness
- poor sleep
- nausea
- stress
- medication changes
- hard workout
- travel

## D. Clinical context

Examples:

- diagnosis
- treatment dates
- medication start / stop dates
- prescribed therapy
- recent visit
- relevant lab values

Clinical context is what separates EVYZ from a generic wearable dashboard.

---

# 6. Core Data Flow

```text
WEARABLE / HOME DEVICE / PATIENT INPUT / CLINICAL CONTEXT
                         ↓
                      INGEST
                         ↓
                    NORMALIZE
                         ↓
                    DATA QUALITY
                         ↓
                  PATIENT HISTORY
                         ↓
                 PERSONAL BASELINE
                         ↓
                    DEVIATIONS
                         ↓
                     EVENTS
                         ↓
                CLINICAL CONTEXT
                         ↓
                  REVIEW QUEUE
                         ↓
                     CLINICIAN
```

---

# 7. Common EVYZ Schema

Every source must be converted into one internal format.

Example:

```json
{
  "patient_id": "p_031",
  "timestamp": "2026-09-23T08:00:00Z",
  "metric": "resting_heart_rate",
  "value": 67,
  "unit": "bpm",
  "source": "oura",
  "device": "oura_ring",
  "context": "overnight"
}
```

EVYZ should preserve the source because measurements with similar names are not always calculated the same way by different companies.

Do not blindly merge provider-specific measurements into one number.

---

# 8. Data Quality Comes Before Alerts

Before EVYZ decides that something changed, it must check whether the measurement is usable.

Check for:

- missing values
- duplicate records
- impossible timestamps
- unit mismatches
- large gaps
- device changes
- timezone errors
- implausible measurements
- too little history

If there is not enough reliable data, EVYZ should say:

> **Insufficient data**

It should not invent a conclusion.

---

# 9. Personal Baseline

EVYZ should compare a patient with their own prior measurements.

For each signal, keep a recent history such as 14–30 days.

Initial calculations can use:

- rolling median
- median absolute deviation
- rolling percentiles
- recent trend
- day-to-day variability

Example:

```text
Patient 031

Resting HR recent range: 58–62 bpm
Current: 69 bpm

HRV recent range: 48–62 ms
Current: 37 ms
```

The system should know that 69 bpm may be normal for one person and unusual for another.

---

# 10. Deviation Detection

For each measurement, EVYZ calculates how far it moved from the patient’s recent range.

Start with transparent calculations.

Examples:

- percent change
- robust z-score
- percentile distance
- consecutive abnormal days
- slope over the last 3–7 days

Do not start with a large neural network.

A more complicated model should only be added if it catches useful events that simpler calculations miss.

---

# 11. Event Detection

EVYZ should not alert on every unusual measurement.

A useful event usually has one or more of these properties:

- more than one signal changed
- the change is large
- the change lasted more than one day
- related signals changed together
- symptoms changed during the same period
- the pattern occurred near a treatment or medication change

Example:

```text
EVYZ EVENT

Start: Sep 20
Duration: 4 days

Resting HR        +12%
HRV               -24%
Activity          -31%
Sleep             -17%
Fatigue report    increased

Treatment: 5 days earlier
```

An event is easier for a clinician to review than hundreds of individual measurements.

---

# 12. Explanation

Every event should answer four questions:

1. What changed?
2. When did it start?
3. How long has it lasted?
4. Why did EVYZ surface this patient?

Example:

> EVYZ surfaced this patient because resting heart rate remained above the recent personal range for three days while HRV and activity moved below their recent ranges. The patient also reported more fatigue during the same period.

The explanation should be generated from structured measurements.

If a language model is used, it should only turn the structured findings into readable text.

The language model should not decide that the patient has a disease.

---

# 13. Feedback Loop

The care team and patient should be able to label an event.

Patient labels may include:

```text
Sick
Poor sleep
Stress
Hard workout
Travel
Medication change
Treatment side effect
Nothing noticeable
Other
```

Clinician labels may include:

```text
Useful event
Not clinically important
Expected after treatment
Needs follow-up
Measurement problem
Unknown
```

This creates a record of:

```text
measurements
+
personal baseline
+
event
+
patient context
+
clinician judgment
```

That is much more useful than a collection of raw wearable measurements.

---

# 14. What EVYZ Should Build First

Do not start with every disease.

Do not start with every wearable.

Do not start with a hospital-wide dashboard.

Pick:

- one specialty
- one patient group
- one period between visits
- one reason a clinician would review a patient

The first vertical should have all of these:

1. Important changes happen outside the clinic.
2. Patients already generate useful measurements at home.
3. The specialist cannot review every patient manually.
4. A missed change can lead to an unnecessary visit, admission, treatment delay, or worse outcome.
5. The clinician can act on the information.

Candidate areas to validate first:

- oncology treatment monitoring
- autoimmune flare monitoring
- respiratory / home-therapy monitoring

**Leading hypothesis: cardiology.** Cardiac patients generate exactly the signals wearables measure best (resting heart rate, HRV, activity), and the founder’s ML research background is in cardiovascular disease, the credibility that opens doors to cardiologists. Validate it against the other candidates with real interviews. If the interviews point elsewhere, follow the interviews.

Do not build all three (or four).

Interview clinicians and choose one.

---

# 15. Current EVYZ Phase 0

Phase 0 is already built around real longitudinal wearable history.

Current flow:

```text
WearableQA
    ↓
daily history
    ↓
28-day personal baseline
    ↓
deviation detection
    ↓
persistent events
    ↓
multi-signal events
    ↓
plain-language explanation
```

Current Phase 0 facts:

- the local run uses WearableQA
- respiratory rate and skin temperature remain empty when the source file does not contain them
- missing HRV is left missing rather than filled in
- the earlier lab dataset is not part of Phase 0
- WearableQA is only bootstrap data and is not a commercial production data source

Phase 0 has already shown that the code can turn a real daily history into personal baselines and events.

Do not spend months polishing the same offline dataset.

---

# 16. Phase 1 — One Live Wearable

The next engineering milestone is one real user with one real wearable.

Use whichever source becomes available first.

Example:

```text
Oura user
   ↓
OAuth / API
   ↓
90 days of history
   ↓
EVYZ normalizer
   ↓
existing baseline engine
   ↓
events
   ↓
"Did this event match something real?"
```

The goal is not API coverage.

The goal is to find out whether a real person recognizes EVYZ events as meaningful.

---

# 17. Phase 2 — Add Symptoms and Treatment Context

Once one live wearable works, add:

- symptom check-in
- medication changes
- treatment dates
- relevant home-device data

Now EVYZ can show a richer event.

Instead of:

> HRV fell for three days.

EVYZ can show:

> HRV and activity fell for three days after treatment. The patient also reported more fatigue.

That is the beginning of the clinical product.

---

# 18. Phase 3 — One Specialist Workflow

Choose one specialty.

Build only what that specialist needs.

Example workflow:

```text
Clinic enrolls patient
        ↓
Patient connects wearable
        ↓
EVYZ imports history
        ↓
Baseline builds
        ↓
New event appears
        ↓
Patient adds context
        ↓
Clinician sees patient in review queue
        ↓
Clinician reviews source measurements
        ↓
Clinician decides what to do
```

The product is successful if it saves the clinician time or helps them notice a patient they would otherwise have missed.

---

# 19. Phase 4 — First 10–20 Patients

Do not measure success by app downloads.

Measure:

- how many patients connect successfully
- how many days of usable data arrive
- how many events EVYZ creates
- how many events patients recognize
- how many events clinicians consider worth reviewing
- false alarms per patient per week
- time from event start to clinician review
- how often the clinician opens the underlying data
- whether EVYZ changes any follow-up action

The most important early question is:

> **Does EVYZ surface a small number of events that a clinician considers useful?**

---

# 20. Business Model

The first business model should be B2B.

Possible buyers:

- specialty clinics
- hospital programs
- health systems
- value-based care groups

Possible pricing later:

- per monitored patient per month
- per treatment episode
- annual clinic contract

The pricing works because remote monitoring is reimbursable: Medicare’s RPM codes let clinics bill for monitoring patients between visits. That is a tailwind, not the product. It makes EVYZ a revenue line for the clinic rather than a cost center, which is why per-patient-per-month pricing is viable.

Do not build the company around reimbursement codes before the product is useful.

First prove that a clinic wants the information. Then, once a pilot clinic is live, the product must help the clinic collect: track transmission days per patient per month, log clinician review time, and export a billing report the biller can use. Verify current CMS thresholds before building this. They change by year.

---

# 21. Hardware Decision

Do not build EVYZ hardware because wearables are interesting.

Build hardware only when the software exposes a specific missing measurement.

Example:

> EVYZ needs signal X continuously at frequency Y, but existing devices do not measure it reliably or do not expose it through their APIs.

Then the sequence is:

```text
software in real users
       ↓
missing measurement discovered
       ↓
measurement requirement written
       ↓
sensor selected
       ↓
hardware prototype
```

This gives the hardware a reason to exist.

---

# 22. Technical Stack

Keep the first production stack small.

## Backend

```text
Python
FastAPI
Pydantic
PostgreSQL
```

## Analysis

```text
Python
NumPy
Pandas
SciPy
scikit-learn
```

## Mobile

```text
React Native
Expo
TypeScript
```

## Authentication

```text
Supabase Auth or another standard OAuth-capable provider
```

## Development

```text
GitHub
Cursor
coding agent
pytest
```

Do not add Kafka, Kubernetes, microservices, a vector database, or a large model unless the product creates a concrete need for them.

---

# 23. Repository Structure

```text
evyz/
│
├── apps/
│   ├── mobile/
│   └── api/
│
├── integrations/
│   ├── oura/
│   ├── whoop/
│   ├── fitbit/
│   └── healthkit/
│
├── core/
│   ├── normalization/
│   ├── quality/
│   ├── baseline/
│   ├── deviations/
│   ├── events/
│   └── explanations/
│
├── db/
│   ├── models/
│   └── migrations/
│
├── scripts/
│   ├── run_phase0.py
│   └── run_oura.py
│
├── tests/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── docs/
│   ├── architecture.md
│   ├── product.md
│   └── data-sources.md
│
├── .env.example
├── .gitignore
└── README.md
```

---

# 24. Security Rules

Health data should be treated as sensitive from day one.

Minimum rules:

- never commit API tokens
- keep secrets in environment variables
- request only the permissions needed
- keep an audit record of data imports
- make deletion possible
- separate source data from derived events
- encrypt data in transit
- use encrypted storage in production
- do not share user data without explicit permission
- do not use production user data as public demo data

---

# 25. First Product Milestones

## Milestone 1 — Done

```text
real public longitudinal history
→ personal baseline
→ deviations
→ events
→ explanation
```

## Milestone 2

```text
one live wearable user
→ historical import
→ same EVYZ pipeline
```

## Milestone 3

```text
live user
→ EVYZ event
→ user labels what happened
```

## Milestone 4

```text
symptoms + treatment context
→ richer event
```

## Milestone 5

```text
one specialist
→ reviews real patient events
```

## Milestone 6

```text
10–20 patients
→ measure useful events and false alarms
```

Do not jump from Milestone 1 to building custom hardware.

---

# 26. What to Do Next

The next three tasks are:

1. Get one real wearable user.
2. Run that person’s history through the existing EVYZ pipeline.
3. Ask whether the detected events correspond to anything that actually happened.

In parallel, talk to specialists in one candidate area and ask:

> What important changes happen to your patients between visits that you usually learn about too late?

The answer should determine the first clinical vertical.

---

# 27. EVYZ in Two Sentences

> **EVYZ flags patients getting worse between visits.** It builds a personal baseline for each patient from the wearables they already own, and gives the care team a short daily review queue of patients who changed. No alert fatigue, no waiting for the next appointment.

---

# 28. YC-Style Pitch

**What are you building?**

> EVYZ flags patients getting worse between visits. It connects to the wearables patients already own, builds a personal baseline for each patient, and gives the care team a short daily review queue: which patients changed, what changed, and why.

**What does the product do today?**

> The current system takes a longitudinal wearable history, builds a 28-day baseline for each person, finds sustained single- and multi-signal changes, groups them into events, and explains which measurements moved and by how much.

**Why won’t clinicians ignore this like every other RPM alert?**

> Existing tools compare patients to population averages, so they cry wolf and doctors tune them out. EVYZ compares each patient to themselves. A resting heart rate of 69 is normal for most people, a red flag for the patient whose baseline is 58-62.

**Who pays?**

> Specialist clinics, per monitored patient per month. Remote monitoring is reimbursable under Medicare’s RPM codes, so EVYZ is a revenue line for the clinic, not a cost center.

**Why is this not WHOOP, Oura, or Fitbit?**

> Those products are built for the individual wearing the device. EVYZ uses the measurements in the context of a disease, treatment, or home-care plan and helps a clinical team decide which patients to review.

**Why not diagnose the patient automatically?**

> The first product does not need to. It needs to reliably show what changed, when it changed, how long it lasted, and the measurements behind the event. The clinician interprets; EVYZ shows evidence.

**Why not build hardware now?**

> Existing devices already produce useful measurements. EVYZ will build hardware only if live users show that an important signal is missing or unavailable through existing devices.

---

# 29. The Core Rule

Do not ask:

> What AI model should EVYZ use?

Do not ask:

> What bracelet should EVYZ build?

Ask:

> **What change in a patient’s condition or treatment can EVYZ show a clinician earlier or more clearly than the clinic can see today?**

Then build only what is required to answer that question.

---

# 30. Evidence Base: What Has Already Been Shown

These references do **not** prove that EVYZ itself works. They support specific parts of the product thesis: personal baselines, longitudinal wearable monitoring, treatment-linked changes, and clinician review of patients outside the hospital.

## A. Personal baselines and deterioration detection

### Personalized anomaly detection for deterioration at home — 2026

**Paper:** *Detecting early signs of patient deterioration at home using wearable sensors: a personalized anomaly detection approach*

- PubMed: https://pubmed.ncbi.nlm.nih.gov/41871459/
- DOI: https://doi.org/10.1088/2057-1976/ae55a9

Why it matters to EVYZ:

- The study treats deterioration as an anomaly-detection problem because serious events are relatively rare.
- It continuously updates models for the individual instead of assuming one fixed population threshold fits everyone.
- It evaluates wearable data against concrete outcomes such as mortality or unplanned readmission.

**EVYZ implication:** the personal-baseline architecture is a reasonable starting point for home monitoring, but EVYZ still has to prove useful alert rates in its own target population.

### Early adverse-event detection from commercial wearables — 2024

**Paper:** *Early adverse physiological event detection using commercial wearables: challenges and opportunities*

- PubMed: https://pubmed.ncbi.nlm.nih.gov/38783001/

Why it matters:

- The work used data from more than 8,000 participants and more than 1.3 million hours of Oura data.
- It identifies four problems EVYZ must handle: differences between people, confounders, sensor noise, and imperfect self-reported labels.
- Individual baseline correction improved pre-symptomatic event-detection performance in the study.

**EVYZ implication:** normalization and data quality are not optional infrastructure. They are part of the product.

### Baseline leakage warning — 2026

**Paper:** *Baseline normalization choices inflate classification performance in wearable health monitoring: quantification and mitigation strategies*

- PubMed: https://pubmed.ncbi.nlm.nih.gov/42682689/

Why it matters:

- The paper shows that wearable-model results can look materially better when the evaluation period leaks into the period used to calculate the baseline.

**EVYZ engineering rule:** a day's measurement must never help construct the historical baseline against which that same day is evaluated. Keep baseline windows strictly prior to the event window.

---

# 31. Evidence for Candidate Clinical Verticals

## A. Oncology

### Lung-cancer treatment: real wearable + clinical dataset — 2026

**Paper:** *A real-world Fitbit-derived dataset of activity, sleep, and heart rate with matched clinical factors in on-treatment lung cancer patients*

- Paper: https://doi.org/10.1038/s41597-026-07762-7
- PubMed: https://pubmed.ncbi.nlm.nih.gov/42380636/
- Dataset: https://zenodo.org/records/20780805

What is in it:

- 178 lung-cancer patients receiving anti-cancer treatment
- Fitbit activity, sleep, and heart-rate data
- treatment regimen and clinical variables
- performance-status scores
- emergency-department visits
- 15,175 patient-days, with 12,409 meeting the paper's 80% wear-adherence threshold

Why it matters to EVYZ:

This is much closer to the eventual EVYZ product than a generic wellness dataset because wearable measurements are tied to **active treatment and clinical outcomes**.

**Best use:** if EVYZ chooses oncology first, this should be one of the first datasets evaluated after the current WearableQA bootstrap. The dataset is publicly downloadable; review the repository's current terms before any commercial use.

### Chemotherapy symptoms and wearable changes — 2026

**Study:** TRACK-BC, *Wearable-derived physical activity monitoring with AI-based detection of treatment-related adverse events during neoadjuvant chemotherapy for early breast cancer*

- Journal of Clinical Oncology abstract: https://doi.org/10.1200/JCO.2026.44.16_suppl.1631

What was reported:

- 101 patients undergoing neoadjuvant chemotherapy
- Fitbit activity, heart rate, sleep, and patient-reported symptoms
- physical activity declined during treatment
- fatigue, insomnia, appetite loss, and neuropathy worsened and broadly tracked wearable changes

**Evidence level:** prospective multicenter study reported as an ASCO/JCO meeting abstract, not a full clinical-validation paper.

**EVYZ implication:** treatment timing + wearable changes + patient-reported symptoms is a concrete data model worth testing.

### CAR-T toxicity: early detection with continuous wearables — 2026

**Paper:** *Detection of cytokine release syndrome using wearables and cytokine profiling following CAR-T therapy for myeloma*

- JCI Insight / PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC13313484/
- DOI: https://doi.org/10.1172/jci.insight.203988

What was reported:

- prospective pilot involving 30 CAR-T patients; 25 had sufficient data for evaluation
- continuous temperature, oxygen saturation, respiratory rate, heart rate, and motion
- the best wearable model detected 18 of 20 cytokine-release-syndrome episodes
- median detection lead time was about 7 hours before standard nursing recognition

**EVYZ implication:** there are high-value treatment windows where continuous measurements can help a clinical team see a meaningful change earlier. This is a strong example of the kind of workflow EVYZ should look for, but the study is small and needs larger validation.

---

## B. Autoimmune / Rheumatology

### Rheumatoid-arthritis flares — 2025/2026

**Paper:** *Wearable devices detect physiological changes that precede and are associated with symptomatic and inflammatory rheumatoid arthritis flares*

- Scientific Reports: https://www.nature.com/articles/s41598-025-29748-y
- PubMed: https://pubmed.ncbi.nlm.nih.gov/41318620/

What was reported:

- 53 people with rheumatoid arthritis
- Apple Watch, Fitbit, or Oura Ring
- heart rate, resting heart rate, HRV, steps, daily symptom surveys, and inflammatory assessments
- several wearable measurements differed between flare and remission periods
- some changes were detectable up to four weeks before flare onset

**EVYZ implication:** this directly supports the idea of combining longitudinal wearable data with symptom and disease context rather than showing generic recovery scores.

---

## C. Respiratory / Home Therapy

### COPD remote monitoring — 2026 systematic review

**Paper:** *AI and Internet of Things for Chronic Obstructive Pulmonary Disease Remote Monitoring: Systematic Review of Exacerbation Prediction and Key Physiological Variables*

- PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC13148758/
- DOI: https://doi.org/10.2196/84814

Why it matters:

The review maps the physiological and environmental variables used in COPD remote monitoring and also highlights weaknesses in current work, including limited external validation and difficulty translating models into realistic home monitoring.

**EVYZ implication:** respiratory monitoring is plausible, but EVYZ should not begin by claiming to predict exacerbations. Start with transparent change detection and clinician review.

### Home oxygen reassessment gap

**Paper:** *Reassessment of Home Oxygen Prescription after Hospitalization for Chronic Obstructive Pulmonary Disease*

- PMC: https://pmc.ncbi.nlm.nih.gov/articles/PMC7919159/

What was reported:

- only 43.6% of 659 patients discharged on home oxygen received complete reassessment within 90 days
- among patients completely reassessed, 43.2% met the study's Medicare-based criteria suggesting oxygen could potentially be discontinued

**EVYZ implication:** one potential product opportunity is not "predict COPD." It is helping care teams see which home-therapy patients need reassessment and why.

---

# 32. Datasets Worth Keeping

Do not download every dataset. Keep this list as a map and use a dataset only when it answers a product question.

## 1. WearableQA — current Phase 0 bootstrap

- Dataset: https://huggingface.co/datasets/facebook/WearableQA
- Code: https://github.com/facebookresearch/WearableQA
- Paper: https://arxiv.org/abs/2609.05405

Contains longitudinal wearable histories for 200 people, with up to about 500 days per person, plus wearable metrics, blood biomarkers, and demographics.

**EVYZ use:** test the generic baseline/event pipeline.

**Restriction:** CC BY-NC 4.0. Do not use it as EVYZ production/commercial data.

## 2. PULSE — strongest current dataset if EVYZ explores oncology

- Dataset: https://zenodo.org/records/20780805
- Paper: https://doi.org/10.1038/s41597-026-07762-7

Contains real Fitbit histories from 178 lung-cancer patients during treatment, plus treatment and clinical variables including emergency-department visits.

**EVYZ use:** test whether the same event pipeline becomes more meaningful when treatment and clinical outcomes are available.

## 3. CovIdentify — strong symptom-linked longitudinal wearable data

- PhysioNet: https://physionet.org/content/covidentify/1.0.0/
- DOI: https://doi.org/10.13026/ncq1-vp79

Includes 2,887 participants who connected Garmin, Fitbit, or Apple wearable data, plus daily symptom surveys and diagnostic-testing information.

**EVYZ use:** test wearable deviations against reported symptoms and known events across device brands.

**Access:** PhysioNet credentialed access and a data-use agreement are required.

## 4. OpenOximetry — useful if EVYZ builds around oxygenation or respiratory sensing

- PhysioNet: https://physionet.org/content/openox-repo/1.1.1/
- Dataset paper DOI: https://doi.org/10.1038/s41597-025-04870-8

Contains pulse-oximetry performance data, matched oxygen-saturation references, physiological metadata, and in some studies raw PPG and related signals.

**EVYZ use:** sensor/measurement validation if oxygen saturation becomes part of a regulated respiratory product.

**Access:** restricted PhysioNet access. This is not a longitudinal home-monitoring dataset.

## 5. BIDMC PPG and Respiration — useful for signal engineering, not the first product

- PhysioNet: https://physionet.org/content/bidmc/1.0.0/

Contains 53 short clinical recordings with PPG, ECG, respiratory signals, heart rate, respiratory rate, SpO2, and manually annotated breaths.

**EVYZ use:** only if the company later needs to estimate respiratory measures from raw PPG or builds its own sensor hardware.

Do not substitute this dataset for real longitudinal patient monitoring.

---

# 33. Regulatory References to Keep Beside the Code

These are not papers, but they matter if EVYZ moves from showing measurements to making clinical claims.

## FDA Clinical Decision Support Software Guidance — January 2026

- https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software

Use this when deciding whether an EVYZ feature is simply presenting transparent information for a clinician to independently review or is becoming a regulated medical-device function.

## FDA Sensor-Based Digital Health Technology Device List

- https://www.fda.gov/medical-devices/digital-health-center-excellence/medical-devices-incorporate-sensor-based-digital-health-technology

This is a practical map of FDA-authorized wearable and home-monitoring devices. Use it to inspect predicates, product codes, intended uses, and regulatory submissions before designing EVYZ hardware.

## FDA AI-Enabled Medical Device List

- https://www.fda.gov/medical-devices/software-medical-device-samd/artificial-intelligence-enabled-medical-devices

Use this to see what kinds of AI-enabled medical claims have already reached the U.S. market and how those products are described.

---

# 34. What the Evidence Does and Does Not Prove

The evidence above supports these statements:

1. Consumer and medical wearables can capture longitudinal physiological changes associated with real clinical states in some populations.
2. Personal baselines can be useful because physiology differs substantially between individuals.
3. Treatment timing, symptoms, and clinical context can make wearable changes more interpretable.
4. Continuous monitoring can sometimes identify clinically relevant changes earlier than intermittent observation.
5. False alarms, missing data, confounding, device differences, and weak external validation remain major problems.

The evidence does **not** prove:

- that the current EVYZ event threshold is clinically valid
- that a generic EVYZ event predicts deterioration
- that one algorithm will work across diseases
- that consumer wearable measurements can replace medical devices
- that a clinician should change treatment because EVYZ generated an event

EVYZ must validate each clinical workflow with the target users and the target patient population.

---

# 35. Most Useful Next Evidence Step

If EVYZ remains broad for another short period, keep WearableQA only as a software bootstrap.

If oncology becomes the first vertical, use the **PULSE lung-cancer dataset** next because it connects real wearable histories to active cancer treatment, performance status, and emergency-department visits.

The next technical question would then be:

> **Can the existing EVYZ baseline/event engine identify periods that line up with clinically meaningful changes in on-treatment patients without creating an unusable number of alerts?**

That is a more useful question than adding another wearable API before the first clinical workflow is chosen.
