"""
tests.test_client
=================
Tests for BSEClient — register_investor, upload_fatca, onboard_investor.

Uses pytest-httpx to mock all HTTP calls. No real BSE API calls ever made.
"""

from __future__ import annotations

import json

import httpx
import pytest
from pytest_httpx import HTTPXMock

from pybse.client import BSEClient, BSECredentials
from pybse.exceptions import BSEApiError, BSEUnknownError
from pybse.models.investor import InvestorProfile

_SUCCESS = {"Status": "0", "Remarks": "SAVE SUCCESSFULLY"}


# ---------------------------------------------------------------------------
# register_investor — happy path
# ---------------------------------------------------------------------------


def test_register_investor_success(
    httpx_mock: HTTPXMock,
    sample_profile: InvestorProfile,
    credentials: BSECredentials,
) -> None:
    httpx_mock.add_response(json=_SUCCESS)
    BSEClient(credentials).register_investor(sample_profile)  # must not raise


# ---------------------------------------------------------------------------
# register_investor — BSE-level errors
# ---------------------------------------------------------------------------


def test_register_investor_bse_error_raises(
    httpx_mock: HTTPXMock,
    sample_profile: InvestorProfile,
    credentials: BSECredentials,
) -> None:
    httpx_mock.add_response(json={"Status": "101", "Remarks": "INVALID PAN"})
    with pytest.raises(BSEUnknownError) as exc_info:
        BSEClient(credentials).register_investor(sample_profile)
    assert exc_info.value.code == "101"
    assert "INVALID PAN" in exc_info.value.message


def test_register_investor_non_zero_status_raises(
    httpx_mock: HTTPXMock,
    sample_profile: InvestorProfile,
    credentials: BSECredentials,
) -> None:
    """Any non-zero Status must raise — even Status '1'."""
    httpx_mock.add_response(json={"Status": "1", "Remarks": "FAILURE"})
    with pytest.raises(BSEUnknownError):
        BSEClient(credentials).register_investor(sample_profile)


# ---------------------------------------------------------------------------
# register_investor — HTTP / transport errors
# ---------------------------------------------------------------------------


def test_register_investor_http_500_raises(
    httpx_mock: HTTPXMock,
    sample_profile: InvestorProfile,
    credentials: BSECredentials,
) -> None:
    httpx_mock.add_response(status_code=500, text="Internal Server Error")
    with pytest.raises(BSEApiError):
        BSEClient(credentials).register_investor(sample_profile)


def test_register_investor_http_401_raises(
    httpx_mock: HTTPXMock,
    sample_profile: InvestorProfile,
    credentials: BSECredentials,
) -> None:
    httpx_mock.add_response(status_code=401, text="Unauthorized")
    with pytest.raises(BSEApiError):
        BSEClient(credentials).register_investor(sample_profile)


def test_register_investor_timeout_raises(
    httpx_mock: HTTPXMock,
    sample_profile: InvestorProfile,
    credentials: BSECredentials,
) -> None:
    httpx_mock.add_exception(httpx.ReadTimeout("timed out"))
    with pytest.raises(BSEApiError):
        BSEClient(credentials).register_investor(sample_profile)


def test_register_investor_network_error_raises(
    httpx_mock: HTTPXMock,
    sample_profile: InvestorProfile,
    credentials: BSECredentials,
) -> None:
    httpx_mock.add_exception(httpx.ConnectError("connection refused"))
    with pytest.raises(BSEApiError):
        BSEClient(credentials).register_investor(sample_profile)


# ---------------------------------------------------------------------------
# register_investor — request shape
# ---------------------------------------------------------------------------


def test_register_investor_sends_correct_fields(
    httpx_mock: HTTPXMock,
    sample_profile: InvestorProfile,
    credentials: BSECredentials,
) -> None:
    """Request body must include credentials, RegnType=NEW, and a 183-field Param."""
    httpx_mock.add_response(json=_SUCCESS)
    BSEClient(credentials).register_investor(sample_profile)

    payload = json.loads(httpx_mock.get_requests()[0].read())

    assert payload["UserId"] == credentials.user_id
    assert payload["MemberCode"] == credentials.member_code
    assert payload["Password"] == credentials.password
    assert payload["RegnType"] == "NEW"
    assert "|" in payload["Param"]
    assert len(payload["Param"].split("|")) == 183


# ---------------------------------------------------------------------------
# upload_fatca — happy path
# ---------------------------------------------------------------------------


def test_upload_fatca_success(
    httpx_mock: HTTPXMock,
    sample_profile: InvestorProfile,
    credentials: BSECredentials,
) -> None:
    httpx_mock.add_response(json=_SUCCESS)
    BSEClient(credentials).upload_fatca(sample_profile)  # must not raise


def test_upload_fatca_bse_error_raises(
    httpx_mock: HTTPXMock,
    sample_profile: InvestorProfile,
    credentials: BSECredentials,
) -> None:
    httpx_mock.add_response(json={"Status": "202", "Remarks": "FATCA ERROR"})
    with pytest.raises(BSEUnknownError) as exc_info:
        BSEClient(credentials).upload_fatca(sample_profile)
    assert exc_info.value.code == "202"


# ---------------------------------------------------------------------------
# onboard_investor — two-call flow
# ---------------------------------------------------------------------------


def test_onboard_investor_makes_two_requests(
    httpx_mock: HTTPXMock,
    sample_profile: InvestorProfile,
    credentials: BSECredentials,
) -> None:
    httpx_mock.add_response(json=_SUCCESS)  # UCC
    httpx_mock.add_response(json=_SUCCESS)  # FATCA
    BSEClient(credentials).onboard_investor(sample_profile)
    assert len(httpx_mock.get_requests()) == 2


def test_onboard_investor_fatca_failure_does_not_retry_ucc(
    httpx_mock: HTTPXMock,
    sample_profile: InvestorProfile,
    credentials: BSECredentials,
) -> None:
    """FATCA failure propagates; UCC is not retried — exactly 2 calls total."""
    httpx_mock.add_response(json=_SUCCESS)
    httpx_mock.add_response(json={"Status": "202", "Remarks": "FATCA ERROR"})

    with pytest.raises(BSEUnknownError) as exc_info:
        BSEClient(credentials).onboard_investor(sample_profile)

    assert exc_info.value.code == "202"
    assert len(httpx_mock.get_requests()) == 2


def test_onboard_investor_ucc_failure_skips_fatca(
    httpx_mock: HTTPXMock,
    sample_profile: InvestorProfile,
    credentials: BSECredentials,
) -> None:
    """If UCC fails, FATCA must not be called."""
    httpx_mock.add_response(json={"Status": "1", "Remarks": "UCC FAILED"})

    with pytest.raises(BSEUnknownError):
        BSEClient(credentials).onboard_investor(sample_profile)

    assert len(httpx_mock.get_requests()) == 1
