"""
pybse.models.investor
=====================
Dataclass models for investor (UCC) creation and FATCA upload.

All fields the caller must supply are represented here. Protocol constants
(HOLDING, CLIENT_TYPE, etc.) are NOT fields — the serialiser writes them.

Non-editable after BSE registration: first_name, last_name, middle_name,
pan, date_of_birth, tax_status.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from pybse.exceptions import BSEValidationError
from pybse.models.enums import (
    AccountType,
    FATCAAddressType,
    FATCATaxIDType,
    Gender,
    IncomeSlab,
    IndianState,
    KYCType,
    NomineeIDType,
    NomineeRelation,
    OccupationCode,
    PaperlessFlag,
    SourceOfWealth,
    TaxStatus,
)

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
_PINCODE_RE = re.compile(r"^\d{6}$")
_IFSC_RE = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
_PHONE_RE = re.compile(r"^\d{10}$")
_MICR_RE = re.compile(r"^\d{9}$")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise BSEValidationError(message)


# ---------------------------------------------------------------------------
# TaxResidence
# ---------------------------------------------------------------------------


@dataclass
class TaxResidence:
    """One entry in the FATCA tax residence list.

    For a Resident Indian with no foreign ties, there should be a single
    entry with country_code="IN".
    """

    country_code: str  # ISO 3166-1 alpha-2, e.g. "IN"
    tax_id_number: str
    tax_id_type: FATCATaxIDType

    def __post_init__(self) -> None:
        _require(
            len(self.country_code) == 2 and self.country_code.isalpha(),
            "country_code must be a 2-letter ISO 3166-1 alpha-2 code",
        )
        _require(
            len(self.tax_id_number) <= 25,
            "tax_id_number must be at most 25 characters",
        )


# ---------------------------------------------------------------------------
# FATCADetails
# ---------------------------------------------------------------------------


@dataclass
class FATCADetails:
    """FATCA-specific fields uploaded in the second API call."""

    place_of_birth: str
    country_of_birth: str  # ISO 3166-1 alpha-2
    source_of_wealth: SourceOfWealth
    income_slab: IncomeSlab
    tax_residences: list[TaxResidence] = field(default_factory=list)
    address_type: FATCAAddressType = FATCAAddressType.RESIDENTIAL

    def __post_init__(self) -> None:
        _require(
            len(self.place_of_birth) <= 50,
            "place_of_birth must be at most 50 characters",
        )
        _require(
            len(self.country_of_birth) == 2 and self.country_of_birth.isalpha(),
            "country_of_birth must be a 2-letter ISO 3166-1 alpha-2 code",
        )
        _require(
            len(self.tax_residences) <= 4,
            "tax_residences may have at most 4 entries",
        )


# ---------------------------------------------------------------------------
# BankAccount
# ---------------------------------------------------------------------------


@dataclass
class BankAccount:
    """One bank account linked to the investor.

    v1 gate: account_type must be SAVINGS or CURRENT.
    """

    account_type: AccountType
    account_number: str
    ifsc: str
    is_default: bool
    micr: str = ""

    def __post_init__(self) -> None:
        _require(
            self.account_type in (AccountType.SAVINGS, AccountType.CURRENT),
            f"account_type {self.account_type!r} is not supported in v1; "
            "use SAVINGS or CURRENT",
        )
        _require(
            len(self.account_number) <= 40,
            "account_number must be at most 40 characters",
        )
        _require(
            bool(_IFSC_RE.match(self.ifsc)),
            f"IFSC {self.ifsc!r} is invalid; "
            "expected format: 4 alpha + '0' + 6 alphanumeric",
        )
        if self.micr:
            _require(
                bool(_MICR_RE.match(self.micr)),
                f"MICR {self.micr!r} is invalid; must be exactly 9 digits",
            )


# ---------------------------------------------------------------------------
# Nominee
# ---------------------------------------------------------------------------


@dataclass
class Nominee:
    """One nominee for the investor."""

    name: str
    relation: NomineeRelation
    share_percentage: int
    is_minor: bool
    id_type: NomineeIDType | None = None
    id_number: str = ""

    def __post_init__(self) -> None:
        _require(len(self.name) <= 40, "nominee name must be at most 40 characters")
        _require(
            1 <= self.share_percentage <= 100,
            f"share_percentage must be between 1 and 100, got {self.share_percentage}",
        )
        if self.id_type is not None:
            _require(
                bool(self.id_number),
                "id_number is required when id_type is set",
            )


# ---------------------------------------------------------------------------
# InvestorProfile
# ---------------------------------------------------------------------------


@dataclass
class InvestorProfile:
    """Single source of truth for all three investor onboarding API calls.

    v1 gate: tax_status must be TaxStatus.INDIVIDUAL.

    Non-editable after BSE registration:
        first_name, last_name, middle_name, pan, date_of_birth, tax_status
    """

    # Identity
    ucc: str
    first_name: str
    last_name: str
    tax_status: TaxStatus
    gender: Gender
    date_of_birth: date
    pan: str
    occupation: OccupationCode

    # Contact
    email: str
    phone: str

    # Address
    address_line1: str
    city: str
    state: IndianState
    pincode: str

    # Bank
    bank_accounts: list[BankAccount]

    # FATCA
    fatca: FATCADetails

    # Optional
    middle_name: str = ""
    address_line2: str = ""
    address_line3: str = ""
    nominees: list[Nominee] = field(default_factory=list)
    kyc_type: KYCType = KYCType.KRA_COMPLIANT
    paperless_flag: PaperlessFlag = PaperlessFlag.EKYC

    def __post_init__(self) -> None:
        # v1 gate
        _require(
            self.tax_status == TaxStatus.INDIVIDUAL,
            f"tax_status {self.tax_status!r} is not supported in v1; "
            "only TaxStatus.INDIVIDUAL is allowed",
        )

        # UCC
        _require(len(self.ucc) <= 10, "ucc must be at most 10 characters")
        _require(bool(self.ucc), "ucc is required")

        # Identity
        _require(bool(self.first_name), "first_name is required")
        _require(len(self.first_name) <= 70, "first_name must be at most 70 characters")
        _require(
            len(self.middle_name) <= 70, "middle_name must be at most 70 characters"
        )
        _require(len(self.last_name) <= 70, "last_name must be at most 70 characters")

        _require(
            bool(_PAN_RE.match(self.pan)),
            f"PAN {self.pan!r} is invalid; "
            "expected format: 5 uppercase letters + 4 digits + 1 uppercase letter",
        )

        # Contact
        _require(len(self.email) <= 50, "email must be at most 50 characters")
        _require(
            bool(_PHONE_RE.match(self.phone)),
            f"phone {self.phone!r} is invalid; must be exactly 10 digits",
        )

        # Address
        _require(bool(self.address_line1), "address_line1 is required")
        _require(
            len(self.address_line1) <= 40,
            "address_line1 must be at most 40 characters",
        )
        _require(
            len(self.address_line2) <= 40,
            "address_line2 must be at most 40 characters",
        )
        _require(
            len(self.address_line3) <= 40,
            "address_line3 must be at most 40 characters",
        )
        _require(len(self.city) <= 35, "city must be at most 35 characters")
        _require(
            bool(_PINCODE_RE.match(self.pincode)),
            f"pincode {self.pincode!r} is invalid; must be exactly 6 digits",
        )

        # Bank accounts
        _require(
            len(self.bank_accounts) >= 1,
            "at least one bank account is required",
        )
        _require(
            len(self.bank_accounts) <= 5,
            f"at most 5 bank accounts are supported; got {len(self.bank_accounts)}",
        )
        default_count = sum(1 for a in self.bank_accounts if a.is_default)
        _require(
            default_count == 1,
            "exactly one bank account must be marked as default; "
            f"found {default_count}",
        )

        # Nominees
        _require(
            len(self.nominees) <= 3,
            f"at most 3 nominees are allowed; got {len(self.nominees)}",
        )
        if self.nominees:
            total_share = sum(n.share_percentage for n in self.nominees)
            _require(
                total_share == 100,
                f"nominee share percentages must sum to 100; got {total_share}",
            )
