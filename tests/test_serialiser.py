"""
tests.test_serialiser
=====================
Tests for UCC and FATCA wire payload builders.

Field positions are 1-indexed in BSE's spec; Python list indices are
0-indexed (field N → index N-1).
"""

from __future__ import annotations

import re
from datetime import date

from pybse.models.enums import (
    AccountType,
    FATCATaxIDType,
    Gender,
    IncomeSlab,
    IndianState,
    OccupationCode,
    SourceOfWealth,
    TaxStatus,
)
from pybse.models.investor import (
    BankAccount,
    FATCADetails,
    InvestorProfile,
    TaxResidence,
)
from pybse.models.serializer import build_fatca_param, build_ucc_param

# ---------------------------------------------------------------------------
# UCC — field count
# ---------------------------------------------------------------------------


def test_ucc_param_field_count(sample_profile: InvestorProfile) -> None:
    fields = build_ucc_param(sample_profile).split("|")
    assert len(fields) == 183


# ---------------------------------------------------------------------------
# UCC — spot checks on protocol constants and key profile values
# ---------------------------------------------------------------------------


def test_ucc_param_spot_checks(sample_profile: InvestorProfile) -> None:
    fields = build_ucc_param(sample_profile).split("|")

    assert fields[0] == sample_profile.ucc  # f1  UCC
    assert fields[4] == "01"  # f5  TAX_STATUS
    assert fields[8] == "SI"  # f9  HOLDING
    assert fields[21] == "N"  # f22 PAN_EXEMPT
    assert fields[25] == sample_profile.pan  # f26 PAN
    assert fields[33] == "P"  # f34 CLIENT_TYPE
    assert fields[41] == "SB"  # f42 ACCOUNT_TYPE
    assert fields[45] == "Y"  # f46 DEFAULT_BANK
    assert fields[67] == "02"  # f68 DIV_PAY_MODE
    assert fields[74] == "India"  # f75 COUNTRY
    assert fields[79] == sample_profile.email  # f80 EMAIL
    assert fields[80] == "E"  # f81 COMM_MODE
    assert fields[92] == sample_profile.phone  # f93 INDIAN_MOB_NO
    assert fields[93] == "K"  # f94 KYC_TYPE
    assert fields[107] == "Z"  # f108 PAPERLESS_FLAG
    assert fields[110] == "SE"  # f111 MOBILE_DECLARATION
    assert fields[111] == "SE"  # f112 EMAIL_DECLARATION
    assert fields[121] == "N"  # f122 NOMINATION_OPT (no nominees)
    assert fields[174] == "N"  # f175 NOM_SOA


def test_ucc_param_nomination_opt_with_nominees(
    sample_profile_with_nominees: InvestorProfile,
) -> None:
    fields = build_ucc_param(sample_profile_with_nominees).split("|")
    assert fields[121] == "Y"  # f122 NOMINATION_OPT


# ---------------------------------------------------------------------------
# UCC — bank slot padding
# ---------------------------------------------------------------------------


def test_ucc_param_bank_padding_unused_slots(
    sample_profile: InvestorProfile,
) -> None:
    """One bank → slots 2–5 (fields 47–66, indices 46–65) are all empty."""
    fields = build_ucc_param(sample_profile).split("|")
    assert fields[46:66] == [""] * 20


def _make_minimal_profile(bank_accounts: list[BankAccount]) -> InvestorProfile:
    """Helper to build a valid InvestorProfile with custom bank accounts."""
    return InvestorProfile(
        ucc="TEST002",
        first_name="Test",
        last_name="User",
        tax_status=TaxStatus.INDIVIDUAL,
        gender=Gender.MALE,
        date_of_birth=date(1990, 1, 1),
        pan="ABCDE1234F",
        occupation=OccupationCode.SERVICE,
        email="test@example.com",
        phone="9876543210",
        address_line1="1 Test St",
        city="Delhi",
        state=IndianState.DELHI,
        pincode="110001",
        bank_accounts=bank_accounts,
        fatca=FATCADetails(
            place_of_birth="Delhi",
            country_of_birth="IN",
            source_of_wealth=SourceOfWealth.SALARY,
            income_slab=IncomeSlab.BELOW_1_LAC,
            tax_residences=[
                TaxResidence(
                    country_code="IN",
                    tax_id_number="ABCDE1234F",
                    tax_id_type=FATCATaxIDType.PAN,
                )
            ],
        ),
    )


def test_ucc_param_default_bank_sorted_first() -> None:
    """Default bank always lands in slot 1 regardless of input order."""
    non_default = BankAccount(
        account_type=AccountType.CURRENT,
        account_number="NONDEFAULT",
        ifsc="ICIC0009999",
        is_default=False,
    )
    default = BankAccount(
        account_type=AccountType.SAVINGS,
        account_number="DEFAULT001",
        ifsc="HDFC0001234",
        is_default=True,
    )
    # Non-default is first in the input list.
    profile = _make_minimal_profile([non_default, default])
    fields = build_ucc_param(profile).split("|")

    assert fields[41] == "SB"  # f42 ACCOUNT_TYPE  (default → slot 1)
    assert fields[42] == "DEFAULT001"  # f43 ACCOUNT_NO
    assert fields[45] == "Y"  # f46 DEFAULT_BANK
    assert fields[46] == "CB"  # f47 ACCOUNT_TYPE  (non-default → slot 2)
    assert fields[50] == "N"  # f51 DEFAULT_BANK


