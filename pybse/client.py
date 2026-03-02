"""
pybse.client
============
Top-level BSE client that orchestrates authentication and API calls.

Usage:
    from pybse.client import BSEClient, BSECredentials

    creds = BSECredentials(
        user_id=os.environ["BSE_USER_ID"],
        member_code=os.environ["BSE_MEMBER_CODE"],
        password=os.environ["BSE_PASSWORD"],
        base_url=os.environ["BSE_BASE_URL"],
    )

    with BSEClient(creds) as client:
        client.onboard_investor(profile)
"""

from __future__ import annotations

from dataclasses import dataclass

from pybse.exceptions import BSEApiError  # noqa: F401 — re-exported for callers
from pybse.http.rest import BSERestClient
from pybse.models.investor import InvestorProfile
from pybse.models.serializer import build_fatca_param, build_ucc_param

_UCC_PATH = "/BSEMFWEBAPI/UCCAPI/UCCRegistrationV183"
_FATCA_PATH = "/BSEMFWEBAPI/UCCAPI/FATCADetailsV2"
_REGN_TYPE = "NEW"


@dataclass(frozen=True)
class BSECredentials:
    user_id: str
    member_code: str
    password: str
    base_url: str


class BSEClient:
    """Public-facing BSE client. Use as a context manager to ensure the
    underlying HTTP connection is closed cleanly."""

    def __init__(self, credentials: BSECredentials) -> None:
        self._rest = BSERestClient(
            user_id=credentials.user_id,
            member_code=credentials.member_code,
            password=credentials.password,
            base_url=credentials.base_url,
        )

    def register_investor(self, profile: InvestorProfile) -> None:
        """POST to UCCRegistrationV183.

        Raises:
            BSEApiError: on any transport failure or BSE-level error.
        """
        self._rest.post(
            _UCC_PATH,
            {
                "RegnType": _REGN_TYPE,
                "Param": build_ucc_param(profile),
            },
        )

    def upload_fatca(self, profile: InvestorProfile) -> None:
        """POST FATCA details for an already-registered investor.

        Raises:
            BSEApiError: on any transport failure or BSE-level error.
        """
        self._rest.post(
            _FATCA_PATH,
            {"Param": build_fatca_param(profile)},
        )

    def onboard_investor(self, profile: InvestorProfile) -> None:
        """Register investor then upload FATCA in one call.

        If FATCA fails after UCC registration succeeds, the UCC is already
        committed — this method does NOT retry UCC. The BSEApiError from FATCA
        propagates as-is so the caller can handle partial success.
        """
        self.register_investor(profile)
        self.upload_fatca(profile)

    def close(self) -> None:
        self._rest.close()

    def __enter__(self) -> BSEClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
