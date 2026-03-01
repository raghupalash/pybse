"""
tests.test_investor
===================
Tests for investor creation (UCC registration and FATCA upload).
"""

from __future__ import annotations

from datetime import date

import pytest

from pybse.exceptions import BSEValidationError
from pybse.models.enums import (
    AccountType,
    FATCATaxIDType,
    Gender,
    IncomeSlab,
    IndianState,
    NomineeIDType,
    NomineeRelation,
    OccupationCode,
    OccupationType,
    SourceOfWealth,
    TaxStatus,
)
from pybse.models.investor import (
    BankAccount,
    FATCADetails,
    InvestorProfile,
    Nominee,
    TaxResidence,
)

# ---------------------------------------------------------------------------
# Fixtures / factories
# ---------------------------------------------------------------------------


def _fatca() -> FATCADetails:
    return FATCADetails(
        place_of_birth="Mumbai",
        country_of_birth="IN",
        source_of_wealth=SourceOfWealth.SALARY,
        income_slab=IncomeSlab.ABOVE_5_LAC_UPTO_10_LAC,
        tax_residences=[
            TaxResidence(
                country_code="IN",
                tax_id_number="ABCDE1234F",
                tax_id_type=FATCATaxIDType.PAN,
            )
        ],
    )


def _bank(
    *, account_type: AccountType = AccountType.SAVINGS, is_default: bool = True
) -> BankAccount:
    return BankAccount(
        account_type=account_type,
        account_number="123456789012",
        ifsc="HDFC0001234",
        is_default=is_default,
    )


def _profile(**overrides: object) -> InvestorProfile:
    defaults: dict[str, object] = {
        "ucc": "TEST001",
        "first_name": "Ravi",
        "last_name": "Kumar",
        "tax_status": TaxStatus.INDIVIDUAL,
        "gender": Gender.MALE,
        "date_of_birth": date(1990, 6, 15),
        "pan": "ABCDE1234F",
        "occupation": OccupationCode.SERVICE,
        "email": "ravi@example.com",
        "phone": "9876543210",
        "address_line1": "123 Main Street",
        "city": "Mumbai",
        "state": IndianState.MAHARASHTRA,
        "pincode": "400001",
        "bank_accounts": [_bank()],
        "fatca": _fatca(),
    }
    defaults.update(overrides)
    return InvestorProfile(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_valid_investor_profile_constructs() -> None:
    profile = _profile()
    assert profile.ucc == "TEST001"
    assert profile.pan == "ABCDE1234F"
    assert profile.tax_status == TaxStatus.INDIVIDUAL


def test_profile_with_nominees() -> None:
    nominees = [
        Nominee(
            name="Priya Kumar",
            relation=NomineeRelation.SPOUSE,
            share_percentage=60,
            is_minor=False,
        ),
        Nominee(
            name="Arun Kumar",
            relation=NomineeRelation.SON,
            share_percentage=40,
            is_minor=False,
        ),
    ]
    profile = _profile(nominees=nominees)
    assert len(profile.nominees) == 2


def test_profile_with_multiple_bank_accounts() -> None:
    accounts = [
        _bank(is_default=True),
        BankAccount(
            account_type=AccountType.CURRENT,
            account_number="987654321",
            ifsc="ICIC0009999",
            is_default=False,
        ),
    ]
    profile = _profile(bank_accounts=accounts)
    assert len(profile.bank_accounts) == 2


# ---------------------------------------------------------------------------
# PAN validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_pan",
    [
        "ABCDE12345",  # last char not alpha
        "abcde1234f",  # lowercase
        "ABCD1234F",  # too short
        "ABCDE12345F",  # too long
        "1BCDE1234F",  # first char not alpha
        "",
    ],
)
def test_invalid_pan_raises(bad_pan: str) -> None:
    with pytest.raises(BSEValidationError, match="PAN"):
        _profile(pan=bad_pan)


def test_valid_pan_accepted() -> None:
    _profile(pan="ABCDE1234F")  # no error


# ---------------------------------------------------------------------------
# IFSC validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_ifsc",
    [
        "HDfC0001234",  # lowercase
        "HDFC1001234",  # 5th char not '0'
        "HDC0001234",  # too short prefix
        "HDFC000123",  # too short suffix
        "",
    ],
)
def test_invalid_ifsc_raises(bad_ifsc: str) -> None:
    with pytest.raises(BSEValidationError, match="IFSC"):
        BankAccount(
            account_type=AccountType.SAVINGS,
            account_number="123456",
            ifsc=bad_ifsc,
            is_default=True,
        )


def test_valid_ifsc_accepted() -> None:
    BankAccount(
        account_type=AccountType.SAVINGS,
        account_number="123456",
        ifsc="HDFC0001234",
        is_default=True,
    )


# ---------------------------------------------------------------------------
# Pincode validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_pin",
    ["12345", "1234567", "ABCDEF", ""],
)
def test_invalid_pincode_raises(bad_pin: str) -> None:
    with pytest.raises(BSEValidationError, match="pincode"):
        _profile(pincode=bad_pin)


# ---------------------------------------------------------------------------
# v1 gates
# ---------------------------------------------------------------------------


def test_non_individual_tax_status_raises() -> None:
    with pytest.raises(BSEValidationError, match="tax_status"):
        _profile(tax_status=TaxStatus.NRI_OTHERS)


