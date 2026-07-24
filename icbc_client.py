"""Client for ICBC's road-test booking API.

Endpoint shapes below were reverse-engineered from public reference
implementations (not official ICBC documentation), so response parsing in
main.py is deliberately defensive. Run `main.py --dry-run --debug` to see
the raw response and adjust field names in main.py if ICBC has changed
anything since these were documented.
"""

from __future__ import annotations

import random
from datetime import date
from typing import Any

import requests

BASE_URL = "https://onlinebusiness.icbc.com/deas-api/v1"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


class ICBCAuthError(RuntimeError):
    pass


class ICBCClient:
    def __init__(self, last_name: str, licence_number: str, keyword: str):
        self.last_name = last_name
        self.licence_number = licence_number
        self.keyword = keyword
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                "User-Agent": random.choice(USER_AGENTS),
            }
        )
        self._token: str | None = None

    def login(self) -> None:
        resp = self._session.put(
            f"{BASE_URL}/webLogin/webLogin",
            json={
                "drvrLastName": self.last_name,
                "licenceNumber": self.licence_number,
                "keyword": self.keyword,
            },
            timeout=20,
        )
        if resp.status_code != 200:
            raise ICBCAuthError(f"ICBC login failed (HTTP {resp.status_code}): {resp.text[:300]}")
        token = resp.headers.get("Authorization")
        if not token:
            raise ICBCAuthError("ICBC login succeeded but no Authorization token was returned")
        self._token = token
        self._session.headers["Authorization"] = token

    def _query_appointments(self, a_pos_id: int, exam_class: int, start_date: date) -> requests.Response:
        return self._session.post(
            f"{BASE_URL}/web/getAvailableAppointments",
            json={
                "aPosID": a_pos_id,
                "examType": f"{exam_class}-R-1",
                "examDate": start_date.isoformat(),
                "ignoreReserveTime": "false",
                "prfDaysOfWeek": "[0,1,2,3,4,5,6]",
                "prfPartsOfDay": "[0,1]",
                "lastName": self.last_name,
                "licenseNumber": self.licence_number,
            },
            timeout=20,
        )

    def get_available_appointments(self, a_pos_id: int, exam_class: int, start_date: date) -> list[dict[str, Any]]:
        if self._token is None:
            self.login()

        resp = self._query_appointments(a_pos_id, exam_class, start_date)
        if resp.status_code == 401:
            self.login()
            resp = self._query_appointments(a_pos_id, exam_class, start_date)

        if resp.status_code != 200:
            raise RuntimeError(f"ICBC availability query failed (HTTP {resp.status_code}): {resp.text[:300]}")

        data = resp.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("appointments", "availableAppointments", "data", "results"):
                if isinstance(data.get(key), list):
                    return data[key]
        return []
