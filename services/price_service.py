import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

LOGGER = logging.getLogger(__name__)

API_BASE_URL = "https://www.goldapi.io/api"
REQUEST_TIMEOUT = 15


def get_goldapi_key() -> str | None:
    return os.getenv("GOLDAPI_KEY") or os.getenv("GOLD_API_KEY")


def get_prices() -> dict[str, float] | None:
    api_key = get_goldapi_key()
    if not api_key:
        LOGGER.error("GOLDAPI_KEY is not set")
        return None

    headers = {
        "x-access-token": api_key,
        "Content-Type": "application/json",
    }

    prices: dict[str, float] = {}

    for metal in ("XAU", "XAG"):
        try:
            response = requests.get(
                f"{API_BASE_URL}/{metal}/USD",
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            payload = response.json()
        except requests.RequestException as exc:
            LOGGER.error("Request failed for %s: %s", metal, exc)
            return None
        except ValueError:
            LOGGER.error("Invalid JSON response for %s", metal)
            return None

        if response.status_code != 200:
            LOGGER.error(
                "GoldAPI rejected %s with status %s: %s",
                metal,
                response.status_code,
                payload,
            )
            return None

        if "price" not in payload:
            LOGGER.error("Missing price in GoldAPI response for %s: %s", metal, payload)
            return None

        prices["gold" if metal == "XAU" else "silver"] = float(payload["price"])

    return prices
