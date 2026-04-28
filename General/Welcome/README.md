# Welcome System

Gates server access behind a Terms & Conditions DM, assigns the member role on acceptance, posts a welcome shoutout, and logs new-member chat activity to #bot-logs on a configurable interval.

## Commands
- `/set_welcome_channel #channel` — set the channel where new members receive their welcome shoutout
- `/set_welcome_role @role` — set the role granted to members after accepting T&C
- `/set_terms <text>` — update the Terms & Conditions text sent to new members via DM
- `/set_monitoring_interval <hours>` — how often (1–24h) the activity digest is posted to #bot-logs
- `/set_monitoring_period <days>` — how many days (1–30) after joining a member is monitored
- `/resend_terms @member` — manually resend the T&C DM to a member (e.g. if they had DMs off)

## Settings (variables.py)
- `MONITORING_PERIOD_DAYS` — default days new members are monitored, default 7
- `MESSAGE_LOG_INTERVAL_HOURS` — default hours between activity log posts, default 1
- `DEFAULT_TERMS` — fallback T&C text used before an admin sets custom text via `/set_terms`
