"""Clean the tickets and agents tables (see support policy section 8 and 9)."""
import pandas as pd
from src.config import IST_OFFSET


def clean_tickets(raw):
    """Returns (clean_df, notes) where notes is a dict of what was fixed."""
    df = raw.copy()
    notes = {"rows_in": len(df)}

    # 1. Parse timestamps (export is UTC) and convert to IST
    for col in ["created_at", "first_response_at", "resolved_at"]:
        df[col] = pd.to_datetime(df[col], errors="coerce") + IST_OFFSET

    # 2. Remove duplicates from the Freshdesk re-import; keep the helpdesk copy
    df["_prio"] = (df["source_system"] != "helpdesk").astype(int)
    df = df.sort_values(["ticket_id", "_prio"])
    notes["duplicates_removed"] = int(df.duplicated("ticket_id").sum())
    df = df.drop_duplicates("ticket_id", keep="first").drop(columns="_prio")

    # 3. Legacy CSAT uses 0 for "no response"; blank must not count as zero
    notes["legacy_csat_zero_fixed"] = int((df["csat_score"] == 0).sum())
    df.loc[df["csat_score"] == 0, "csat_score"] = pd.NA

    # 4. Rows we cannot measure
    bad = df["created_at"].isna() | df["first_response_at"].isna()
    notes["rows_without_timestamps"] = int(bad.sum())
    df = df[~bad]

    notes["rows_out"] = len(df)
    return df.reset_index(drop=True), notes


def clean_agents(raw):
    df = raw.copy()
    df["from_date"] = pd.to_datetime(df["from_date"], errors="coerce")
    df["to_date"] = pd.to_datetime(df["to_date"], errors="coerce")  # blank = current
    return df