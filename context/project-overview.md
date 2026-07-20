# Finance Tracker

## Overview

Finance Tracker is a multi-user web app that turns raw income and expense
records into insight, answering one question for each user: "Where is my
money actually going, and is that changing over time?" It is built as a
portfolio piece for the Stockholm fintech market (Klarna, Tink, Trustly,
and the wider payments/lending scene). The point is not "store
transactions" — it is "turn raw transactions into insight," with trend
charts, category breakdowns, AI-assisted categorization, and (as a stretch)
real Open Banking / PSD2 data.

## Goals

1. Let a signed-in user record, edit, and delete income and expense
   transactions that persist reliably in Postgres.
2. Turn those transactions into insight — category breakdowns, spending
   over time, and month-vs-last-month summaries — visible at a glance on a
   dashboard.
3. Ship a polished, deployed, multi-user app with one clickable demo URL
   and a README that makes the project look employable.

## Core User Flow

1. User signs up / logs in via Supabase Auth.
2. User records a transaction (amount, type, date, description, category).
3. FastAPI validates the input and stores it in Postgres, scoped to that
   user.
4. User assigns or edits the transaction's category — manually, or via
   auto-categorization once Phase 4 lands.
5. User opens the dashboard and sees spending by category, spending over
   time, and a period summary (income, expense, net).
6. User filters and explores transactions by date range, type, category,
   and account.

## Features

### Transaction Management (Phase 1)

- Create, view, edit, and delete transactions.
- Each transaction has an amount, type (income/expense), date,
  description, and optional category and account.
- Money stored as `numeric`, never float — amount positive, `type` gives
  direction.

### Categories & Accounts (Phase 2)

- User-managed categories: seeded global defaults plus custom ones.
- Optional accounts (checking / savings / cash).
- Filter the transaction list by date range, type, category, and account.

### Insight Layer / Dashboard (Phase 3)

- Summary cards: income, expense, and net for the selected period.
- Donut: expense share by category.
- Line/bar: income vs. expense over time.
- Period selector (this month / last month / custom) driving all views.

### Smart Categorization (Phase 4)

- Rule-based pass first (keyword → category), LLM fallback for the rest.
- "Auto" badge on auto-categorized transactions; user can always override.
- User-managed rules manager (keyword → category).
- Categorization runs as a background task so creating a transaction stays
  fast.

### Auth & Deployment (Phase 5)

- Multi-user auth via Supabase (email/password or magic link).
- Deployed with a single clickable live-demo URL.

### Bank Import — Stretch (Phase 6)

- Import real transactions via an Open Banking / PSD2 aggregator (e.g.
  Tink) sandbox.
- OAuth flow, duplicate-safe import, optional auto-categorization on
  import.

## Scope

### In Scope

- Full transaction CRUD with validation and per-user scoping.
- User-managed categories and optional accounts, with list filtering.
- Aggregation dashboard (summary, by-category, over-time).
- Rule-based + LLM-assisted categorization as a background task.
- Supabase Auth, deployment, tests, CI, and a strong README.

### Out of Scope

- Building our own auth / user table — Supabase Auth owns `auth.users`.
- Production Open Banking access — sandbox / mock only for the portfolio
  piece.
- A separate job queue (Celery/Redis) — FastAPI background tasks are
  enough to start.
- Storing large binary/blob content — this is a relational, metadata-only
  app.
- Native mobile apps.

## Success Criteria

1. A signed-in user can add, edit, list, and delete transactions through
   the UI, each with a category, persisted in Postgres, with passing tests
   in CI.
2. Opening the app shows a dashboard that tells the money story at a glance
   for a chosen period.
3. A new transaction with a recognizable description gets a sensible
   category automatically, and the user can define rules and override
   results.
4. A stranger can click a link, sign up, use the app end to end, and read
   a README that makes the project look employable.
