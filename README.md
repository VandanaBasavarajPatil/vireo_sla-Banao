# Vireo Audio: SLA Breach Report

A local Streamlit app that reports first-response SLA breaches by week, shift and agent, and the credit cost they create.

## Run it
```
pip install -r requirements.txt
streamlit run app.py
```
Open http://localhost:8501 and upload `tickets.csv` and `agents.csv` in the sidebar (or copy the CSVs into `data/`). The data is not included in this repo.

## How a breach is calculated
1. Remove duplicate tickets from the Freshdesk re-import (keep the helpdesk copy).
2. Convert timestamps from UTC to IST (+5:30).
3. Response time = `first_response_at` - `created_at`.
4. Breach if response time is over the channel target: chat 15 min, voice 2 h, social 4 h, email 8 h.
5. Shift = the IST shift in which the ticket was **created** (Morning 06-14, Day 14-22, Night 22-06).
6. Credit = Rs 350 per breached ticket that is resolved or closed (policy s.3: issued on resolution).
7. Legacy CSAT of 0 is treated as no response.

## What the data shows (Jan 2025 - Jun 2026, 11,200 tickets)
- 2,440 breaches (21.8%), Rs 8.12 lakh in credits.
- Credits were about Rs 7k-14k a month until June 2025 and about Rs 60k-70k a month since August 2025.
- Overnight chat tickets breached about 7.8% of the time before the Indore night shift was dissolved (29 Jun 2025) and about 99.9% after.
- 67% of all breaches are on tickets created 22:00-06:00 IST; 16% on tickets created in the Morning shift.
- The Morning team shows many breaches because they resolve tickets that arrived overnight and were already late. Among the top agents by breaches, 36-41% of the tickets they resolved were created overnight.

**Implication:** this looks like a coverage gap, not an individual-performance problem. Use the agent report with the `overnight_created_%` column and do not rank people by it. Headcount is frozen, so the options to examine are re-timing existing shifts or moving a small chat team back onto nights.

## Assumptions and limits
- `agent_id` is the resolving agent, not necessarily the one who replied first; the data has no first-responder field.
- Open and pending tickets count as breaches if their first response was late, but no credit is counted until they resolve.
- Weeks start Monday (IST). Roster dates are treated as inclusive.
- Tier 2 agents are flagged, not excluded; the policy says not to compare them with Tier 1 on volume.
- Refunds, orders, products and customers are not used. Legacy refund units were not checked or converted.

## Structure
```
app.py            Streamlit UI (upload, filters, tabs)
src/config.py     policy constants
src/loader.py     reads uploaded or local CSVs
src/cleaning.py   dedupe, UTC->IST, CSAT fix
src/metrics.py    breach flags and report tables
```