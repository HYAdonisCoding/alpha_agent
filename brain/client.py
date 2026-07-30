"""
WorldQuant BRAIN Client
=======================
Interface for interacting with the WorldQuant BRAIN platform.

Handles:
- Authentication
- Data fetching
- Alpha submission
- Simulation requests

Note: Requires valid WorldQuant BRAIN credentials.
"""

import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)


@dataclass
class BrainConfig:
    """BRAIN platform configuration."""

    api_base: str = "https://api.worldquantbrain.com"
    username: Optional[str] = None
    password: Optional[str] = None
    max_retries: int = 3
    retry_delay: float = 2.0
    max_submissions_per_day: int = 10


class BrainClient:
    """
    Client for WorldQuant BRAIN platform.

    Usage:
        client = BrainClient(username="...", password="...")
        client.authenticate()
        datasets = client.list_datasets()
    """

    def __init__(self, config: Optional[BrainConfig] = None):
        self.config = config or BrainConfig()
        self.session = requests.Session()
        self._authenticated = False
        self._submission_count = 0
        self._submission_date = None

    def authenticate(self) -> bool:
        """
        Authenticate with BRAIN platform.

        Returns True if successful.
        """
        if not self.config.username or not self.config.password:
            logger.warning(
                "BRAIN credentials not configured. "
                "Set username/password in config or environment."
            )
            return False

        try:
            # WorldQuant BRAIN authentication flow
            auth_url = f"{self.config.api_base}/authentication"
            response = self.session.post(
                auth_url,
                json={
                    "username": self.config.username,
                    "password": self.config.password,
                },
                timeout=30,
            )
            response.raise_for_status()
            self._authenticated = True
            logger.info("BRAIN authentication successful")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"BRAIN authentication failed: {e}")
            self._authenticated = False
            return False

    def list_datasets(self) -> List[Dict]:
        """List available datasets on BRAIN."""
        if not self._ensure_auth():
            return []

        try:
            url = f"{self.config.api_base}/data/datasets"
            response = self._retry_request("GET", url)
            if response:
                return response.json().get("datasets", [])
        except Exception as e:
            logger.error(f"Failed to list datasets: {e}")

        return []

    def get_data(
        self,
        dataset_id: str,
        fields: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Fetch data from a BRAIN dataset.

        Args:
            dataset_id: Dataset identifier
            fields: Data fields to fetch
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        """
        if not self._ensure_auth():
            return None

        try:
            url = f"{self.config.api_base}/data/datasets/{dataset_id}"
            params = {}
            if fields:
                params["fields"] = ",".join(fields)
            if start_date:
                params["start"] = start_date
            if end_date:
                params["end"] = end_date

            response = self._retry_request("GET", url, params=params)
            if response:
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get data from {dataset_id}: {e}")

        return None

    def submit_alpha(
        self,
        expression: str,
        settings: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Submit an alpha expression to BRAIN.

        Args:
            expression: Alpha factor expression
            settings: Simulation/alpha settings

        Returns:
            Response dict with submission ID and status
        """
        if not self._ensure_auth():
            return {"status": "error", "message": "Not authenticated"}

        # Check daily submission limit
        import datetime
        today = datetime.date.today().isoformat()
        if self._submission_date != today:
            self._submission_count = 0
            self._submission_date = today

        if self._submission_count >= self.config.max_submissions_per_day:
            return {
                "status": "error",
                "message": f"Daily submission limit reached "
                f"({self.config.max_submissions_per_day})",
            }

        try:
            url = f"{self.config.api_base}/alphas"
            payload = {
                "expression": expression,
                "settings": settings or {},
            }

            response = self._retry_request("POST", url, json=payload)
            if response:
                self._submission_count += 1
                logger.info(
                    f"Alpha submitted ({self._submission_count}/"
                    f"{self.config.max_submissions_per_day})"
                )
                return response.json()

        except Exception as e:
            logger.error(f"Alpha submission failed: {e}")

        return {"status": "error", "message": "Submission failed"}

    def check_alpha_status(self, alpha_id: str) -> Dict[str, Any]:
        """Check the status of a submitted alpha."""
        if not self._ensure_auth():
            return {"status": "error"}

        try:
            url = f"{self.config.api_base}/alphas/{alpha_id}"
            response = self._retry_request("GET", url)
            if response:
                return response.json()
        except Exception as e:
            logger.error(f"Failed to check alpha {alpha_id}: {e}")

        return {"status": "error"}

    def list_my_alphas(self, limit: int = 50) -> List[Dict]:
        """List the user's submitted alphas."""
        if not self._ensure_auth():
            return []

        try:
            url = f"{self.config.api_base}/alphas"
            params = {"limit": limit}
            response = self._retry_request("GET", url, params=params)
            if response:
                return response.json().get("alphas", [])
        except Exception as e:
            logger.error(f"Failed to list alphas: {e}")

        return []

    # ---- Internal ----

    def _ensure_auth(self) -> bool:
        """Ensure we're authenticated, try to auth if not."""
        if self._authenticated:
            return True
        return self.authenticate()

    def _retry_request(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> Optional[requests.Response]:
        """Make an HTTP request with retries."""
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.request(method, url, timeout=30, **kwargs)

                if response.status_code == 401:
                    logger.warning("BRAIN token expired, re-authenticating...")
                    self._authenticated = False
                    if not self.authenticate():
                        return None
                    # Retry with new auth
                    continue

                if response.status_code == 429:
                    wait = int(response.headers.get("Retry-After", self.config.retry_delay))
                    logger.warning(f"Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                logger.warning(f"BRAIN request attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))

        return None
