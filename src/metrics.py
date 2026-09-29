"""SLA breach calculations and report tables."""
import pandas as pd
from src.config import (SLA_TARGET_MIN, BREACH_CREDIT_INR, TRANSFER_COST_INR,
                        RESOLVED_STATUSES, SHIFT_ORDER, NIGHT_SHIFT_END)


def shift_for_hour(hour):
    """Which IST shift a given hour falls into (policy section 7)."""
    if 6 <= hour < 14:
        return "Morning"
    if 14 <= hour < 22:
        return "Day"
    return "Night"


def add_sla_columns(df):
    """Adds response time, breach flag, creation shift, week and credit cost."""
    df = df.copy()
    df["response_min"] = (df["first_response_at"] - df["created_at"]).dt.total_seconds() / 60
    df["target_min"] = df["channel"].map(SLA_TARGET_MIN)
    df["breached"] = df["response_min"] > df["target_min"]
    df["created_shift"] = df["created_at"].dt.hour.map(shift_for_hour)
    df["created_date"] = df["created_at"].dt.normalize()
    df["week_start"] = df["created_date"] - pd.to_timedelta(df["created_at"].dt.weekday, unit="D")
    df["month"] = df["created_at"].dt.to_period("M").astype(str)
    # Credit is issued on resolution, so only resolved/closed breaches cost money
    df["credit_inr"] = (df["breached"] & df["status"].isin(RESOLVED_STATUSES)) * BREACH_CREDIT_INR
    return df


def _summarise(g):
    return pd.Series({
        "tickets": len(g),
        "breaches": int(g["breached"].sum()),
        "breach_rate_%": round(100 * g["breached"].mean(), 1),
        "credit_cost_inr": int(g["credit_inr"].sum()),
    })


def _ints(out):
    for c in ["tickets", "breaches", "credit_cost_inr"]:
        out[c] = out[c].astype(int)
    return out


def weekly_report(df):
    out = _ints(df.groupby("week_start").apply(_summarise, include_groups=False).reset_index())
    out["week_start"] = out["week_start"].dt.date
    return out


def weekly_by_shift(df):
    """Weekly breach counts with one column per creation shift (for the chart)."""
    p = df.pivot_table(index="week_start", columns="created_shift", values="breached",
                       aggfunc="sum", fill_value=0)
    return p.reindex(columns=[s for s in SHIFT_ORDER if s in p.columns])


def shift_report(df):
    """Breaches by the shift in which the ticket was CREATED (i.e. which shift the customer hit)."""
    out = df.groupby("created_shift").apply(_summarise, include_groups=False)
    out = _ints(out.reindex([s for s in SHIFT_ORDER if s in out.index]).reset_index())
    out["share_of_all_breaches_%"] = round(100 * out["breaches"] / out["breaches"].sum(), 1)
    return out.rename(columns={"created_shift": "shift_created_in"})


def shift_by_channel(df):
    p = df.pivot_table(index="created_shift", columns="channel", values="breached",
                       aggfunc="mean").mul(100).round(1)
    return p.reindex([s for s in SHIFT_ORDER if s in p.index])


def _attach_roster(df, agents):
    """Find the roster row that was active for the resolving agent on the ticket date."""
    m = df[["ticket_id", "agent_id", "created_date"]].merge(agents, on="agent_id", how="left")
    ok = (m["created_date"] >= m["from_date"]) & (m["to_date"].isna() | (m["created_date"] <= m["to_date"]))
    m = m[ok].drop_duplicates("ticket_id")
    return df.merge(m[["ticket_id", "name", "site", "team", "shift", "tier"]], on="ticket_id", how="left")


def agent_report(df, agents):
    d = _attach_roster(df, agents)
    d["created_overnight"] = d["created_shift"] == "Night"
    g = d.groupby(["agent_id", "name", "team", "shift", "tier"], dropna=False)
    out = g.agg(tickets=("ticket_id", "count"),
                breaches=("breached", "sum"),
                overnight_created_share=("created_overnight", "mean"),
                credit_cost_inr=("credit_inr", "sum")).reset_index()
    out["breach_rate_%"] = (100 * out["breaches"] / out["tickets"]).round(1)
    out["overnight_created_share"] = (100 * out["overnight_created_share"]).round(1)
    out = out.rename(columns={"shift": "shift_on_roster", "overnight_created_share": "overnight_created_%"})
    return out.sort_values("breaches", ascending=False)


def business_impact(df):
    """Headline numbers for the finance / ops conversation."""
    resolved_breach = df[df["breached"] & df["status"].isin(RESOLVED_STATUSES)]
    months = df.groupby("month")["credit_inr"].sum()
    night_chat = df[(df["channel"] == "chat") & (df["created_shift"] == "Night")]
    before = night_chat[night_chat["created_date"] <= NIGHT_SHIFT_END]
    after = night_chat[night_chat["created_date"] > NIGHT_SHIFT_END]
    return {
        "tickets": len(df),
        "breaches": int(df["breached"].sum()),
        "breach_rate": 100 * df["breached"].mean(),
        "credit_total": int(df["credit_inr"].sum()),
        "credit_per_month_avg": float(months.mean()) if len(months) else 0,
        "credit_by_month": months,
        "night_breach_share": 100 * df.loc[df["breached"], "created_shift"].eq("Night").mean(),
        "morning_breach_share": 100 * df.loc[df["breached"], "created_shift"].eq("Morning").mean(),
        "night_chat_rate_before": 100 * before["breached"].mean() if len(before) else float("nan"),
        "night_chat_rate_after": 100 * after["breached"].mean() if len(after) else float("nan"),
        "transfer_cost": int(df["transfers"].sum() * TRANSFER_COST_INR),
        "n_resolved_breaches": len(resolved_breach),
    }