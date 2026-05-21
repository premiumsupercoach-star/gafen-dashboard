"""
Ad Schedule Manager — runs every 30 min via cron.
Active hours: 06:00–01:00 (next day) — all day + evening + late night
Dead zone OFF: 01:00–06:00 (zero conversions in data)
Shabbat OFF: Friday 12:00 → Saturday 20:30
Motzei Shabbat ON: Saturday 20:30 → Sunday 06:00 (compensate)
"""
import json
import os
import pytz
from datetime import datetime
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adset import AdSet

# ── config ────────────────────────────────────────────────
import sys
sys.path.insert(0, '/Users/ebg/fb_clean_build')
from config import ACCESS_TOKEN, APP_ID, APP_SECRET, AD_ACCOUNT_ID

STATE_FILE = '/Users/ebg/fb_clean_build/schedule_state.json'
ISRAEL_TZ  = pytz.timezone('Asia/Jerusalem')

# ── schedule logic ─────────────────────────────────────────
def should_be_active():
    now = datetime.now(ISRAEL_TZ)
    wd  = now.weekday()   # 0=Mon … 4=Fri, 5=Sat, 6=Sun
    h, m = now.hour, now.minute

    # Shabbat: Friday from 12:00
    if wd == 4 and h >= 12:
        return False

    # Shabbat: Saturday before 20:30
    if wd == 5 and (h < 20 or (h == 20 and m < 30)):
        return False

    # Motzei Shabbat: Saturday 20:30 → on
    if wd == 5:
        return True

    # Sunday 00:00-06:00 — continuation of Motzei Shabbat night
    if wd == 6 and h < 6:
        return True

    # Regular hours: 06:00–01:00 (cut only 01:00–06:00 dead zone)
    return h >= 6 or h == 0  # 06:00–23:59 and 00:00

# ── state helpers ──────────────────────────────────────────
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'paused_by_us': []}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

# ── facebook helpers ───────────────────────────────────────
def get_active_adsets():
    FacebookAdsApi.init(APP_ID, APP_SECRET, ACCESS_TOKEN)
    account = AdAccount(AD_ACCOUNT_ID)
    adsets = account.get_ad_sets(
        fields=['id', 'name', 'status', 'effective_status'],
        params={'effective_status': ['ACTIVE']}
    )
    return [{'id': a['id'], 'name': a['name']} for a in adsets]

def pause_adset(adset_id):
    AdSet(adset_id).api_update(params={'status': 'PAUSED'})

def resume_adset(adset_id):
    AdSet(adset_id).api_update(params={'status': 'ACTIVE'})

# ── main ───────────────────────────────────────────────────
def main():
    now = datetime.now(ISRAEL_TZ)
    active = should_be_active()
    state  = load_state()
    ts     = now.strftime('%d/%m %H:%M')

    reason = ''
    wd, h, m = now.weekday(), now.hour, now.minute
    if wd == 4 and h >= 12:
        reason = 'שבת'
    elif wd == 5 and (h < 20 or (h == 20 and m < 30)):
        reason = 'שבת'
    elif wd == 5 or (wd == 6 and h < 6):
        reason = 'מוצ"ש — לילה'
    elif not active:
        reason = f'מת-זון ({h:02d}:00 — 01:00–06:00)'
    else:
        reason = f'שעות פעילות ({h:02d}:00)'

    if not active:
        # Pause all currently active adsets
        adsets = get_active_adsets()
        if adsets:
            paused_now = []
            for a in adsets:
                try:
                    pause_adset(a['id'])
                    paused_now.append(a['id'])
                    print(f"  ⏸️  {a['name']}")
                except Exception as e:
                    print(f"  ⚠️  {a['name']}: {e}")
            state['paused_by_us'] = list(set(state['paused_by_us'] + paused_now))
            save_state(state)
            print(f"[{ts}] ⏸️  הושהו {len(paused_now)} אד-סטים — {reason}")
        else:
            print(f"[{ts}] ⏸️  כבר מושהה — {reason}")

    else:
        # Resume only adsets WE paused
        to_resume = state.get('paused_by_us', [])
        if to_resume:
            resumed = []
            for adset_id in to_resume:
                try:
                    resume_adset(adset_id)
                    resumed.append(adset_id)
                except Exception as e:
                    print(f"  ⚠️  {adset_id}: {e}")
            state['paused_by_us'] = []
            save_state(state)
            print(f"[{ts}] ▶️  הופעלו {len(resumed)} אד-סטים — {reason}")
        else:
            print(f"[{ts}] ✅ פעיל — {reason}")

if __name__ == '__main__':
    main()
