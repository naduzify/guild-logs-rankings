"""Minimal Warcraft Logs API v2 client with an on-disk response cache.

Every response is written under data/cache/ at a path chosen by the caller,
so an interrupted crawl resumes by skipping what is already cached.
"""

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "cache"

TOKEN_URL = "https://www.warcraftlogs.com/oauth/token"
# Progression Classic realms (Arugal: Classic 2019 -> MoP) live on the classic site.
# The vanilla site hosts Era/SoD realms; it is only queried as a fallback.
HOSTS = {
    "classic": "https://classic.warcraftlogs.com/api/v2",
    "vanilla": "https://vanilla.warcraftlogs.com/api/v2",
}
# Written by pipeline.auth. When present, queries go to /user, which can read archived reports.
USER_TOKEN_FILE = ROOT / ".wcl_user_token.json"


class WCLError(RuntimeError):
    pass


class WCLClient:
    def __init__(self, host: str = "classic", user: bool = True):
        load_dotenv(ROOT / ".env")
        self.client_id = os.environ.get("WCL_CLIENT_ID")
        self.client_secret = os.environ.get("WCL_CLIENT_SECRET")
        if not self.client_id or not self.client_secret:
            raise WCLError("WCL_CLIENT_ID / WCL_CLIENT_SECRET missing from .env")
        self.host = host
        self.session = requests.Session()
        self._token = None
        if user and USER_TOKEN_FILE.exists():
            self._token = json.loads(USER_TOKEN_FILE.read_text(encoding="utf-8"))["access_token"]
            self.url = HOSTS[host] + "/user"
        else:
            self.url = HOSTS[host] + "/client"
        self.requests_made = 0

    def _get_token(self) -> str:
        if self._token is None:
            resp = self.session.post(
                TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
                timeout=30,
            )
            resp.raise_for_status()
            self._token = resp.json()["access_token"]
        return self._token

    def query(self, query: str, variables: dict | None = None) -> dict:
        """Run a GraphQL query, retrying on rate limit and transient errors."""
        for attempt in range(6):
            resp = self.session.post(
                self.url,
                json={"query": query, "variables": variables or {}},
                headers={"Authorization": f"Bearer {self._get_token()}"},
                timeout=120,
            )
            self.requests_made += 1
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 60))
                print(f"  rate limited, sleeping {wait}s")
                time.sleep(wait)
                continue
            if resp.status_code >= 500:
                time.sleep(5 * (attempt + 1))
                continue
            resp.raise_for_status()
            body = resp.json()
            if body.get("errors"):
                raise WCLError(json.dumps(body["errors"])[:1000])
            return body["data"]
        raise WCLError(f"giving up after retries: {resp.status_code} {resp.text[:300]}")

    def cached_query(self, cache_key: str, query: str, variables: dict | None = None) -> dict:
        """Return the cached response for cache_key, fetching it if missing."""
        path = CACHE_DIR / self.host / f"{cache_key}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))["data"]
        data = self.query(query, variables)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"query": query, "variables": variables, "fetched_at": time.time(), "data": data}
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)
        return data

    def rate_limit(self) -> dict:
        q = "{ rateLimitData { limitPerHour pointsSpentThisHour pointsResetIn } }"
        return self.query(q)["rateLimitData"]
