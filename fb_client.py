from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
import config


def validate_connection() -> AdAccount:
    """
    Initialises the SDK and validates credentials.
    Returns the AdAccount object on success, raises on failure.
    """
    FacebookAdsApi.init(
        app_id=config.APP_ID,
        app_secret=config.APP_SECRET,
        access_token=config.ACCESS_TOKEN,
        api_version=config.API_VERSION,
    )

    account = AdAccount(config.AD_ACCOUNT_ID)
    info = account.api_get(fields=["name", "account_status", "currency"])

    status_map = {
        1: "ACTIVE", 2: "DISABLED", 3: "UNSETTLED",
        7: "PENDING_RISK_REVIEW", 9: "IN_GRACE_PERIOD",
        100: "PENDING_CLOSURE", 101: "CLOSED",
    }

    print("\n── Connection Validated ──────────────────────────────────────")
    print(f"  Account Name   : {info.get('name')}")
    print(f"  Account ID     : {config.AD_ACCOUNT_ID}")
    print(f"  Currency       : {info.get('currency')}")
    print(f"  Account Status : {status_map.get(info.get('account_status'), 'UNKNOWN')}")
    print("──────────────────────────────────────────────────────────────\n")

    return account
