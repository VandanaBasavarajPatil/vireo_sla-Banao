"""Constants taken from the Vireo support policy (v3.2)."""
import pandas as pd

# Section 9: helpdesk API exports UTC; policy shifts are IST
IST_OFFSET = pd.Timedelta(hours=5, minutes=30)

# Section 3: first-response targets, in minutes
SLA_TARGET_MIN = {"chat": 15, "voice": 120, "social": 240, "email": 480}

# Section 3: credit issued for every breached ticket, on resolution
BREACH_CREDIT_INR = 350

# Section 4: cost standards
TRANSFER_COST_INR = 305
AGENT_COST_PER_HOUR_INR = 165
SHIFT_HOURS = 8

# Section 7: shifts in IST (start hour inclusive, end hour exclusive)
SHIFT_ORDER = ["Morning", "Day", "Night"]

# Statuses where the credit has actually been issued (section 3: "on resolution")
RESOLVED_STATUSES = ["resolved", "closed"]

# Indore night shift was dissolved on this date (see agents.csv)
NIGHT_SHIFT_END = pd.Timestamp("2025-06-29")
