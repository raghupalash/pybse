"""
tests.conftest
==============
Shared fixtures for all test modules.
"""

from __future__ import annotations

from datetime import date

import pytest

from pybse.client import BSECredentials
from pybse.models.enums import (
    AccountType,
    FATCATaxIDType,
    Gender,
    IncomeSlab,
    IndianState,
    NomineeRelation,
    OccupationCode,
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


@pytest.fixture
def sample_profile() -> InvestorProfile:
    return InvestorProfile(
        ucc="TEST001",
        first_name="Arjun",
        last_name="Sharma",
        tax_status=TaxStatus.INDIVIDUAL,
        gender=Gender.MALE,
        date_of_birth=date(1990, 6, 15),
        pan="ABCDE1234F",
        occupation=OccupationCode.SERVICE,
        email="arjun@example.com",
        phone="9876543210",
        address_line1="12 MG Road",
        city="Mumbai",
        state=IndianState.MAHARASHTRA,
        pincode="400001",
        bank_accounts=[
            BankAccount(
                account_type=AccountType.SAVINGS,
                account_number="123456789012",
                ifsc="HDFC0001234",
                is_default=True,
            )
        ],
        fatca=FATCADetails(
            place_of_birth="Mumbai",
            country_of_birth="IN",
            source_of_wealth=SourceOfWealth.SALARY,
            income_slab=IncomeSlab.ABOVE_1_LAC_UPTO_5_LAC,
            tax_residences=[
                TaxResidence(
                    country_code="IN",
                    tax_id_number="ABCDE1234F",
                    tax_id_type=FATCATaxIDType.PAN,
                )
            ],
        ),
    )


@pytest.fixture
def sample_profile_with_nominees(sample_profile: InvestorProfile) -> InvestorProfile:
    """Profile with two nominees summing to 100%."""
    from dataclasses import replace

    return replace(
        sample_profile,
        nominees=[
            Nominee(
                name="Priya Sharma",
                relation=NomineeRelation.SPOUSE,
                share_percentage=60,
                is_minor=False,
            ),
            Nominee(
                name="Rahul Sharma",
                relation=NomineeRelation.SON,
                share_percentage=40,
                is_minor=False,
            ),
        ],
    )


@pytest.fixture
def credentials() -> BSECredentials:
    return BSECredentials(
        user_id="TESTUSER",
        member_code="10000",
        password="testpass",
        base_url="https://bsemf-uat.example.com",
    )