def test_nre_account_type_raises() -> None:
    with pytest.raises(BSEValidationError, match="account_type"):
        _bank(account_type=AccountType.NRE)


def test_nro_account_type_raises() -> None:
    with pytest.raises(BSEValidationError, match="account_type"):
        _bank(account_type=AccountType.NRO)


# ---------------------------------------------------------------------------
# Nominee rules
# ---------------------------------------------------------------------------


def test_more_than_3_nominees_raises() -> None:
    nominees = [
        Nominee(
            name=f"Nominee {i}",
            relation=NomineeRelation.OTHERS,
            share_percentage=25,
            is_minor=False,
        )
        for i in range(4)
    ]
    with pytest.raises(BSEValidationError, match="3 nominees"):
        _profile(nominees=nominees)


def test_nominee_shares_not_summing_to_100_raises() -> None:
    nominees = [
        Nominee(
            name="A",
            relation=NomineeRelation.SPOUSE,
            share_percentage=60,
            is_minor=False,
        ),
        Nominee(
            name="B", relation=NomineeRelation.SON, share_percentage=30, is_minor=False
        ),
    ]
    with pytest.raises(BSEValidationError, match="sum to 100"):
        _profile(nominees=nominees)


def test_single_nominee_100_percent_accepted() -> None:
    nominees = [
        Nominee(
            name="Priya",
            relation=NomineeRelation.SPOUSE,
            share_percentage=100,
            is_minor=False,
        )
    ]
    _profile(nominees=nominees)  # no error


def test_empty_nominees_accepted() -> None:
    _profile(nominees=[])  # opt-out of nomination


# ---------------------------------------------------------------------------
# OccupationType.from_occupation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "occ,expected",
    [
        (OccupationCode.BUSINESS, OccupationType.BUSINESS),
        (OccupationCode.FOREX_DEALER, OccupationType.BUSINESS),
        (OccupationCode.SERVICE, OccupationType.SERVICE),
        (OccupationCode.PROFESSIONAL, OccupationType.SERVICE),
        (OccupationCode.DOCTOR, OccupationType.SERVICE),
        (OccupationCode.PRIVATE_SECTOR_SERVICE, OccupationType.SERVICE),
        (OccupationCode.PUBLIC_SECTOR_SERVICE, OccupationType.SERVICE),
        (OccupationCode.GOVERNMENT_SERVICE, OccupationType.SERVICE),
        (OccupationCode.AGRICULTURE, OccupationType.OTHERS),
        (OccupationCode.RETIRED, OccupationType.OTHERS),
        (OccupationCode.HOUSEWIFE, OccupationType.OTHERS),
        (OccupationCode.STUDENT, OccupationType.OTHERS),
        (OccupationCode.OTHERS, OccupationType.OTHERS),
        (OccupationCode.UNKNOWN, OccupationType.OTHERS),
    ],
)
def test_occupation_type_from_occupation(
    occ: OccupationCode, expected: OccupationType
) -> None:
    assert OccupationType.from_occupation(occ) == expected


# ---------------------------------------------------------------------------
# Bank account cardinality
# ---------------------------------------------------------------------------


def test_no_bank_accounts_raises() -> None:
    with pytest.raises(BSEValidationError, match="at least one"):
        _profile(bank_accounts=[])


def test_more_than_5_bank_accounts_raises() -> None:
    accounts = [
        BankAccount(
            account_type=AccountType.SAVINGS,
            account_number=f"ACC{i}",
            ifsc="HDFC0001234",
            is_default=(i == 0),
        )
        for i in range(6)
    ]
    with pytest.raises(BSEValidationError, match="5 bank accounts"):
        _profile(bank_accounts=accounts)


def test_no_default_bank_account_raises() -> None:
    accounts = [
        _bank(is_default=False),
        BankAccount(
            account_type=AccountType.SAVINGS,
            account_number="999",
            ifsc="ICIC0000001",
            is_default=False,
        ),
    ]
    with pytest.raises(BSEValidationError, match="default"):
        _profile(bank_accounts=accounts)


def test_multiple_default_bank_accounts_raises() -> None:
    accounts = [_bank(is_default=True), _bank(is_default=True)]
    with pytest.raises(BSEValidationError, match="default"):
        _profile(bank_accounts=accounts)


# ---------------------------------------------------------------------------
# Nominee ID
# ---------------------------------------------------------------------------


def test_nominee_id_type_without_id_number_raises() -> None:
    with pytest.raises(BSEValidationError, match="id_number"):
        Nominee(
            name="Priya",
            relation=NomineeRelation.SPOUSE,
            share_percentage=100,
            is_minor=False,
            id_type=NomineeIDType.AADHAAR,
            id_number="",
        )


def test_nominee_with_id_type_and_number_accepted() -> None:
    Nominee(
        name="Priya",
        relation=NomineeRelation.SPOUSE,
        share_percentage=100,
        is_minor=False,
        id_type=NomineeIDType.AADHAAR,
        id_number="1234",
    )


# ---------------------------------------------------------------------------
# Enums work as plain strings
# ---------------------------------------------------------------------------


def test_enum_members_work_as_strings() -> None:
    assert str(TaxStatus.INDIVIDUAL) == "01"
    assert str(Gender.MALE) == "M"
    assert str(AccountType.SAVINGS) == "SB"
    assert f"{OccupationCode.SERVICE}" == "02"
