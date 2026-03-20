"""
LexiScan — Frontend API Client
Wraps all backend API calls with error handling.
"""

import os
from typing import Any, Dict, List, Optional

import requests
from loguru import logger

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class APIClient:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _get(self, path: str, params: dict = None) -> Dict:
        url = f"{self.base}{path}"
        try:
            r = self.session.get(url, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except requests.ConnectionError:
            raise ConnectionError(f"Cannot reach LexiScan API at {self.base}. Is the backend running?")
        except requests.HTTPError as e:
            raise RuntimeError(f"API error {e.response.status_code}: {e.response.text}")

    def _post(self, path: str, json: dict = None, files: dict = None, data: dict = None) -> Dict:
        url = f"{self.base}{path}"
        try:
            r = self.session.post(url, json=json, files=files, data=data, timeout=300)
            r.raise_for_status()
            return r.json()
        except requests.ConnectionError:
            raise ConnectionError(f"Cannot reach LexiScan API at {self.base}.")
        except requests.HTTPError as e:
            raise RuntimeError(f"API error {e.response.status_code}: {e.response.text}")

    def _delete(self, path: str) -> None:
        url = f"{self.base}{path}"
        r = self.session.delete(url, timeout=30)
        r.raise_for_status()

    # ── Contract Endpoints ────────────────────────────────────

    def analyze_contract(self, file_bytes: bytes, filename: str, contract_name: str = None) -> Dict:
        """Upload and analyze a contract PDF."""
        files = {"file": (filename, file_bytes, "application/pdf")}
        data = {}
        if contract_name:
            data["contract_name"] = contract_name
        return self._post("/api/v1/contracts/analyze", files=files, data=data)

    def list_contracts(self, skip: int = 0, limit: int = 50) -> List[Dict]:
        """List all contracts."""
        return self._get("/api/v1/contracts/", params={"skip": skip, "limit": limit})

    def get_contract(self, contract_id: str) -> Dict:
        """Get contract metadata."""
        return self._get(f"/api/v1/contracts/{contract_id}")

    def get_analysis(self, contract_id: str, risk_level: str = None) -> Dict:
        """Get full analysis including clauses and entities."""
        params = {}
        if risk_level:
            params["risk_level"] = risk_level
        return self._get(f"/api/v1/contracts/{contract_id}/analysis", params=params)

    def get_clauses(
        self,
        contract_id: str,
        risk_level: str = None,
        flagged_only: bool = False,
    ) -> List[Dict]:
        """Get clauses with optional filters."""
        params = {"flagged_only": flagged_only}
        if risk_level:
            params["risk_level"] = risk_level
        return self._get(f"/api/v1/contracts/{contract_id}/clauses", params=params)

    def compare_contracts(self, contract_id_1: str, contract_id_2: str) -> Dict:
        """Compare two contracts."""
        return self._post(
            "/api/v1/contracts/compare",
            json={"contract_id_1": contract_id_1, "contract_id_2": contract_id_2},
        )

    def delete_contract(self, contract_id: str) -> None:
        """Delete a contract."""
        self._delete(f"/api/v1/contracts/{contract_id}")

    def health_check(self) -> Dict:
        """Check backend health."""
        return self._get("/api/v1/health")


# Singleton
_client: Optional[APIClient] = None


def get_client() -> APIClient:
    global _client
    if _client is None:
        _client = APIClient()
    return _client
