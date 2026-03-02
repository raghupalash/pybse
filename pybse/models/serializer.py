"""
pybse.models.serializer
=======================
Builds BSE wire payloads from InvestorProfile.

Protocol constants (HOLDING, CLIENT_TYPE, etc.) are set here, never in the
model. Callers never deal with BSE's raw field ordering or pipe-delimited
format.
"""

from __future__ import annotations

from pybse.models.enums import OccupationType
from pybse.models.investor import BankAccount, InvestorProfile, Nominee, TaxResidence

# ---------------------------------------------------------------------------
# Protocol constants
# ---------------------------------------------------------------------------

_HOLDING = "SI"
_CLIENT_TYPE = "P"
_PAN_EXEMPT = "N"
_DIV_PAY_MODE = "02"
_COUNTRY = "India"
_COMM_MODE = "E"
_MOBILE_DECLARATION = "SE"
_EMAIL_DECLARATION = "SE"
_NOMINATION_AUTH_MODE = "O"
_NOM_SOA = "N"
_DATA_SRC = "E"
_PEP_FLAG = "N"
_EXCH_NAME = "O"
_UBO_APPL = "N"
_UBO_DF = "N"
_NEW_CHANGE = "N"


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _bank_slot(bank: BankAccount | None) -> list[str]:
    """5 elements for one bank account slot. Empty strings when slot unused."""
    if bank is None:
        return ["", "", "", "", ""]
    return [
        str(bank.account_type),
        bank.account_number,
        bank.micr or "",
        bank.ifsc,
        "Y" if bank.is_default else "N",
    ]


def _nominee_slot(nominee: Nominee | None, profile: InvestorProfile) -> list[str]:
    """17 elements for one nominee slot. Empty strings when slot unused."""
    if nominee is None:
        return [""] * 17
    return [
        nominee.name,
        str(nominee.relation),
        str(nominee.share_percentage),
        "Y" if nominee.is_minor else "N",
        "",  # NOMINEE_DOB — not collected in v1
        "",  # NOMINEE_GUARDIAN
        "",  # NOMINEE_GUARDIAN_PAN
        str(nominee.id_type) if nominee.id_type is not None else "",
        nominee.id_number,
        profile.email,  # NOMINEE_EMAIL = investor's own contact
        profile.phone,  # NOMINEE_MOBILE = investor's own contact
        profile.address_line1,
        profile.address_line2,
        profile.address_line3,
        profile.city,
        profile.pincode,
        _COUNTRY,
    ]


