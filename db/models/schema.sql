-- Phase-0 data model. Not deployed yet.
-- max_robust_z is an internal magnitude. It is not a user-facing score.

create table users (
    id text primary key,
    created_at timestamptz not null default now()
);

create table wearable_connections (
    id text primary key,
    user_id text not null references users (id),
    provider text not null,
    created_at timestamptz not null default now()
);

create table daily_metrics (
    id text primary key,
    user_id text not null references users (id),
    date date not null,
    resting_hr double precision,
    hrv double precision,
    sleep_minutes double precision,
    steps double precision,
    respiratory_rate double precision,
    temperature_delta double precision,
    source text not null,
    quality_status text not null,
    unique (user_id, date, source)
);

create table daily_events (
    id text primary key,
    user_id text not null references users (id),
    start_date date not null,
    end_date date not null,
    status text not null,
    changed_metrics text not null,
    max_robust_z double precision,
    explanation text not null
);

create table user_feedback (
    id text primary key,
    user_id text not null references users (id),
    event_id text not null references daily_events (id),
    label text not null check (
        label in (
            'sick',
            'poor_sleep',
            'stress',
            'hard_workout',
            'travel',
            'medication_change',
            'treatment_side_effect',
            'nothing_noticeable',
            'other'
        )
    ),
    notes text,
    created_at timestamptz not null default now()
);
