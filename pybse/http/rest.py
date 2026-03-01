"""
pybse.http.rest
===============
REST HTTP client using httpx for BSE STAR MF REST APIs.

Responsibilities:
- Hold credentials and inject them into every request body.
- Make POST calls to BSE REST endpoints.
- Translate HTTP transport failures into BSEApiError.
- Translate BSE-level failures (Status != "0") into typed exceptions.

BSE error codes are handled empirically — only what's been confirmed through
testing is mapped. Unknown codes fall through to BSEUnknownError.
"""

from __future__ import annotations

import httpx

from pybse.exceptions import BSEApiError, BSEUnknownError


class BSERestClient:
    """Low-level BSE REST transport. One instance per set of credentials."""

    def __init__(
        self,
        user_id: str,
        member_code: str,
        password: str,
        base_url: str,
    ) -> None:
        self._credentials: dict[str, str] = {
            "UserId": user_id,
            "MemberCode": member_code,
            "Password": password,
        }
        self._base_url = base_url.rstrip("/")
        self._http = httpx.Client(timeout=30.0)

    def post(self, path: str, body: dict[str, str]) -> dict[str, object]:
        """POST to a BSE endpoint.

        Credentials are injected automatically — callers only supply the
        call-specific fields (e.g. RegnType, Param).

        Raises:
            BSEApiError: HTTP transport failure or HTTP 4xx/5xx.
            BSEUnknownError: BSE returned Status != "0" with no typed mapping.
        """
        full_body = {**self._credentials, **body}
        url = f"{self._base_url}{path}"

        try:
            response = self._http.post(url, json=full_body)
        except httpx.TimeoutException as exc:
            raise BSEApiError(f"Request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise BSEApiError(f"Network error: {exc}") from exc

        if response.is_error:
            raise BSEApiError(f"HTTP {response.status_code}: {response.text}")

        data: dict[str, object] = response.json()
        status = str(data.get("Status", ""))
        remarks = str(data.get("Remarks", ""))

        if status != "0":
            raise BSEUnknownError(code=status, message=remarks)

        return data

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> BSERestClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
