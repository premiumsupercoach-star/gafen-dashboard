"""
Monday.com GraphQL client — לידים גפן | 2026
Board ID: 5096913676
"""
import requests
import pandas as pd
from datetime import date, datetime

try:
    from config import MONDAY_API_KEY, LEADS_BOARD_ID
except ImportError:
    MONDAY_API_KEY = ""
    LEADS_BOARD_ID = "5096913676"

URL = "https://api.monday.com/v2"

# Column ID map
COL = {
    "phone":     "phone_mm3j51yp",
    "topic":     "color_mm3jphwb",
    "crm":       "color_mm3j67qk",
    "date_in":   "date_mm3j1tja",
    "followup":  "date_mm3j6hc8",
    "message":   "long_text_mm3jmcnp",
    "deal_val":  "numeric_mm3jm85s",
    "lead_cost": "numeric_mm3jdtan",
    "notes":     "long_text_mm3jv5gb",
}

# Group ID map (pipeline stages)
GROUP_LABELS = {
    "topics":            "🔴 ליד חדש",
    "group_mm3jw7v7":    "🟡 יצרתי קשר",
    "group_mm3j772f":    "🟠 בשיחה / הצעה",
    "group_mm3jbn80":    "✅ נסגר עסקה",
    "group_mm3jyjdr":    "❌ לא רלוונטי",
}

STAGE_ORDER = ["🔴 ליד חדש", "🟡 יצרתי קשר", "🟠 בשיחה / הצעה", "✅ נסגר עסקה", "❌ לא רלוונטי"]


def _gql(query: str, variables: dict = None) -> dict:
    headers = {
        "Authorization": MONDAY_API_KEY,
        "Content-Type": "application/json",
        "API-Version": "2024-01",
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    r = requests.post(URL, json=payload, headers=headers, timeout=15)
    return r.json()


def _col_value(col_values: list, col_id: str) -> str:
    for cv in col_values:
        if cv["id"] == col_id:
            return cv.get("text", "") or ""
    return ""


def fetch_leads() -> pd.DataFrame:
    """Fetch all leads from the board → DataFrame."""
    query = f"""
    {{
      boards(ids: [{LEADS_BOARD_ID}]) {{
        items_page(limit: 200) {{
          items {{
            id
            name
            group {{ id }}
            column_values {{ id text }}
          }}
        }}
      }}
    }}
    """
    data = _gql(query)
    if not data.get("data"):
        return pd.DataFrame()
    rows = []
    for item in data["data"]["boards"][0]["items_page"]["items"]:
        group_id = item.get("group", {}).get("id", "")
        group = {"id": group_id}
        stage = GROUP_LABELS.get(group_id, group_id)
        cv = item["column_values"]

        date_in_str = _col_value(cv, COL["date_in"])
        followup_str = _col_value(cv, COL["followup"])

        try:
            date_in = datetime.strptime(date_in_str, "%Y-%m-%d").date() if date_in_str else None
        except Exception:
            date_in = None
        try:
            followup = datetime.strptime(followup_str, "%Y-%m-%d").date() if followup_str else None
        except Exception:
            followup = None

        days_since = (date.today() - date_in).days if date_in else None
        deal_val = _col_value(cv, COL["deal_val"])
        lead_cost = _col_value(cv, COL["lead_cost"])

        rows.append({
            "id":         item["id"],
            "name":       item["name"],
            "phone":      _col_value(cv, COL["phone"]),
            "topic":      _col_value(cv, COL["topic"]),
            "crm":        _col_value(cv, COL["crm"]),
            "stage":      stage,
            "date_in":    date_in,
            "followup":   followup,
            "days_since": days_since,
            "message":    _col_value(cv, COL["message"]),
            "deal_val":   float(deal_val) if deal_val else 0.0,
            "lead_cost":  float(lead_cost) if lead_cost else 0.0,
            "notes":      _col_value(cv, COL["notes"]),
        })
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=[
        "id","name","phone","topic","crm","stage","date_in",
        "followup","days_since","message","deal_val","lead_cost","notes"
    ])
    return df



def fetch_leads_summary(df: pd.DataFrame = None) -> dict:
    """Count leads per pipeline stage."""
    if df is None:
        df = fetch_leads()
    summary = {stage: 0 for stage in STAGE_ORDER}
    for stage, count in df["stage"].value_counts().items():
        if stage in summary:
            summary[stage] = int(count)
    total = len(df)
    closed = summary.get("✅ נסגר עסקה", 0)
    conv_rate = round(closed / total * 100, 1) if total else 0
    total_revenue = float(df["deal_val"].sum())
    return {
        "stages":       summary,
        "total":        total,
        "closed":       closed,
        "conv_rate":    conv_rate,
        "total_revenue": total_revenue,
    }


def fetch_urgent(df: pd.DataFrame = None) -> dict:
    """Return leads needing action: overdue follow-ups + untouched new leads."""
    if df is None:
        df = fetch_leads()
    today = date.today()

    overdue = df[
        df["followup"].notna() &
        (df["followup"] < today) &
        (~df["stage"].isin(["✅ נסגר עסקה", "❌ לא רלוונטי"]))
    ]

    new_untouched = df[
        (df["stage"] == "🔴 ליד חדש") &
        (df["days_since"].notna()) &
        (df["days_since"] >= 1)
    ]

    followup_today = df[
        df["followup"].notna() &
        (df["followup"] == today)
    ]

    return {
        "overdue":        overdue,
        "new_untouched":  new_untouched,
        "followup_today": followup_today,
    }


def create_lead(name: str, phone: str, topic: str, message: str) -> str:
    """Create a new lead item in '🔴 ליד חדש' group. Returns item ID."""
    import json as _json
    col_vals = _json.dumps({
        COL["phone"]:   {"phone": phone, "countryShortName": "IL"},
        COL["topic"]:   {"label": topic},
        COL["date_in"]: {"date": date.today().isoformat()},
        COL["message"]: {"text": message},
    })
    col_vals_escaped = col_vals.replace('"', '\\"')
    query = f"""
    mutation {{
      create_item(
        board_id: {LEADS_BOARD_ID}
        group_id: "topics"
        item_name: "{name}"
        column_values: "{col_vals_escaped}"
      ) {{ id }}
    }}
    """
    data = _gql(query)
    return data["data"]["create_item"]["id"]


if __name__ == "__main__":
    df = fetch_leads()
    print(f"סה\"כ לידים: {len(df)}")
    summary = fetch_leads_summary(df)
    for stage, count in summary["stages"].items():
        print(f"  {stage}: {count}")
    print(f"% המרה: {summary['conv_rate']}%")
    print(f"הכנסות: ₪{summary['total_revenue']:,.0f}")