# ---------------------------------------------------------------------------
# UCC — nominee slots
# ---------------------------------------------------------------------------


def test_ucc_param_no_nominees_fields_are_empty(
    sample_profile: InvestorProfile,
) -> None:
    """With no nominees all 51 nominee sub-fields (fields 124–174) are empty."""
    fields = build_ucc_param(sample_profile).split("|")
    assert fields[123:174] == [""] * 51


def test_ucc_param_nominees_populated(
    sample_profile_with_nominees: InvestorProfile,
) -> None:
    fields = build_ucc_param(sample_profile_with_nominees).split("|")
    p = sample_profile_with_nominees

    # Slot 1 — first nominee (starts at index 123)
    assert fields[123] == p.nominees[0].name  # f124 NOMINEE_NAME
    assert fields[124] == str(p.nominees[0].relation)  # f125 NOMINEE_RELATION
    assert fields[125] == str(p.nominees[0].share_percentage)  # f126
    assert fields[126] == "N"  # f127 NOMINEE_MINOR_FLAG
    assert fields[132] == p.email  # f133 NOMINEE_EMAIL
    assert fields[133] == p.phone  # f134 NOMINEE_MOBILE
    assert fields[139] == "India"  # f140 NOMINEE_COUNTRY

    # Slot 2 — second nominee (starts at index 140, offsets same as slot 1)
    assert fields[140] == p.nominees[1].name  # f141 NOMINEE_NAME
    assert fields[142] == str(p.nominees[1].share_percentage)  # f143

    # Slot 3 — unused
    assert fields[157:174] == [""] * 17


# ---------------------------------------------------------------------------
# UCC — date format
# ---------------------------------------------------------------------------


def test_ucc_param_dob_format(sample_profile: InvestorProfile) -> None:
    """UCC date of birth must be DD/MM/YYYY."""
    fields = build_ucc_param(sample_profile).split("|")
    assert re.fullmatch(r"\d{2}/\d{2}/\d{4}", fields[6])
    assert fields[6] == "15/06/1990"  # 1990-06-15 → DD/MM/YYYY


# ---------------------------------------------------------------------------
# UCC — foreign address fields blank for Resident Indians
# ---------------------------------------------------------------------------


def test_ucc_param_foreign_address_blank(sample_profile: InvestorProfile) -> None:
    """Fields 82–92 (indices 81–91) must be empty for Resident Indians."""
    fields = build_ucc_param(sample_profile).split("|")
    assert fields[81:92] == [""] * 11


# ---------------------------------------------------------------------------
# FATCA — date format
# ---------------------------------------------------------------------------


def test_fatca_param_dob_format(sample_profile: InvestorProfile) -> None:
    """FATCA date of birth must be MM/DD/YYYY — different from UCC."""
    fields = build_fatca_param(sample_profile).split("|")
    assert re.fullmatch(r"\d{2}/\d{2}/\d{4}", fields[3])
    assert fields[3] == "06/15/1990"  # 1990-06-15 → MM/DD/YYYY


# ---------------------------------------------------------------------------
# FATCA — spot checks
# ---------------------------------------------------------------------------


def test_fatca_param_spot_checks(sample_profile: InvestorProfile) -> None:
    fields = build_fatca_param(sample_profile).split("|")

    assert fields[0] == sample_profile.pan  # f1  PAN_RP
    assert fields[2] == "Arjun Sharma"  # f3  INV_NAME
    assert fields[6] == "01"  # f7  TAX_STATUS
    assert fields[7] == "E"  # f8  DATA_SRC
    assert fields[10] == "IN"  # f11 CO_BIR_INC
    assert fields[11] == "IN"  # f12 TAX_RES1 country
    assert fields[13] == "D"  # f14 ID1_TYPE (PAN = "D")
    assert fields[25] == "N"  # f26 PEP_FLAG
    assert fields[26] == "02"  # f27 OCC_CODE
    assert fields[27] == "S"  # f28 OCC_TYPE (SERVICE → S)
    assert fields[28] == "O"  # f29 EXCH_NAME
    assert fields[32] == sample_profile.ucc  # f33 LOG_NAME


def test_fatca_param_tax_residence_padding(
    sample_profile: InvestorProfile,
) -> None:
    """Unused tax residence slots 2–4 (fields 15–23, indices 14–22) are empty."""
    fields = build_fatca_param(sample_profile).split("|")
    assert fields[14:23] == [""] * 9


def test_fatca_param_full_name_no_double_spaces(
    sample_profile: InvestorProfile,
) -> None:
    """Full name must not have extra spaces when middle_name is empty."""
    fields = build_fatca_param(sample_profile).split("|")
    assert fields[2] == "Arjun Sharma"
    assert "  " not in fields[2]
