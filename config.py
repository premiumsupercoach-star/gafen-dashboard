# ── Credentials ────────────────────────────────────────────────────────────
# In Streamlit Cloud: set these in the Secrets dashboard.
# Locally: values below are used as fallback.

try:
    import streamlit as st
    _s = st.secrets
    ACCESS_TOKEN    = _s["ACCESS_TOKEN"]
    APP_ID          = _s["APP_ID"]
    APP_SECRET      = _s["APP_SECRET"]
    AD_ACCOUNT_ID   = _s["AD_ACCOUNT_ID"]
    PAGE_ID         = _s["PAGE_ID"]
    PAGE_TOKEN      = _s["PAGE_TOKEN"]
    API_VERSION     = _s.get("API_VERSION", "v20.0")
    WHATSAPP_NUMBER = _s["WHATSAPP_NUMBER"]
    MONDAY_API_KEY  = _s["MONDAY_API_KEY"]
    LEADS_BOARD_ID  = _s.get("LEADS_BOARD_ID", "5096913676")
except Exception:
    ACCESS_TOKEN  = "EAAXxn7aqXusBRVgxPEfyMO8BtwaZCvTtwxac8bqvpxOCZBtarhnZClP0haLP2wNZBEL7WcRkc7eDPu2WmJrUtW7BIwU8XK6zLLZALdBIG7qknoeuIlbhZA02SAVHXMXJJobMA4wbiGsrqmVlE1ZBW4n7hLcJAv5OWPj9LZCGYHK31ZBSMcxroj9r1K4UodQq37CdReuEl75riJahx"
    APP_ID        = "1673043150266091"
    APP_SECRET    = "77df2df71b6e275e46034e7742fcd2de"
    AD_ACCOUNT_ID = "act_2348841501876406"
    PAGE_ID       = "103770585473146"
    PAGE_TOKEN    = "EAAXxn7aqXusBReQdkZCbnufyAAHN5vmrkHDWJoZAb4W0gr635PoEnERHlfHBRZCR3RrmZC5qjcZCy8uZBI8CRJfzxoMc1eis2QRtaxKQZCVSlZCo541gKKFHry4U3tTGV1lNuTElZAEcMtGe3bCgvQmlmdP1P7WVHpiw6VaZCk61eWw4qo84pONzwL8y1ZBS6VZBntJZBMpq2SaMKs9jCS2FAf5IZD"
    API_VERSION      = "v20.0"
    WHATSAPP_NUMBER  = "+972508787287"
    MONDAY_API_KEY   = "eyJhbGciOiJIUzI1NiJ9.eyJ0aWQiOjYyODM1NDMzNCwiYWFpIjoxMSwidWlkIjo5OTkyODgzOSwiaWFkIjoiMjAyNi0wMy0wM1QxODowMTozOS4wMDBaIiwicGVyIjoibWU6d3JpdGUiLCJhY3RpZCI6MzM4MjcyOTEsInJnbiI6ImV1YzEifQ.DhTQ3KGStEo958KUeNpmSjQJrsHwBte0xf0_9Ntq9zI"
    LEADS_BOARD_ID   = "5096913676"