def _tax_residence_triple(residences: list[TaxResidence], index: int) -> list[str]:
    """3 elements: [country_code, tax_id_number, tax_id_type] or ["","",""]."""
    if index >= len(residences):
        return ["", "", ""]
    r = residences[index]
    return [r.country_code, r.tax_id_number, str(r.tax_id_type)]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_ucc_param(profile: InvestorProfile) -> str:
    """Return the 183-field pipe-delimited Param string for UCCRegistrationV183."""
    # Sort bank accounts: default first, then the rest in insertion order.
    # Two separate steps so mypy knows the lambda receives BankAccount, not None.
    sorted_banks: list[BankAccount] = sorted(
        profile.bank_accounts, key=lambda b: (0 if b.is_default else 1)
    )
    banks: list[BankAccount | None] = list(sorted_banks)
    # Pad to 5 slots.
    while len(banks) < 5:
        banks.append(None)

    # Pad nominees to 3 slots.
    nominees: list[Nominee | None] = list(profile.nominees)
    while len(nominees) < 3:
        nominees.append(None)

    fields: list[str] = [
        # 1–9: Identity + holding
        str(profile.ucc),  # 1  UCC
        profile.first_name,  # 2  FIRSTNAME
        profile.middle_name,  # 3  MIDDLENAME
        profile.last_name,  # 4  LASTNAME
        str(profile.tax_status),  # 5  TAX_STATUS
        str(profile.gender),  # 6  GENDER
        profile.date_of_birth.strftime("%d/%m/%Y"),  # 7  DOB
        str(profile.occupation),  # 8  OCCUPATION_CODE
        _HOLDING,  # 9  HOLDING
        # 10–17: Second/third holder names + DOBs (always blank in v1)
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        # 18–21: Guardian name + DOB (always blank in v1)
        "",
        "",
        "",
        "",
        # 22–25: PAN exempt flags
        _PAN_EXEMPT,
        "",
        "",
        "",  # 22–25
        # 26–29: PAN fields
        profile.pan,
        "",
        "",
        "",  # 26–29
        # 30–33: Exempt categories
        "",
        "",
        "",
        "",  # 30–33
        # 34–41: Client type + demat fields
        _CLIENT_TYPE,  # 34  CLIENT_TYPE
        "",
        "",
        "",
        "",
        "",
        "",
        "",  # 35–41
        # 42–66: Bank accounts (5 slots × 5 sub-fields)
        *_bank_slot(banks[0]),  # 42–46
        *_bank_slot(banks[1]),  # 47–51
        *_bank_slot(banks[2]),  # 52–56
        *_bank_slot(banks[3]),  # 57–61
        *_bank_slot(banks[4]),  # 62–66
        # 67–68: Cheque name + dividend pay mode
        "",  # 67  CHEQUE_NAME
        _DIV_PAY_MODE,  # 68  DIV_PAY_MODE
        # 69–81: Address + communication
        profile.address_line1,  # 69  ADDRESS_1
        profile.address_line2,  # 70  ADDRESS_2
        profile.address_line3,  # 71  ADDRESS_3
        profile.city,  # 72  CITY
        str(profile.state),  # 73  STATE
        profile.pincode,  # 74  PINCODE
        _COUNTRY,  # 75  COUNTRY
        profile.phone,  # 76  RESI_PHONE
        "",  # 77  RESI_FAX
        "",  # 78  OFFICE_PHONE
        "",  # 79  OFFICE_FAX
        profile.email,  # 80  EMAIL
        _COMM_MODE,  # 81  COMM_MODE
        # 82–92: Foreign address fields (always blank for Resident Indians)
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        # 93: Indian mobile number
        profile.phone,  # 93  INDIAN_MOB_NO
        # 94–105: KYC fields
        str(profile.kyc_type),  # 94  KYC_TYPE
        "",  # 95  CKYC_NUMBER
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",  # 96–105
        # 106–110: Aadhaar / LEI
        "",
        "",
        str(profile.paperless_flag),
        "",
        "",  # 106–110
        # 111–120: Mobile/email declarations for all holders
        _MOBILE_DECLARATION,  # 111  MOBILE_DECLARATION
        _EMAIL_DECLARATION,  # 112  EMAIL_DECLARATION
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",  # 113–120
        # 121: Guardian relationship (always blank in v1)
        "",  # 121
        # 122–123: Nomination opt + auth mode
        "Y" if profile.nominees else "N",  # 122  NOMINATION_OPT
        _NOMINATION_AUTH_MODE,  # 123  NOMINATION_AUTH_MODE
        # 124–174: Nominees (3 slots × 17 sub-fields)
        *_nominee_slot(nominees[0], profile),  # 124–140
        *_nominee_slot(nominees[1], profile),  # 141–157
        *_nominee_slot(nominees[2], profile),  # 158–174
        # 175: NOM_SOA
        _NOM_SOA,  # 175
        # 176–183: Filler fields
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",  # 176–183
    ]

    assert len(fields) == 183, f"BUG: UCC param has {len(fields)} fields, expected 183"
    return "|".join(fields)


def build_fatca_param(profile: InvestorProfile) -> str:
    """Return the pipe-delimited Param string for FATCADetailsV2."""
    fatca = profile.fatca
    residences = fatca.tax_residences

    full_name = " ".join(
        part
        for part in [profile.first_name, profile.middle_name, profile.last_name]
        if part
    )[:70]

    fields: list[str] = [
        profile.pan,  # 1   PAN_RP
        "",  # 2   PEKRN
        full_name,  # 3   INV_NAME
        profile.date_of_birth.strftime("%m/%d/%Y"),  # 4   DOB (MM/DD/YYYY)
        "",  # 5   FR_NAME
        "",  # 6   SP_NAME
        str(profile.tax_status),  # 7   TAX_STATUS
        _DATA_SRC,  # 8   DATA_SRC
        str(fatca.address_type),  # 9   ADDR_TYPE
        fatca.place_of_birth[:50],  # 10  PO_BIR_INC
        fatca.country_of_birth,  # 11  CO_BIR_INC
        *_tax_residence_triple(residences, 0),  # 12–14 TAX_RES1/TPIN1/ID1_TYPE
        *_tax_residence_triple(residences, 1),  # 15–17
        *_tax_residence_triple(residences, 2),  # 18–20
        *_tax_residence_triple(residences, 3),  # 21–23
        str(fatca.source_of_wealth),  # 24  SRCE_WEALT
        str(fatca.income_slab),  # 25  INC_SLAB
        _PEP_FLAG,  # 26  PEP_FLAG
        str(profile.occupation),  # 27  OCC_CODE
        str(OccupationType.from_occupation(profile.occupation)),  # 28  OCC_TYPE
        _EXCH_NAME,  # 29  EXCH_NAME
        _UBO_APPL,  # 30  UBO_APPL
        _UBO_DF,  # 31  UBO_DF
        _NEW_CHANGE,  # 32  NEW_CHANGE
        str(profile.ucc),  # 33  LOG_NAME
        "",  # 34  DOC1
        "",  # 35  DOC2
    ]

    return "|".join(fields)
