import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import re
import pytz
import requests
from datetime import datetime, date, timedelta
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative
from config import ACCESS_TOKEN, APP_ID, APP_SECRET, AD_ACCOUNT_ID
from monday_client import fetch_leads, fetch_leads_summary, fetch_urgent
from schedule_manager import should_be_active, load_state, ISRAEL_TZ

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="מרכז בקרה | גפן",
    layout="wide",
    page_icon="🎯",
    initial_sidebar_state="expanded",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;600;700;900&display=swap');

html, body, [class*="css"], * {
  font-family: 'Heebo', sans-serif !important;
}
.stApp { background: #080f1e !important; direction: rtl; }
section[data-testid="stSidebar"] { background: #060d1a !important; border-left: 1px solid rgba(255,255,255,0.06); }
section[data-testid="stSidebar"] * { color: rgba(255,255,255,0.85) !important; direction: rtl; }
#MainMenu, footer, header { visibility: hidden; }

/* כרטיסי KPI */
.kpi-wrap { display: grid; grid-template-columns: repeat(4,1fr); gap: 16px; margin-bottom: 24px; }
.kpi-card {
  background: #0f1e35;
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 18px;
  padding: 22px 20px;
  text-align: center;
  position: relative;
  overflow: hidden;
}
.kpi-card::before {
  content: '';
  position: absolute;
  top: 0; right: 0;
  width: 80px; height: 80px;
  border-radius: 50%;
  opacity: 0.07;
  background: var(--kpi-color, #E8A020);
  transform: translate(20px,-20px);
}
.kpi-icon { font-size: 1.5rem; margin-bottom: 8px; display: block; }
.kpi-value { font-size: 2.2rem; font-weight: 900; color: var(--kpi-color, #E8A020); line-height: 1; }
.kpi-label { font-size: 0.8rem; color: rgba(255,255,255,0.5); margin-top: 8px; font-weight: 600; letter-spacing: 0.5px; }
.kpi-delta { font-size: 0.78rem; margin-top: 6px; font-weight: 700; }
.kpi-delta.up { color: #10b981; }
.kpi-delta.down { color: #ef4444; }

/* header */
.dash-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 0 24px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  margin-bottom: 28px;
}
.dash-title { font-size: 1.6rem; font-weight: 900; color: #fff; }
.dash-title span { color: #E8A020; }
.dash-sub { font-size: 0.82rem; color: rgba(255,255,255,0.4); margin-top: 4px; }
.dash-updated { font-size: 0.78rem; color: rgba(255,255,255,0.3); text-align: left; direction: ltr; }

/* section titles */
.section-title {
  font-size: 1rem; font-weight: 800; color: #fff;
  margin: 28px 0 14px;
  display: flex; align-items: center; gap: 8px;
}
.section-title::after {
  content: ''; flex: 1; height: 1px;
  background: rgba(255,255,255,0.06);
}

/* status badges */
.badge {
  display: inline-block;
  padding: 3px 10px; border-radius: 50px;
  font-size: 0.72rem; font-weight: 700; letter-spacing: 0.5px;
}
.badge-active { background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.3); }
.badge-paused { background: rgba(239,68,68,0.12); color: #ef4444; border: 1px solid rgba(239,68,68,0.2); }

/* adset cards */
.adset-card {
  background: #0f1e35;
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 14px;
  padding: 16px 18px;
  margin-bottom: 10px;
  transition: border-color 0.2s;
}
.adset-card:hover { border-color: rgba(232,160,32,0.25); }
.adset-card.has-convert { border-right: 3px solid #10b981; }
.adset-card.burned { border-right: 3px solid #f59e0b; }
.adset-card.wasting { border-right: 3px solid #ef4444; }
.adset-name { font-size: 0.95rem; font-weight: 800; color: #fff; margin-bottom: 10px; }
.adset-stats { display: flex; gap: 20px; flex-wrap: wrap; }
.adset-stat { text-align: center; }
.adset-stat .val { font-size: 1.05rem; font-weight: 800; color: #E8A020; }
.adset-stat .lbl { font-size: 0.7rem; color: rgba(255,255,255,0.4); margin-top: 2px; }

/* input overrides */
.stNumberInput input { background: #162235 !important; border: 1px solid rgba(255,255,255,0.1) !important; color: white !important; border-radius: 8px !important; text-align: center !important; }
.stToggle { direction: ltr; }
.stButton button {
  background: #E8A020 !important; color: #060d1a !important;
  font-weight: 800 !important; border-radius: 8px !important;
  border: none !important; font-family: 'Heebo', sans-serif !important;
}
.stButton button:hover { background: #F5B84A !important; }

/* success / error */
.stSuccess, .stError { border-radius: 10px !important; direction: rtl; }

/* ads table */
.ads-table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
.ads-table th { color: rgba(255,255,255,0.4); font-weight: 700; font-size: 0.75rem; padding: 10px 12px; text-align: right; border-bottom: 1px solid rgba(255,255,255,0.06); }
.ads-table td { padding: 10px 12px; color: rgba(255,255,255,0.85); border-bottom: 1px solid rgba(255,255,255,0.04); }
.ads-table tr:hover td { background: rgba(255,255,255,0.03); }
.ads-table tr.winner td { background: rgba(16,185,129,0.07); }
.ads-table tr.waster td { background: rgba(239,68,68,0.07); }
.ad-name { font-weight: 700; color: #fff; }

/* selectbox / radio */
.stSelectbox select, .stRadio label { color: rgba(255,255,255,0.85) !important; }

/* expander */
.streamlit-expanderHeader { background: #0f1e35 !important; border-radius: 10px !important; color: white !important; font-weight: 700 !important; }

/* ── Leads tab ── */
.action-card {
  background: #0f1e35;
  border-radius: 14px;
  padding: 20px;
  text-align: center;
  cursor: pointer;
}
.action-card.red   { border: 2px solid rgba(239,68,68,0.5); }
.action-card.yellow{ border: 2px solid rgba(245,158,11,0.5); }
.action-card.green { border: 2px solid rgba(16,185,129,0.4); }
.action-num  { font-size: 2.6rem; font-weight: 900; line-height: 1; }
.action-lbl  { font-size: 0.8rem; color: rgba(255,255,255,0.5); margin-top: 6px; font-weight: 600; }
.action-card.red   .action-num { color: #ef4444; }
.action-card.yellow .action-num { color: #f59e0b; }
.action-card.green  .action-num { color: #10b981; }

.funnel-wrap { display: flex; align-items: center; gap: 0; margin: 16px 0; }
.funnel-stage {
  flex: 1; background: #0f1e35;
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 10px; padding: 14px 10px;
  text-align: center;
}
.funnel-num  { font-size: 1.6rem; font-weight: 900; color: #E8A020; }
.funnel-lbl  { font-size: 0.68rem; color: rgba(255,255,255,0.4); margin-top: 4px; }
.funnel-arrow { color: rgba(255,255,255,0.2); font-size: 1.2rem; padding: 0 6px; flex: 0; }

.leads-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.leads-table th { color: rgba(255,255,255,0.35); font-weight: 700; font-size: 0.72rem; padding: 10px 10px; text-align: right; border-bottom: 1px solid rgba(255,255,255,0.06); }
.leads-table td { padding: 9px 10px; border-bottom: 1px solid rgba(255,255,255,0.04); }
.leads-table tr.overdue td { background: rgba(239,68,68,0.07); }
.leads-table tr.new-lead td { background: rgba(245,158,11,0.06); }
.leads-table tr.in-pipe td  { background: rgba(255,255,255,0.01); }
.leads-table tr.closed td   { opacity: 0.45; }

/* ── Status tab ── */
.status-big {
  border-radius: 20px; padding: 28px 24px; text-align: center; margin-bottom: 20px;
}
.status-big.active { background: rgba(16,185,129,0.08); border: 2px solid rgba(16,185,129,0.3); }
.status-big.paused { background: rgba(239,68,68,0.07); border: 2px solid rgba(239,68,68,0.25); }
.status-dot { font-size: 2.5rem; margin-bottom: 10px; }
.status-main { font-size: 1.4rem; font-weight: 900; color: #fff; }
.status-sub  { font-size: 0.85rem; color: rgba(255,255,255,0.45); margin-top: 6px; }
.today-stat  { background: #0f1e35; border: 1px solid rgba(255,255,255,0.07); border-radius: 14px; padding: 18px; text-align: center; }
.today-val   { font-size: 1.8rem; font-weight: 900; color: #E8A020; }
.today-lbl   { font-size: 0.75rem; color: rgba(255,255,255,0.4); margin-top: 6px; }
</style>
""", unsafe_allow_html=True)


# ─── API helpers ──────────────────────────────────────────────────────────────
def init_api():
    FacebookAdsApi.init(APP_ID, APP_SECRET, ACCESS_TOKEN)
    return AdAccount(AD_ACCOUNT_ID)


@st.cache_data(ttl=300)
def fetch_adset_insights(date_preset):
    FacebookAdsApi.init(APP_ID, APP_SECRET, ACCESS_TOKEN)
    account = AdAccount(AD_ACCOUNT_ID)

    try:
        insights_raw = list(account.get_insights(fields=[
            'adset_id', 'adset_name', 'campaign_name', 'campaign_id',
            'spend', 'impressions', 'reach', 'frequency',
            'clicks', 'ctr', 'actions',
        ], params={'date_preset': date_preset, 'level': 'adset'}))
    except Exception:
        insights_raw = []

    try:
        adsets_raw = list(account.get_ad_sets(fields=['id', 'name', 'status', 'daily_budget', 'campaign_id']))
        adset_meta = {a['id']: dict(a) for a in adsets_raw}
    except Exception:
        adset_meta = {}

    try:
        campaigns_raw = list(account.get_campaigns(fields=['id', 'name', 'status']))
        campaign_meta = {c['id']: dict(c) for c in campaigns_raw}
    except Exception:
        campaign_meta = {}

    rows = []
    for row in insights_raw:
        row = dict(row)
        adset_id = row.get('adset_id', '')
        campaign_id = row.get('campaign_id', '')
        meta = adset_meta.get(adset_id, {})
        camp = campaign_meta.get(campaign_id, {})

        actions = row.get('actions', [])
        wa = next((float(a['value']) for a in actions if 'messaging_conversation_started_7d' in a.get('action_type', '')), 0)
        leads = next((float(a['value']) for a in actions if a.get('action_type') == 'lead'), 0)
        spend = float(row.get('spend', 0))
        freq = float(row.get('frequency', 0))
        ctr = float(row.get('ctr', 0))
        daily_budget = meta.get('daily_budget')

        status_flag = 'normal'
        if wa > 0 or leads > 0:
            status_flag = 'convert'
        elif freq > 4:
            status_flag = 'burned'
        elif spend > 50:
            status_flag = 'wasting'

        rows.append({
            'campaign_name': row.get('campaign_name', camp.get('name', '?')),
            'campaign_id': campaign_id,
            'campaign_status': camp.get('status', '?'),
            'adset_id': adset_id,
            'adset_name': row.get('adset_name', meta.get('name', '?')),
            'adset_status': meta.get('status', 'ACTIVE'),
            'daily_budget': int(daily_budget) // 100 if daily_budget else 0,
            'spend': spend,
            'impressions': int(row.get('impressions', 0)),
            'reach': int(row.get('reach', 0)),
            'frequency': round(freq, 1),
            'clicks': int(row.get('clicks', 0)),
            'ctr': round(ctr, 2),
            'wa': int(wa),
            'leads': int(leads),
            'conversions': int(wa + leads),
            'status_flag': status_flag,
        })
    return rows


@st.cache_data(ttl=300)
def fetch_ad_insights(date_preset):
    FacebookAdsApi.init(APP_ID, APP_SECRET, ACCESS_TOKEN)
    account = AdAccount(AD_ACCOUNT_ID)

    try:
        insights_raw = list(account.get_insights(fields=[
            'ad_id', 'ad_name', 'campaign_name',
            'spend', 'impressions', 'clicks', 'ctr', 'actions',
        ], params={'date_preset': date_preset, 'level': 'ad'}))
    except Exception:
        insights_raw = []

    try:
        ads_raw = list(account.get_ads(fields=['id', 'name', 'status', 'adset_id']))
        ad_meta = {a['id']: dict(a) for a in ads_raw}
    except Exception:
        ad_meta = {}

    rows = []
    for row in insights_raw:
        row = dict(row)
        ad_id = row.get('ad_id', '')
        meta = ad_meta.get(ad_id, {})

        actions = row.get('actions', [])
        wa = next((float(a['value']) for a in actions if 'messaging_conversation_started_7d' in a.get('action_type', '')), 0)
        leads = next((float(a['value']) for a in actions if a.get('action_type') == 'lead'), 0)
        spend = float(row.get('spend', 0))

        flag = 'normal'
        if wa > 0 or leads > 0:
            flag = 'winner'
        elif spend > 30:
            flag = 'waster'

        rows.append({
            'campaign_name': row.get('campaign_name', '?'),
            'ad_id': ad_id,
            'ad_name': row.get('ad_name', meta.get('name', '?')),
            'ad_status': meta.get('status', 'ACTIVE'),
            'adset_id': meta.get('adset_id', ''),
            'spend': spend,
            'clicks': int(row.get('clicks', 0)),
            'ctr': round(float(row.get('ctr', 0)), 2),
            'wa': int(wa),
            'leads': int(leads),
            'conversions': int(wa + leads),
            'flag': flag,
        })
    return rows


@st.cache_data(ttl=300)
def fetch_daily_spend():
    FacebookAdsApi.init(APP_ID, APP_SECRET, ACCESS_TOKEN)
    account = AdAccount(AD_ACCOUNT_ID)
    try:
        insights = list(account.get_insights(fields=['spend', 'date_start'], params={
            'date_preset': 'last_14d',
            'time_increment': 1,
            'level': 'account',
        }))
        return [{'date': r['date_start'], 'spend': float(r.get('spend', 0))} for r in insights]
    except Exception:
        return []


@st.cache_data(ttl=1800)
def fetch_ad_creatives():
    FacebookAdsApi.init(APP_ID, APP_SECRET, ACCESS_TOKEN)
    account = AdAccount(AD_ACCOUNT_ID)
    result = {}
    try:
        ads = account.get_ads(fields=['id', 'creative'])
        for ad in ads:
            creative_id = ad.get('creative', {}).get('id')
            if not creative_id:
                continue
            try:
                cr = AdCreative(creative_id).api_get(fields=[
                    'body', 'thumbnail_url', 'image_url', 'object_story_spec'
                ])
                link_data = cr.get('object_story_spec', {}).get('link_data', {})
                body = cr.get('body') or link_data.get('message', '')
                thumb = (cr.get('image_url')
                         or link_data.get('picture')
                         or cr.get('thumbnail_url', ''))
                result[ad['id']] = {
                    'thumbnail_url': thumb,
                    'body': body,
                    'copy_preview': body[:140] + '...' if len(body) > 140 else body,
                }
            except Exception:
                continue
    except Exception:
        pass
    return result


@st.cache_data(ttl=300)
def fetch_monday_data():
    df = fetch_leads()
    summary = fetch_leads_summary(df)
    urgent = fetch_urgent(df)
    return df, summary, urgent


@st.cache_data(ttl=300)
def fetch_today_summary():
    FacebookAdsApi.init(APP_ID, APP_SECRET, ACCESS_TOKEN)
    account = AdAccount(AD_ACCOUNT_ID)
    try:
        insights = list(account.get_insights(fields=['actions', 'spend'], params={
            'date_preset': 'today',
            'level': 'account',
        }))
        if not insights:
            return 0.0, 0
        row = dict(insights[0])
        spend = float(row.get('spend', 0))
        actions = row.get('actions', [])
        wa = next((float(a['value']) for a in actions
                   if 'messaging_conversation_started_7d' in a.get('action_type', '')), 0)
        leads = next((float(a['value']) for a in actions
                      if a.get('action_type') == 'lead'), 0)
        return spend, int(wa + leads)
    except Exception:
        return 0.0, 0


# Ad-set name → topic mapping
ADSET_TOPIC_MAP = {
    "גפן | חינוך פיננסי | 2026":          "חינוך פיננסי",
    "גפן | בינה מלאכותית | 2026":         "בינה מלאכותית",
    "גפן | ספורט | 2026":                  "ספורט (קפוארה/נינג'ה/לחימה)",
    "גפן | סדנאות מורים וילדים | 2026":   "סדנאות AI",
}


@st.cache_data(ttl=300)
def fetch_adset_spend_by_topic():
    """Fetch spend per ad-set for the last 30 days using the Graph API (requests)."""
    url = f"https://graph.facebook.com/v20.0/{AD_ACCOUNT_ID}/adsets"
    params = {
        "fields": "name,insights.date_preset(last_30d){spend}",
        "access_token": ACCESS_TOKEN,
        "limit": 200,
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return {}

    spend_by_topic: dict[str, float] = {}
    for adset in data.get("data", []):
        name = adset.get("name", "")
        topic = None
        for adset_key, topic_val in ADSET_TOPIC_MAP.items():
            if adset_key in name:
                topic = topic_val
                break
        if topic is None:
            continue
        insights = adset.get("insights", {}).get("data", [])
        spend = sum(float(row.get("spend", 0)) for row in insights)
        spend_by_topic[topic] = spend_by_topic.get(topic, 0.0) + spend

    return spend_by_topic


def update_adset_budget(adset_id, new_budget_ils):
    FacebookAdsApi.init(APP_ID, APP_SECRET, ACCESS_TOKEN)
    AdSet(adset_id).api_update(params={'daily_budget': new_budget_ils * 100})
    fetch_adset_insights.clear()


def toggle_adset(adset_id, current_status):
    FacebookAdsApi.init(APP_ID, APP_SECRET, ACCESS_TOKEN)
    new_status = 'PAUSED' if current_status == 'ACTIVE' else 'ACTIVE'
    AdSet(adset_id).api_update(params={'status': new_status})
    fetch_adset_insights.clear()
    fetch_ad_insights.clear()


def toggle_ad(ad_id, current_status):
    FacebookAdsApi.init(APP_ID, APP_SECRET, ACCESS_TOKEN)
    new_status = 'PAUSED' if current_status == 'ACTIVE' else 'ACTIVE'
    Ad(ad_id).api_update(params={'status': new_status})
    fetch_ad_insights.clear()


def wa_link(phone_raw: str) -> str:
    digits = re.sub(r'[^\d]', '', str(phone_raw))
    if digits.startswith('972'):
        pass
    elif digits.startswith('0') and len(digits) >= 10:
        digits = '972' + digits[1:]
    elif len(digits) == 9:
        digits = '972' + digits
    return f"https://wa.me/{digits}" if len(digits) >= 11 else ""


# ─── Layout ───────────────────────────────────────────────────────────────────
account = init_api()

with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:16px 0 24px">
      <div style="font-size:1.8rem">🎯</div>
      <div style="font-size:1rem;font-weight:900;color:#E8A020;margin-top:4px">מרכז בקרה</div>
      <div style="font-size:0.72rem;color:rgba(255,255,255,0.35);margin-top:2px">תוכניות העשרה גפן</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**⏱️ טווח זמן**")
    date_options = {
        'היום': 'today',
        'אתמול': 'yesterday',
        '7 ימים': 'last_7d',
        '14 ימים': 'last_14d',
        'החודש': 'this_month',
        'מהתחלה': 'maximum',
    }
    date_label = st.selectbox('', list(date_options.keys()), index=2, label_visibility='collapsed')
    date_preset = date_options[date_label]

    st.markdown("**📊 סטטוס**")
    status_filter = st.radio('', ['הכל', 'פעיל בלבד', 'מושהה בלבד'], label_visibility='collapsed')

    st.markdown("**🎯 ביצועים**")
    perf_filter = st.selectbox('', ['הכל', 'יש המרות', 'אפס המרות', 'קהל שרוף (>4x)'], label_visibility='collapsed')

    st.markdown("**💸 מינימום הוצאה**")
    min_spend = st.slider('', 0, 300, 0, 5, label_visibility='collapsed')

    st.markdown("**🔃 מיון לפי**")
    sort_by = st.selectbox('', ['הוצאה', 'CTR', 'המרות', 'תדירות'], label_visibility='collapsed')

    st.markdown("---")
    auto_refresh = st.checkbox('🔄 רענון אוטומטי (5 דק׳)', value=False)

    if st.button('🔄 רענן עכשיו', use_container_width=True):
        fetch_adset_insights.clear()
        fetch_ad_insights.clear()
        fetch_daily_spend.clear()
        fetch_ad_creatives.clear()
        fetch_monday_data.clear()
        fetch_today_summary.clear()
        st.rerun()


# Header
now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
st.markdown(f"""
<div class="dash-header">
  <div>
    <div class="dash-title">🎯 מרכז בקרה <span>| תוכניות העשרה גפן</span></div>
    <div class="dash-sub">נתוני Facebook Ads + לידים Monday.com בזמן אמת</div>
  </div>
  <div class="dash-updated">עודכן: {now_str}</div>
</div>
""", unsafe_allow_html=True)


# Fetch all data
with st.spinner('טוען נתונים...'):
    adset_rows = fetch_adset_insights(date_preset)
    ad_rows = fetch_ad_insights(date_preset)
    daily_rows = fetch_daily_spend()
    try:
        creatives_map = fetch_ad_creatives()
    except Exception:
        creatives_map = {}
    try:
        df_leads, leads_summary, leads_urgent = fetch_monday_data()
    except Exception:
        df_leads = pd.DataFrame()
        leads_summary = {}
        leads_urgent = {}

df_adsets = pd.DataFrame(adset_rows) if adset_rows else pd.DataFrame()
df_ads = pd.DataFrame(ad_rows) if ad_rows else pd.DataFrame()
df_daily = pd.DataFrame(daily_rows) if daily_rows else pd.DataFrame()

# Apply adset filters
if not df_adsets.empty:
    if status_filter == 'פעיל בלבד':
        df_adsets = df_adsets[df_adsets['adset_status'] == 'ACTIVE']
    elif status_filter == 'מושהה בלבד':
        df_adsets = df_adsets[df_adsets['adset_status'] == 'PAUSED']

    if perf_filter == 'יש המרות':
        df_adsets = df_adsets[df_adsets['conversions'] > 0]
    elif perf_filter == 'אפס המרות':
        df_adsets = df_adsets[df_adsets['conversions'] == 0]
    elif perf_filter == 'קהל שרוף (>4x)':
        df_adsets = df_adsets[df_adsets['frequency'] > 4]

    df_adsets = df_adsets[df_adsets['spend'] >= min_spend]

    sort_map = {'הוצאה': 'spend', 'CTR': 'ctr', 'המרות': 'conversions', 'תדירות': 'frequency'}
    df_adsets = df_adsets.sort_values(sort_map[sort_by], ascending=False)

if not df_ads.empty:
    df_ads = df_ads.sort_values('spend', ascending=False)


# ─── TABS ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 מודעות", "🔴 לידים", "⚡ סטטוס"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — מודעות
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    # KPI Cards
    total_spend = df_adsets['spend'].sum() if not df_adsets.empty else 0
    total_conv = df_adsets['conversions'].sum() if not df_adsets.empty else 0
    cpa = total_spend / total_conv if total_conv > 0 else 0
    avg_ctr = df_adsets['ctr'].mean() if not df_adsets.empty else 0
    total_reach = df_adsets['reach'].sum() if not df_adsets.empty else 0

    kpi_html = f"""
    <div class="kpi-wrap">
      <div class="kpi-card" style="--kpi-color:#E8A020">
        <span class="kpi-icon">💸</span>
        <div class="kpi-value">₪{total_spend:,.0f}</div>
        <div class="kpi-label">הוצאה כוללת — {date_label}</div>
      </div>
      <div class="kpi-card" style="--kpi-color:#10b981">
        <span class="kpi-icon">📲</span>
        <div class="kpi-value">{int(total_conv)}</div>
        <div class="kpi-label">המרות (WA + לידים)</div>
      </div>
      <div class="kpi-card" style="--kpi-color:#6366f1">
        <span class="kpi-icon">💰</span>
        <div class="kpi-value">{'₪'+f'{cpa:,.0f}' if total_conv > 0 else '—'}</div>
        <div class="kpi-label">עלות ממוצעת להמרה</div>
      </div>
      <div class="kpi-card" style="--kpi-color:#f59e0b">
        <span class="kpi-icon">👁️</span>
        <div class="kpi-value">{avg_ctr:.2f}%</div>
        <div class="kpi-label">CTR ממוצע | Reach: {total_reach:,}</div>
      </div>
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)

    # Daily spend chart
    if not df_daily.empty:
        st.markdown('<div class="section-title">📈 הוצאה יומית — 14 ימים</div>', unsafe_allow_html=True)
        df_daily['date'] = pd.to_datetime(df_daily['date'])
        df_daily = df_daily.sort_values('date')

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_daily['date'],
            y=df_daily['spend'],
            marker_color='#E8A020',
            marker_line_width=0,
            hovertemplate='<b>%{x|%d/%m}</b><br>₪%{y:,.0f}<extra></extra>',
        ))
        fig.update_layout(
            paper_bgcolor='#0f1e35',
            plot_bgcolor='#0f1e35',
            font=dict(color='rgba(255,255,255,0.6)', family='Heebo'),
            margin=dict(l=10, r=10, t=10, b=10),
            height=180,
            xaxis=dict(showgrid=False, color='rgba(255,255,255,0.3)'),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='rgba(255,255,255,0.3)'),
            bargap=0.3,
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # Creative gallery
    st.markdown('<div class="section-title">🖼️ ניתוח קריאטיב</div>', unsafe_allow_html=True)

    if not df_ads.empty and creatives_map:
        tab_gallery, tab_compare = st.tabs(["📸 גלריה", "📊 השוואת קריאטיב"])

        with tab_gallery:
            sorted_ads = df_ads.sort_values('spend', ascending=False)
            cols_per_row = 3
            ad_list = list(sorted_ads.iterrows())
            for i in range(0, len(ad_list), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, (_, ad) in enumerate(ad_list[i:i + cols_per_row]):
                    cr = creatives_map.get(ad['ad_id'], {})
                    thumb = cr.get('thumbnail_url', '')
                    copy_text = cr.get('copy_preview', '')
                    flag = ad.get('flag', 'normal')

                    border_color = '#10b981' if flag == 'winner' else ('#ef4444' if flag == 'waster' else 'rgba(255,255,255,0.07)')
                    flag_badge = '✅ מנצח' if flag == 'winner' else ('🔴 בזבזן' if flag == 'waster' else '')
                    conv_text = f'💬 {ad["wa"]} WA' if ad['wa'] > 0 else ('📋 ' + str(ad['leads']) + ' לידים' if ad['leads'] > 0 else '—')

                    with cols[j]:
                        if thumb:
                            st.image(thumb, use_container_width=True)
                        else:
                            st.markdown('<div style="height:160px;background:#162235;border-radius:10px;display:flex;align-items:center;justify-content:center;color:rgba(255,255,255,0.2);font-size:2rem">🖼️</div>', unsafe_allow_html=True)

                        st.markdown(f"""
                        <div style="background:#0f1e35;border:1px solid {border_color};border-radius:12px;padding:14px;margin-top:6px;margin-bottom:4px">
                          <div style="font-size:0.82rem;font-weight:800;color:#fff;margin-bottom:8px">{ad['ad_name']}</div>
                          <div style="display:flex;gap:10px;margin-bottom:8px;flex-wrap:wrap">
                            <span style="font-size:0.78rem;color:#E8A020;font-weight:700">₪{ad['spend']:,.0f}</span>
                            <span style="font-size:0.78rem;color:rgba(255,255,255,0.5)">CTR {ad['ctr']}%</span>
                            <span style="font-size:0.78rem;color:#10b981;font-weight:700">{conv_text}</span>
                          </div>
                          {f'<div style="font-size:0.72rem;color:#10b981;font-weight:800;margin-bottom:6px">{flag_badge}</div>' if flag_badge else ''}
                          <div style="font-size:0.73rem;color:rgba(255,255,255,0.45);line-height:1.5;border-top:1px solid rgba(255,255,255,0.06);padding-top:8px;direction:rtl">{copy_text or "אין קופי זמין"}</div>
                        </div>
                        """, unsafe_allow_html=True)

        with tab_compare:
            df_ads_cr = df_ads.copy()
            df_ads_cr['image_ver'] = df_ads_cr['ad_name'].apply(
                lambda n: 'תמונה 2' if 'תמונה2' in n else ('תמונה 1' if 'תמונה1' in n else 'אחר')
            )
            df_ads_cr['copy_type'] = df_ads_cr['ad_name'].apply(
                lambda n: 'ישיר' if 'ישיר' in n else ('רגשי' if 'רגשי' in n else 'אחר')
            )

            col_img, col_copy = st.columns(2)

            with col_img:
                st.markdown('<div style="font-size:0.9rem;font-weight:800;color:#fff;margin-bottom:12px">📸 תמונה 1 vs תמונה 2</div>', unsafe_allow_html=True)
                img_grp = df_ads_cr.groupby('image_ver').agg(
                    spend=('spend', 'sum'), ctr=('ctr', 'mean'),
                    conversions=('conversions', 'sum'), ads=('ad_id', 'count'),
                ).reset_index()
                for _, r in img_grp.iterrows():
                    winner_tag = ' 🏆' if r['spend'] > 0 and r['conversions'] == img_grp['conversions'].max() and img_grp['conversions'].max() > 0 else ''
                    st.markdown(f"""
                    <div style="background:#0f1e35;border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:14px;margin-bottom:8px">
                      <div style="font-size:0.9rem;font-weight:900;color:#E8A020">{r['image_ver']}{winner_tag}</div>
                      <div style="display:flex;gap:16px;margin-top:8px">
                        <span style="font-size:0.8rem;color:rgba(255,255,255,0.7)">הוצאה: <b style="color:#fff">₪{r['spend']:,.0f}</b></span>
                        <span style="font-size:0.8rem;color:rgba(255,255,255,0.7)">CTR: <b style="color:#fff">{r['ctr']:.2f}%</b></span>
                        <span style="font-size:0.8rem;color:rgba(255,255,255,0.7)">המרות: <b style="color:#10b981">{int(r['conversions'])}</b></span>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

            with col_copy:
                st.markdown('<div style="font-size:0.9rem;font-weight:800;color:#fff;margin-bottom:12px">✍️ ישיר vs רגשי</div>', unsafe_allow_html=True)
                copy_grp = df_ads_cr.groupby('copy_type').agg(
                    spend=('spend', 'sum'), ctr=('ctr', 'mean'),
                    conversions=('conversions', 'sum'), ads=('ad_id', 'count'),
                ).reset_index()
                for _, r in copy_grp.iterrows():
                    winner_tag = ' 🏆' if r['spend'] > 0 and r['conversions'] == copy_grp['conversions'].max() and copy_grp['conversions'].max() > 0 else ''
                    st.markdown(f"""
                    <div style="background:#0f1e35;border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:14px;margin-bottom:8px">
                      <div style="font-size:0.9rem;font-weight:900;color:#E8A020">{r['copy_type']}{winner_tag}</div>
                      <div style="display:flex;gap:16px;margin-top:8px">
                        <span style="font-size:0.8rem;color:rgba(255,255,255,0.7)">הוצאה: <b style="color:#fff">₪{r['spend']:,.0f}</b></span>
                        <span style="font-size:0.8rem;color:rgba(255,255,255,0.7)">CTR: <b style="color:#fff">{r['ctr']:.2f}%</b></span>
                        <span style="font-size:0.8rem;color:rgba(255,255,255,0.7)">המרות: <b style="color:#10b981">{int(r['conversions'])}</b></span>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

            st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
            chart_df = df_ads_cr.groupby(['image_ver', 'copy_type']).agg(
                spend=('spend', 'sum'), conversions=('conversions', 'sum')
            ).reset_index()
            chart_df['קבוצה'] = chart_df['image_ver'] + ' + ' + chart_df['copy_type']

            fig2 = go.Figure()
            fig2.add_trace(go.Bar(name='הוצאה (₪)', x=chart_df['קבוצה'], y=chart_df['spend'],
                                  marker_color='#E8A020', yaxis='y'))
            fig2.add_trace(go.Bar(name='המרות', x=chart_df['קבוצה'], y=chart_df['conversions'],
                                  marker_color='#10b981', yaxis='y2'))
            fig2.update_layout(
                paper_bgcolor='#0f1e35', plot_bgcolor='#0f1e35',
                font=dict(color='rgba(255,255,255,0.6)', family='Heebo'),
                barmode='group', height=220,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation='h', y=1.1, font=dict(color='white')),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='rgba(255,255,255,0.4)'),
                yaxis2=dict(overlaying='y', side='left', showgrid=False, color='#10b981'),
                xaxis=dict(color='rgba(255,255,255,0.4)'),
            )
            st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})

    # Adsets
    st.markdown('<div class="section-title">🗂️ ניהול אד-סטים</div>', unsafe_allow_html=True)

    if df_adsets.empty:
        st.info('אין נתונים לפי הפילטרים שנבחרו')
    else:
        for _, row in df_adsets.iterrows():
            card_class = {
                'convert': 'adset-card has-convert',
                'burned': 'adset-card burned',
                'wasting': 'adset-card wasting',
            }.get(row['status_flag'], 'adset-card')

            flag_badge = {
                'convert': '🟢 יש המרה',
                'burned': '🟡 קהל שרוף',
                'wasting': '🔴 מבזבז',
                'normal': '⚪ רגיל',
            }.get(row['status_flag'], '')

            status_badge = f'<span class="badge badge-active">פעיל</span>' if row['adset_status'] == 'ACTIVE' else '<span class="badge badge-paused">מושהה</span>'

            st.markdown(f"""
            <div class="{card_class}">
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
                <div class="adset-name">{row['adset_name']} &nbsp; {status_badge}</div>
                <div style="font-size:0.78rem;color:rgba(255,255,255,0.4)">{flag_badge} &nbsp;|&nbsp; {row['campaign_name'][:35]}</div>
              </div>
              <div class="adset-stats">
                <div class="adset-stat"><div class="val">₪{row['spend']:,.0f}</div><div class="lbl">הוצאה</div></div>
                <div class="adset-stat"><div class="val">{row['reach']:,}</div><div class="lbl">Reach</div></div>
                <div class="adset-stat"><div class="val">{row['frequency']}</div><div class="lbl">תדירות</div></div>
                <div class="adset-stat"><div class="val">{row['ctr']}%</div><div class="lbl">CTR</div></div>
                <div class="adset-stat"><div class="val">{row['wa']}</div><div class="lbl">WA</div></div>
                <div class="adset-stat"><div class="val">₪{row['daily_budget']}</div><div class="lbl">תקציב/יום</div></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            with col1:
                new_budget = st.number_input(
                    'תקציב יומי (₪)',
                    min_value=5, max_value=5000,
                    value=max(5, int(row['daily_budget'])),
                    step=5,
                    key=f"budget_{row['adset_id']}",
                    label_visibility='collapsed',
                )
            with col2:
                if st.button('💾 עדכן תקציב', key=f"upd_{row['adset_id']}"):
                    if new_budget != row['daily_budget']:
                        try:
                            update_adset_budget(row['adset_id'], new_budget)
                            st.success(f"✅ תקציב עודכן ל-₪{new_budget}/יום")
                            st.rerun()
                        except Exception as e:
                            st.error(f"שגיאה: {e}")
                    else:
                        st.info("אין שינוי בתקציב")
            with col3:
                toggle_label = '⏸️ השהה' if row['adset_status'] == 'ACTIVE' else '▶️ הפעל'
                if st.button(toggle_label, key=f"tog_{row['adset_id']}"):
                    try:
                        toggle_adset(row['adset_id'], row['adset_status'])
                        st.success("✅ סטטוס עודכן")
                        st.rerun()
                    except Exception as e:
                        st.error(f"שגיאה: {e}")
            with col4:
                st.markdown(f"<div style='padding-top:8px;font-size:0.78rem;color:rgba(255,255,255,0.35)'>{row['adset_id'][-8:]}</div>", unsafe_allow_html=True)

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # Ads detail
    st.markdown('<div class="section-title">📣 מודעות בפירוט</div>', unsafe_allow_html=True)

    if not df_ads.empty:
        wasters = df_ads[(df_ads['spend'] > 30) & (df_ads['conversions'] == 0) & (df_ads['ad_status'] == 'ACTIVE')]
        if not wasters.empty:
            col_bulk1, col_bulk2 = st.columns([3, 1])
            with col_bulk1:
                st.markdown(f"<div style='padding:10px 0;font-size:0.85rem;color:#f59e0b'>⚠️ נמצאו <b>{len(wasters)}</b> מודעות שמוציאות >₪30 ואפס המרות</div>", unsafe_allow_html=True)
            with col_bulk2:
                if st.button('⏸️ השהה את כולן', key='bulk_pause'):
                    errors = []
                    for _, wad in wasters.iterrows():
                        try:
                            toggle_ad(wad['ad_id'], 'ACTIVE')
                        except Exception as e:
                            errors.append(str(e))
                    if errors:
                        st.error(f"שגיאות: {'; '.join(errors)}")
                    else:
                        st.success(f"✅ הושהו {len(wasters)} מודעות")
                        st.rerun()

        with st.expander(f"📋 כל המודעות ({len(df_ads)})", expanded=False):
            rows_html = ""
            for _, ad in df_ads.iterrows():
                row_class = 'winner' if ad['flag'] == 'winner' else ('waster' if ad['flag'] == 'waster' else '')
                flag_icon = '✅' if ad['flag'] == 'winner' else ('🔴' if ad['flag'] == 'waster' else '⚪')
                status_icon = '▶️' if ad['ad_status'] == 'ACTIVE' else '⏸️'
                rows_html += f"""
                <tr class="{row_class}">
                  <td><span class="ad-name">{flag_icon} {ad['ad_name']}</span></td>
                  <td>₪{ad['spend']:,.1f}</td>
                  <td>{ad['clicks']}</td>
                  <td>{ad['ctr']}%</td>
                  <td>{'💬 ' + str(ad['wa']) if ad['wa'] > 0 else '—'}</td>
                  <td>{status_icon} {ad['ad_status']}</td>
                </tr>
                """
            st.markdown(f"""
            <table class="ads-table">
              <thead><tr>
                <th>מודעה</th><th>הוצאה</th><th>קליקים</th><th>CTR</th><th>WA</th><th>סטטוס</th>
              </tr></thead>
              <tbody>{rows_html}</tbody>
            </table>
            """, unsafe_allow_html=True)

            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

            for _, ad in df_ads.iterrows():
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.markdown(f"<div style='font-size:0.78rem;color:rgba(255,255,255,0.4);padding:2px 0'>{ad['ad_name']}</div>", unsafe_allow_html=True)
                with col_b:
                    btn_label = '⏸️' if ad['ad_status'] == 'ACTIVE' else '▶️'
                    if st.button(btn_label, key=f"adtog_{ad['ad_id']}"):
                        try:
                            toggle_ad(ad['ad_id'], ad['ad_status'])
                            st.success("✅ עודכן")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

    if auto_refresh:
        import time
        st.markdown("<div style='text-align:center;color:rgba(255,255,255,0.2);font-size:0.75rem;padding:20px 0'>רענון אוטומטי כל 5 דקות</div>", unsafe_allow_html=True)
        time.sleep(300)
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — לידים
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    if df_leads.empty:
        st.info("לא נמצאו לידים — בדוק חיבור ל-Monday.com")
    else:
        overdue_df    = leads_urgent.get("overdue", pd.DataFrame())
        untouched_df  = leads_urgent.get("new_untouched", pd.DataFrame())
        today_fu_df   = leads_urgent.get("followup_today", pd.DataFrame())
        today_date    = date.today()

        # ── Zone 1 — נדרש ממך עכשיו ─────────────────────────────────────────
        st.markdown('<div class="section-title">🚨 נדרש ממך עכשיו</div>', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            n = len(overdue_df)
            st.markdown(f"""
            <div class="action-card {'red' if n > 0 else 'green'}">
              <div class="action-num">{n}</div>
              <div class="action-lbl">פולו-אפ שעבר המועד</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            n = len(untouched_df)
            st.markdown(f"""
            <div class="action-card {'yellow' if n > 0 else 'green'}">
              <div class="action-num">{n}</div>
              <div class="action-lbl">לידים חדשים לא טופלו</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            n = len(today_fu_df)
            st.markdown(f"""
            <div class="action-card {'yellow' if n > 0 else 'green'}">
              <div class="action-num">{n}</div>
              <div class="action-lbl">פולו-אפ היום</div>
            </div>
            """, unsafe_allow_html=True)

        # Urgent lead lists
        urgent_sections = [
            ("🔴 פולו-אפ שעבר המועד", overdue_df, "overdue"),
            ("🟡 לידים חדשים שלא טופלו", untouched_df, "untouched"),
            ("📅 פולו-אפ היום", today_fu_df, "today_fu"),
        ]
        for section_title, section_df, section_key in urgent_sections:
            if section_df is not None and not section_df.empty:
                with st.expander(f"{section_title} ({len(section_df)})", expanded=True):
                    for _, lead in section_df.iterrows():
                        link = wa_link(lead.get('phone', ''))
                        days = lead.get('days_since')
                        days_txt = f"{int(days)} ימים" if days is not None else "—"
                        fu_date = lead.get('followup')
                        fu_txt = fu_date.strftime('%d/%m') if fu_date else "—"

                        col_info, col_wa = st.columns([5, 1])
                        with col_info:
                            st.markdown(f"""
                            <div style="background:#0f1e35;border-radius:10px;padding:12px 14px;margin-bottom:6px">
                              <div style="font-weight:800;color:#fff;font-size:0.9rem">{lead.get('name','—')}</div>
                              <div style="display:flex;gap:14px;margin-top:6px;flex-wrap:wrap">
                                <span style="font-size:0.78rem;color:#E8A020">{lead.get('topic','—')}</span>
                                <span style="font-size:0.78rem;color:rgba(255,255,255,0.4)">{lead.get('stage','—')}</span>
                                <span style="font-size:0.78rem;color:rgba(255,255,255,0.4)">נכנס לפני {days_txt}</span>
                                <span style="font-size:0.78rem;color:rgba(255,255,255,0.4)">פולו-אפ: {fu_txt}</span>
                              </div>
                            </div>
                            """, unsafe_allow_html=True)
                        with col_wa:
                            if link:
                                st.link_button("📱 WA", link, use_container_width=True)

        # ── Zone 2 — פאנל המרה ───────────────────────────────────────────────
        st.markdown('<div class="section-title">📊 פאנל המרה</div>', unsafe_allow_html=True)

        from monday_client import STAGE_ORDER
        stages = leads_summary.get("stages", {})
        active_stages = [s for s in STAGE_ORDER if s not in ["✅ נסגר עסקה", "❌ לא רלוונטי"]]

        funnel_parts = []
        for i, s in enumerate(active_stages):
            funnel_parts.append(f'<div class="funnel-stage"><div class="funnel-num">{stages.get(s, 0)}</div><div class="funnel-lbl">{s}</div></div>')
            if i < len(active_stages) - 1:
                funnel_parts.append('<div class="funnel-arrow">→</div>')

        conv_rate = leads_summary.get("conv_rate", 0)
        closed    = leads_summary.get("closed", 0)
        total_l   = leads_summary.get("total", 0)

        st.markdown(f"""
        <div class="funnel-wrap">{''.join(funnel_parts)}</div>
        <div style="display:flex;gap:24px;margin-top:12px">
          <div style="background:#0f1e35;border:1px solid rgba(16,185,129,0.3);border-radius:10px;padding:14px 20px;text-align:center">
            <div style="font-size:1.6rem;font-weight:900;color:#10b981">{closed}</div>
            <div style="font-size:0.72rem;color:rgba(255,255,255,0.4);margin-top:4px">✅ נסגרו</div>
          </div>
          <div style="background:#0f1e35;border:1px solid rgba(239,68,68,0.25);border-radius:10px;padding:14px 20px;text-align:center">
            <div style="font-size:1.6rem;font-weight:900;color:#ef4444">{stages.get('❌ לא רלוונטי', 0)}</div>
            <div style="font-size:0.72rem;color:rgba(255,255,255,0.4);margin-top:4px">❌ לא רלוונטי</div>
          </div>
          <div style="background:#0f1e35;border:1px solid rgba(99,102,241,0.3);border-radius:10px;padding:14px 20px;text-align:center">
            <div style="font-size:1.6rem;font-weight:900;color:#6366f1">{conv_rate}%</div>
            <div style="font-size:0.72rem;color:rgba(255,255,255,0.4);margin-top:4px">% המרה ({closed}/{total_l})</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Zone 3 — כל הלידים ───────────────────────────────────────────────
        st.markdown('<div class="section-title">📋 כל הלידים</div>', unsafe_allow_html=True)

        # Filters row
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            topic_opts = ['הכל'] + sorted(df_leads['topic'].dropna().unique().tolist())
            topic_f = st.selectbox('תוכנית', topic_opts, key='lead_topic_f', label_visibility='collapsed')
        with fc2:
            stage_opts = ['הכל'] + STAGE_ORDER
            stage_f = st.selectbox('שלב', stage_opts, key='lead_stage_f', label_visibility='collapsed')
        with fc3:
            urgency_f = st.selectbox('דחיפות', ['הכל', 'פולו-אפ שעבר', 'ליד חדש', 'פולו-אפ היום'], key='lead_urg_f', label_visibility='collapsed')

        # Build display df with urgency column
        disp = df_leads.copy()
        if topic_f != 'הכל':
            disp = disp[disp['topic'] == topic_f]
        if stage_f != 'הכל':
            disp = disp[disp['stage'] == stage_f]

        overdue_ids   = set(overdue_df['id'].tolist()) if not overdue_df.empty else set()
        untouched_ids = set(untouched_df['id'].tolist()) if not untouched_df.empty else set()
        today_ids     = set(today_fu_df['id'].tolist()) if not today_fu_df.empty else set()

        def urgency_rank(row):
            if row['id'] in overdue_ids:
                return 0
            if row['id'] in untouched_ids:
                return 1
            if row['id'] in today_ids:
                return 2
            if row['stage'] in ['✅ נסגר עסקה', '❌ לא רלוונטי']:
                return 4
            return 3

        def row_class(row):
            if row['id'] in overdue_ids:
                return 'overdue'
            if row['id'] in untouched_ids:
                return 'new-lead'
            if row['stage'] in ['✅ נסגר עסקה', '❌ לא רלוונטי']:
                return 'closed'
            return 'in-pipe'

        disp['_rank'] = disp.apply(urgency_rank, axis=1)
        disp = disp.sort_values('_rank')

        if urgency_f == 'פולו-אפ שעבר':
            disp = disp[disp['id'].isin(overdue_ids)]
        elif urgency_f == 'ליד חדש':
            disp = disp[disp['id'].isin(untouched_ids)]
        elif urgency_f == 'פולו-אפ היום':
            disp = disp[disp['id'].isin(today_ids)]

        # Render table
        rows_html = ""
        for _, lead in disp.iterrows():
            rc = row_class(lead)
            link = wa_link(lead.get('phone', ''))
            wa_btn = f'<a href="{link}" target="_blank" style="color:#25D366;font-weight:800;font-size:0.85rem">📱</a>' if link else '—'
            days = lead.get('days_since')
            days_txt = f"{int(days)}י'" if days is not None else "—"
            fu = lead.get('followup')
            fu_txt = fu.strftime('%d/%m') if fu else "—"
            stage_color = {
                '🔴 ליד חדש': '#f59e0b',
                '🟡 יצרתי קשר': '#6366f1',
                '🟠 בשיחה / הצעה': '#E8A020',
                '✅ נסגר עסקה': '#10b981',
                '❌ לא רלוונטי': '#6b7280',
            }.get(lead.get('stage', ''), '#fff')

            rows_html += f"""
            <tr class="{rc}">
              <td style="font-weight:800;color:#fff">{lead.get('name','—')}</td>
              <td style="color:#E8A020">{lead.get('topic','—')}</td>
              <td style="color:{stage_color};font-weight:700;font-size:0.78rem">{lead.get('stage','—')}</td>
              <td style="color:rgba(255,255,255,0.5)">{days_txt}</td>
              <td style="color:rgba(255,255,255,0.5)">{fu_txt}</td>
              <td>{wa_btn}</td>
            </tr>
            """

        st.markdown(f"""
        <table class="leads-table">
          <thead><tr>
            <th>שם</th><th>תוכנית</th><th>שלב</th><th>ימים</th><th>פולו-אפ</th><th>WA</th>
          </tr></thead>
          <tbody>{rows_html}</tbody>
        </table>
        <div style="height:8px"></div>
        """, unsafe_allow_html=True)

        # ── Zone 4 — Revenue ──────────────────────────────────────────────────
        st.markdown('<div class="section-title">💰 Revenue Tracker</div>', unsafe_allow_html=True)

        total_rev   = leads_summary.get("total_revenue", 0)
        total_spend_all = df_adsets['spend'].sum() if not df_adsets.empty else 0
        cpa_real    = total_spend_all / closed if closed > 0 else 0

        rev_c1, rev_c2, rev_c3 = st.columns(3)
        with rev_c1:
            st.markdown(f"""
            <div class="today-stat">
              <div class="today-val">₪{total_rev:,.0f}</div>
              <div class="today-lbl">סה"כ ערך עסקאות שנסגרו</div>
            </div>
            """, unsafe_allow_html=True)
        with rev_c2:
            st.markdown(f"""
            <div class="today-stat">
              <div class="today-val">{'₪'+f'{cpa_real:,.0f}' if closed > 0 else '—'}</div>
              <div class="today-lbl">CPA אמיתי (הוצאה / עסקאות)</div>
            </div>
            """, unsafe_allow_html=True)
        with rev_c3:
            roi = ((total_rev - total_spend_all) / total_spend_all * 100) if total_spend_all > 0 else 0
            roi_color = '#10b981' if roi > 0 else '#ef4444'
            st.markdown(f"""
            <div class="today-stat">
              <div class="today-val" style="color:{roi_color}">{roi:+.0f}%</div>
              <div class="today-lbl">ROI (הכנסות vs הוצאות)</div>
            </div>
            """, unsafe_allow_html=True)

        # ── Zone 5 — עלות ליד לפי נושא ───────────────────────────────────────
        st.markdown('<div class="section-title">📊 עלות ליד לפי נושא</div>', unsafe_allow_html=True)

        try:
            spend_by_topic = fetch_adset_spend_by_topic()
        except Exception:
            spend_by_topic = {}

        # Count leads per topic from Monday data (exclude irrelevant/closed if desired)
        topic_lead_counts = (
            df_leads[df_leads['topic'].notna() & (df_leads['topic'] != '')]
            .groupby('topic')
            .size()
            .to_dict()
        ) if not df_leads.empty else {}

        # Build unified topic set from both sources
        all_topics = sorted(set(list(spend_by_topic.keys()) + list(topic_lead_counts.keys())))

        if not all_topics:
            st.info("אין נתונים לניתוח עלות ליד לפי נושא")
        else:
            cpl_rows = []
            for topic in all_topics:
                spend = spend_by_topic.get(topic, 0.0)
                leads_count = topic_lead_counts.get(topic, 0)
                cpl = spend / leads_count if leads_count > 0 else None
                cpl_rows.append({
                    "נושא":         topic,
                    "הוצאה ₪":     spend,
                    "לידים":       leads_count,
                    "עלות/ליד ₪":  cpl,
                })

            cpl_df = pd.DataFrame(cpl_rows).sort_values("הוצאה ₪", ascending=False)

            # Render styled cards
            cpl_cols = st.columns(len(cpl_df)) if len(cpl_df) <= 4 else st.columns(2)
            for idx, (_, r) in enumerate(cpl_df.iterrows()):
                col = cpl_cols[idx % len(cpl_cols)]
                cpl_val = f"₪{r['עלות/ליד ₪']:,.0f}" if r['עלות/ליד ₪'] is not None else "—"
                spend_val = f"₪{r['הוצאה ₪']:,.0f}" if r['הוצאה ₪'] > 0 else "₪0"
                cpl_color = '#10b981' if (r['עלות/ליד ₪'] or 999) < 80 else ('#f59e0b' if (r['עלות/ליד ₪'] or 999) < 150 else '#ef4444')
                if r['עלות/ליד ₪'] is None:
                    cpl_color = 'rgba(255,255,255,0.3)'
                with col:
                    st.markdown(f"""
                    <div style="background:#0f1e35;border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:18px;text-align:center;margin-bottom:10px">
                      <div style="font-size:0.8rem;font-weight:800;color:#E8A020;margin-bottom:12px;direction:rtl">{r['נושא']}</div>
                      <div style="font-size:1.7rem;font-weight:900;color:{cpl_color};line-height:1">{cpl_val}</div>
                      <div style="font-size:0.68rem;color:rgba(255,255,255,0.35);margin-top:4px;margin-bottom:10px">עלות ליד</div>
                      <div style="display:flex;justify-content:space-around;border-top:1px solid rgba(255,255,255,0.06);padding-top:10px">
                        <div>
                          <div style="font-size:1rem;font-weight:800;color:#fff">{spend_val}</div>
                          <div style="font-size:0.65rem;color:rgba(255,255,255,0.35);margin-top:2px">הוצאה</div>
                        </div>
                        <div>
                          <div style="font-size:1rem;font-weight:800;color:#fff">{int(r['לידים'])}</div>
                          <div style="font-size:0.65rem;color:rgba(255,255,255,0.35);margin-top:2px">לידים</div>
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

            # Summary table
            with st.expander("📋 טבלת סיכום — עלות ליד לפי נושא", expanded=False):
                display_df = cpl_df.copy()
                display_df["הוצאה ₪"] = display_df["הוצאה ₪"].apply(lambda x: f"₪{x:,.0f}")
                display_df["עלות/ליד ₪"] = display_df["עלות/ליד ₪"].apply(
                    lambda x: f"₪{x:,.0f}" if x is not None else "—"
                )
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — סטטוס
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    now_il  = datetime.now(ISRAEL_TZ)
    active  = should_be_active()
    state   = load_state()
    wd      = now_il.weekday()   # 0=Mon … 4=Fri, 5=Sat, 6=Sun
    h, m    = now_il.hour, now_il.minute

    # Determine reason + next change
    if wd == 4 and h >= 12:
        reason     = "שבת — ממשיך עד מוצ״ש"
        next_event = "יחזור: שבת 20:30"
    elif wd == 5 and (h < 20 or (h == 20 and m < 30)):
        reason     = "שבת"
        resume_min = (20 * 60 + 30) - (h * 60 + m)
        next_event = f"יחזור בעוד {resume_min // 60}:{resume_min % 60:02d} שעות"
    elif not active:
        reason     = f"מת-זון — {h:02d}:{m:02d} (01:00–06:00)"
        wake_min   = (6 * 60) - (h * 60 + m)
        next_event = f"יחזור בעוד {wake_min} דקות (06:00)"
    else:
        if h >= 6:
            until_min = (25 * 60) - (h * 60 + m)  # next 01:00
        else:
            until_min = (1 * 60) - (h * 60 + m)
        reason     = f"שעות פעילות ({h:02d}:{m:02d})"
        next_event = f"מת-זון בעוד {until_min // 60}:{until_min % 60:02d} שעות (01:00)"

    paused_count = len(state.get('paused_by_us', []))

    if active:
        st.markdown(f"""
        <div class="status-big active">
          <div class="status-dot">🟢</div>
          <div class="status-main">פרסומות פעילות</div>
          <div class="status-sub">{reason}</div>
          <div class="status-sub" style="margin-top:8px;color:rgba(255,255,255,0.3)">{next_event}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="status-big paused">
          <div class="status-dot">🔴</div>
          <div class="status-main">פרסומות מושהות</div>
          <div class="status-sub">{reason}</div>
          <div class="status-sub" style="margin-top:8px;color:rgba(255,255,255,0.3)">{next_event}</div>
          {f'<div class="status-sub" style="margin-top:6px;color:#f59e0b">{paused_count} אד-סטים הושהו אוטומטית</div>' if paused_count > 0 else ''}
        </div>
        """, unsafe_allow_html=True)

    # Today's metrics
    st.markdown('<div class="section-title">📊 היום עד עכשיו</div>', unsafe_allow_html=True)

    today_spend, today_conv = fetch_today_summary()
    cpa_today = today_spend / today_conv if today_conv > 0 else 0

    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        st.markdown(f"""
        <div class="today-stat">
          <div class="today-val">₪{today_spend:,.0f}</div>
          <div class="today-lbl">הוצאה היום</div>
        </div>
        """, unsafe_allow_html=True)
    with tc2:
        st.markdown(f"""
        <div class="today-stat">
          <div class="today-val">{today_conv}</div>
          <div class="today-lbl">שיחות / לידים היום</div>
        </div>
        """, unsafe_allow_html=True)
    with tc3:
        st.markdown(f"""
        <div class="today-stat">
          <div class="today-val">{'₪'+f'{cpa_today:,.0f}' if today_conv > 0 else '—'}</div>
          <div class="today-lbl">עלות לשיחה היום</div>
        </div>
        """, unsafe_allow_html=True)

    # Schedule reference
    st.markdown('<div class="section-title">📅 לוח זמנים קבוע</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#0f1e35;border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:20px;line-height:2;font-size:0.85rem;color:rgba(255,255,255,0.7)">
      <div>🟢 <b style="color:#fff">ראשון–חמישי</b> &nbsp; 06:00 → 01:00 (למחרת)</div>
      <div>🔴 <b style="color:#fff">01:00 → 06:00</b> &nbsp; מת-זון — אפס המרות בנתונים</div>
      <div>🔴 <b style="color:#fff">שישי 12:00 → שבת 20:30</b> &nbsp; שבת</div>
      <div>🟢 <b style="color:#fff">מוצ"ש 20:30 → ראשון 06:00</b> &nbsp; פעיל (מוצ"ש)</div>
    </div>
    """, unsafe_allow_html=True)

    # Active adsets from FB
    active_adsets_in_state = state.get('paused_by_us', [])
    if active_adsets_in_state:
        st.markdown(f"""
        <div style="margin-top:16px;padding:14px 18px;background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.25);border-radius:12px;font-size:0.83rem;color:#f59e0b">
          ⚠️ {len(active_adsets_in_state)} אד-סטים הושהו ע"י המתזמן — יחזרו אוטומטית בשעות הפעילות
        </div>
        """, unsafe_allow_html=True)


st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)
