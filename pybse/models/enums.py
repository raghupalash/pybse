"""
pybse.models.enums
==================
All BSE protocol enums. Members inherit from StrEnum so they work as plain
strings without calling .value (e.g. in format strings and API payloads).
"""

from __future__ import annotations

from enum import StrEnum


class TaxStatus(StrEnum):
    """BSE tax status codes. v1 only permits INDIVIDUAL."""

    INDIVIDUAL = "01"
    ON_BEHALF_OF_MINOR = "02"
    HUF = "03"
    NRI_OTHERS = "11"
    NRE = "21"
    NRO = "24"


class Gender(StrEnum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"


class OccupationCode(StrEnum):
    BUSINESS = "01"
    SERVICE = "02"
    PROFESSIONAL = "03"
    AGRICULTURE = "04"
    RETIRED = "05"
    HOUSEWIFE = "06"
    STUDENT = "07"
    OTHERS = "08"
    DOCTOR = "09"
    PRIVATE_SECTOR_SERVICE = "41"
    PUBLIC_SECTOR_SERVICE = "42"
    FOREX_DEALER = "43"
    GOVERNMENT_SERVICE = "44"
    UNKNOWN = "99"


class OccupationType(StrEnum):
    """FATCA occupation type — coarser grouping derived from OccupationCode.

    Callers never set this directly; use from_occupation() or let the
    serialiser derive it.
    """

    BUSINESS = "B"
    SERVICE = "S"
    OTHERS = "O"

    @classmethod
    def from_occupation(cls, occ: OccupationCode) -> OccupationType:
        _BUSINESS = {OccupationCode.BUSINESS, OccupationCode.FOREX_DEALER}
        _SERVICE = {
            OccupationCode.SERVICE,
            OccupationCode.PROFESSIONAL,
            OccupationCode.DOCTOR,
            OccupationCode.PRIVATE_SECTOR_SERVICE,
            OccupationCode.PUBLIC_SECTOR_SERVICE,
            OccupationCode.GOVERNMENT_SERVICE,
        }
        if occ in _BUSINESS:
            return cls.BUSINESS
        if occ in _SERVICE:
            return cls.SERVICE
        return cls.OTHERS


class HoldingNature(StrEnum):
    SINGLE = "SI"
    JOINT = "JO"
    ANYONE_OR_SURVIVOR = "AS"


class AccountType(StrEnum):
    """v1 only allows SAVINGS and CURRENT."""

    SAVINGS = "SB"
    CURRENT = "CB"
    NRE = "NE"
    NRO = "NO"


class DividendPayMode(StrEnum):
    DIRECT_CREDIT = "02"


class KYCType(StrEnum):
    KRA_COMPLIANT = "K"
    CKYC_COMPLIANT = "C"
    BIOMETRIC = "B"
    AADHAAR_EKYC = "E"


class PaperlessFlag(StrEnum):
    EKYC = "Z"


class CommunicationMode(StrEnum):
    EMAIL = "E"


class IndianState(StrEnum):
    ANDHRA_PRADESH = "AP"
    ARUNACHAL_PRADESH = "AR"
    ASSAM = "AS"
    BIHAR = "BR"
    CHHATTISGARH = "CG"
    GOA = "GA"
    GUJARAT = "GJ"
    HARYANA = "HR"
    HIMACHAL_PRADESH = "HP"
    JAMMU_AND_KASHMIR = "JK"
    JHARKHAND = "JH"
    KARNATAKA = "KA"
    KERALA = "KL"
    MADHYA_PRADESH = "MP"
    MAHARASHTRA = "MH"
    MANIPUR = "MN"
    MEGHALAYA = "ML"
    MIZORAM = "MZ"
    NAGALAND = "NL"
    ODISHA = "OR"
    PUNJAB = "PB"
    RAJASTHAN = "RJ"
    SIKKIM = "SI"
    TAMIL_NADU = "TN"
    TELANGANA = "TS"
    TRIPURA = "TR"
    UTTAR_PRADESH = "UP"
    UTTARAKHAND = "UL"
    WEST_BENGAL = "WB"
    ANDAMAN_AND_NICOBAR = "AN"
    CHANDIGARH = "CH"
    DADRA_AND_NAGAR_HAVELI = "DN"
    DAMAN_AND_DIU = "DD"
    DELHI = "DL"
    LAKSHADWEEP = "LD"
    PUDUCHERRY = "PY"
    LADAKH = "LA"


class NomineeRelation(StrEnum):
    AUNT = "01"
    BROTHER_IN_LAW = "02"
    BROTHER = "03"
    DAUGHTER = "04"
    DAUGHTER_IN_LAW = "05"
    FATHER = "06"
    FATHER_IN_LAW = "07"
    GRANDDAUGHTER = "08"
    GRANDFATHER = "09"
    GRANDMOTHER = "10"
    GRANDSON = "11"
    MOTHER_IN_LAW = "12"
    MOTHER = "13"
    NEPHEW = "14"
    NIECE = "15"
    SISTER = "16"
    SISTER_IN_LAW = "17"
    SON = "18"
    SON_IN_LAW = "19"
    SPOUSE = "20"
    UNCLE = "21"
    OTHERS = "22"
    COURT_APPOINTED_GUARDIAN = "23"


class NomineeIDType(StrEnum):
    PAN = "01"
    AADHAAR = "02"
    PASSPORT = "03"
    VOTER_ID = "04"
    DRIVING_LICENCE = "05"
    OTHERS = "06"


class SourceOfWealth(StrEnum):
    SALARY = "01"
    BUSINESS_INCOME = "02"
    GIFT = "03"
    ANCESTRAL_PROPERTY = "04"
    RENTAL_INCOME = "05"
    PRIZE_MONEY = "06"
    ROYALTY = "07"
    OTHERS = "08"


class IncomeSlab(StrEnum):
    BELOW_1_LAC = "31"
    ABOVE_1_LAC_UPTO_5_LAC = "32"
    ABOVE_5_LAC_UPTO_10_LAC = "33"
    ABOVE_10_LAC_UPTO_25_LAC = "34"
    ABOVE_25_LAC_UPTO_1_CRORE = "35"
    ABOVE_1_CRORE = "36"


class FATCATaxIDType(StrEnum):
    PASSPORT = "A"
    ELECTION_ID = "B"
    PAN = "D"
    DRIVING_LICENCE = "E"
    AADHAAR = "G"
    NREGA_JOB_CARD = "H"
    TIN = "T"
    OTHERS = "O"
    NOT_CATEGORIZED = "X"


class FATCAAddressType(StrEnum):
    RESIDENTIAL = "1"
    BUSINESS = "2"
    REGISTERED = "3"
