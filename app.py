"""Vireo Audio - SLA breach report. Run with:  streamlit run app.py"""
import pandas as pd
import streamlit as st

from src.loader import load_uploaded, load_from_folder, missing_required
from src.cleaning import clean_tickets, clean_agents
from src import metrics as m
from src.config import SLA_TARGET_MIN, BREACH_CREDIT_INR

st.set_page_config(page_title="Vireo SLA Breach Report", layout="wide")
st.title("Vireo Audio - SLA Breach Report")

# ---------------------------------------------------------------- 1. Load data
st.sidebar.header("1. Upload data")
files = st.sidebar.file_uploader("Upload the CSV files (tickets.csv and agents.csv are required)",
                                 type="csv", accept_multiple_files=True)
data = load_uploaded(files) if files else load_from_folder("data")
if not files and data:
    st.sidebar.info("No upload - using CSVs found in the data/ folder.")

missing = missing_required(data)
if missing:
    st.info("Upload at least **tickets.csv** and **agents.csv** in the sidebar to begin.\n\n"
            f"Still missing: {', '.join(missing)}")
    st.stop()

# ------------------------------------------------------- 2. Clean + calculate
tickets, notes = clean_tickets(data["tickets"])
agents = clean_agents(data["agents"])
tickets = m.add_sla_columns(tickets)

# ---------------------------------------------------------------- 3. Filters
st.sidebar.header("2. Filters")
channels = st.sidebar.multiselect("Channel", sorted(tickets["channel"].unique()),
                                  default=sorted(tickets["channel"].unique()))
teams = st.sidebar.multiselect("Assigned team", sorted(tickets["assigned_team"].unique()),
                               default=sorted(tickets["assigned_team"].unique()))
dmin, dmax = tickets["created_date"].min().date(), tickets["created_date"].max().date()
dates = st.sidebar.date_input("Created between (IST)", (dmin, dmax), min_value=dmin, max_value=dmax)
if len(dates) != 2:
    st.warning("Pick both a start and an end date.")
    st.stop()

view = tickets[tickets["channel"].isin(channels) & tickets["assigned_team"].isin(teams)
               & (tickets["created_date"].dt.date >= dates[0])
               & (tickets["created_date"].dt.date <= dates[1])]
if view.empty:
    st.warning("No tickets match these filters.")
    st.stop()

st.caption("Targets used: " + ", ".join(f"{k} {v} min" for k, v in SLA_TARGET_MIN.items())
           + f" | Credit per breach: Rs {BREACH_CREDIT_INR} | All times converted UTC to IST")

tab_impact, tab_week, tab_shift, tab_agent, tab_dq = st.tabs(
    ["Business impact", "Weekly report", "Shift report", "Agent report", "Data quality"])

# ------------------------------------------------------------ Business impact
with tab_impact:
    b = m.business_impact(view)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tickets", f"{b['tickets']:,}")
    c2.metric("SLA breaches", f"{b['breaches']:,}", f"{b['breach_rate']:.1f}% of tickets", delta_color="off")
    c3.metric("Breach credits issued", f"Rs {b['credit_total']:,}")
    c4.metric("Avg credits / month", f"Rs {b['credit_per_month_avg']:,.0f}")

    st.subheader("Credit cost per month (Rs)")
    st.bar_chart(b["credit_by_month"])

    st.subheader("Where do the breaches start?")
    c1, c2 = st.columns(2)
    c1.metric("Breaches on tickets created overnight (22:00-06:00 IST)", f"{b['night_breach_share']:.0f}%")
    c2.metric("Breaches on tickets created in the Morning shift", f"{b['morning_breach_share']:.0f}%")
    st.write(f"Overnight **chat** tickets breached **{b['night_chat_rate_before']:.1f}%** of the time up to "
             f"29 Jun 2025 (Indore night shift) and **{b['night_chat_rate_after']:.1f}%** after it. "
             "Nobody is staffed to answer them until the morning shift starts.")
    st.write(f"Transfer handling cost in this view: **Rs {b['transfer_cost']:,}** "
             "(Rs 305 per hand-off, policy section 4).")
    st.caption("Credits are counted only for resolved/closed tickets (policy section 3: issued on resolution).")

# ---------------------------------------------------------------- Weekly
with tab_week:
    st.subheader("Weekly breach report (weeks start Monday, IST)")
    wk = m.weekly_report(view)
    st.line_chart(wk.set_index("week_start")["breach_rate_%"])
    st.subheader("Breaches per week by the shift the ticket was created in")
    st.bar_chart(m.weekly_by_shift(view))
    st.dataframe(wk, hide_index=True)
    st.download_button("Download weekly report (CSV)", wk.to_csv(index=False), "weekly_breach_report.csv")

# ---------------------------------------------------------------- Shift
with tab_shift:
    st.subheader("Breaches by shift in which the ticket was created")
    st.caption("Shows which shift the customer reached, not who eventually answered. "
               "Night = 22:00-06:00 IST.")
    sh = m.shift_report(view)
    st.dataframe(sh, hide_index=True)
    st.bar_chart(sh.set_index("shift_created_in")["breach_rate_%"])
    st.subheader("Breach rate % by shift and channel")
    st.dataframe(m.shift_by_channel(view))
    st.download_button("Download shift report (CSV)", sh.to_csv(index=False), "shift_breach_report.csv")

# ---------------------------------------------------------------- Agent
with tab_agent:
    st.subheader("Breaches by resolving agent")
    st.warning("Read with care: this counts the agent who **resolved** the ticket, which may not be the "
               "one who was late. Use the overnight_created_% column - many breaches on morning agents "
               "are tickets that arrived overnight and were already late when the shift started. "
               "Tier 2 agents work multi-touch cases and should not be compared with Tier 1 on volume.")
    ag = m.agent_report(view, agents)
    min_t = st.slider("Hide agents with fewer than N tickets", 0, 100, 20)
    ag = ag[ag["tickets"] >= min_t]
    st.dataframe(ag, hide_index=True)
    st.download_button("Download agent report (CSV)", ag.to_csv(index=False), "agent_breach_report.csv")

# ---------------------------------------------------------------- Data quality
with tab_dq:
    st.subheader("What was cleaned")
    st.write(f"- Rows read: **{notes['rows_in']:,}**\n"
             f"- Duplicate tickets removed (helpdesk + legacy copies): **{notes['duplicates_removed']:,}**\n"
             f"- Legacy CSAT of 0 turned into blank: **{notes['legacy_csat_zero_fixed']:,}**\n"
             f"- Rows without usable timestamps dropped: **{notes['rows_without_timestamps']:,}**\n"
             f"- Rows used: **{notes['rows_out']:,}**")
    st.write("Timestamps were exported in UTC and are shown in IST (+5:30).")