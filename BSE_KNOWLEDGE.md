# BSE Investor System — Knowledge Document

This is a reference document capturing everything known about BSE's investor
onboarding system. It is not implementation — it is facts. Code is written
against this document, not the other way around.

Sources:
- BSE Enhanced UCC Process Note v1.0 (Jul 2021 PDF)
- SBNRI internal API handling code (bse_ucc_onboarding_api_md)

Verification status is noted explicitly. Anything marked ⚠️ UNVERIFIED was
reconstructed from SBNRI's internal code and must be confirmed against the
official BSE API doc before shipping.

---

## 1. The Three-Call Investor Onboarding Flow

Registering an investor requires three separate API calls in sequence:

1. **UCC Registration** — `POST UCCRegistrationV183`
   The main registration call. A 183-field parameter. Creates the investor
   in BSE's system.

2. **FATCA Upload** — called immediately after UCC registration succeeds.
   Uploads tax residency and wealth declaration data.

3. **AOF Upload** — called *after BSE activates the UCC account*.
   This is deferred — BSE must activate the account first. Uses identity,
   address, bank, nominee, and signature data.

All three calls draw from the same investor data. There is no separate data
model per call — one investor profile, three serialisations.

---

## 2. Protocol Constants (Never Vary in v1)

These are BSE fields that always have the same value for v1 (Resident Indian,
individual, physical). They are NOT caller inputs — the serialiser writes them.

| BSE Field            | Value | Meaning                          |
|----------------------|-------|----------------------------------|
| HOLDING              | "SI"  | Single holder                    |
| CLIENT_TYPE          | "P"   | Physical (no demat)              |
| KYC_TYPE             | "K"   | KRA-compliant                    |
| PAPERLESS_FLAG       | "Z"   | eKYC / paperless                 |
| PAN_EXEMPT           | "N"   | PAN is always provided           |
| COMM_MODE            | "E"   | Email                            |
| MOBILE_DECLARATION   | "SE"  | Self-declared                    |
| EMAIL_DECLARATION    | "SE"  | Self-declared                    |
| NOMINATION_AUTH_MODE | "O"   | OTP                              |
| NOM_SOA              | "N"   |                                  |
| COUNTRY              | "India"|                                 |
| FOREIGN_ADD_*        | ""    | Blank for Resident Indians       |
| DATA_SRC (FATCA)     | "E"   | Electronic submission            |
| PEP_FLAG (FATCA)     | "N"   | Not politically exposed          |
| EXCH_NAME (FATCA)    | "O"   | Others / not exchange-listed     |
| UBO_APPL (FATCA)     | "N"   |                                  |
| UBO_DF (FATCA)       | "N"   |                                  |
| NEW_CHANGE (FATCA)   | "N"   | New submission, not a change     |
| ADDR_TYPE (FATCA)    | "1"   | Residential                      |
| DIV_PAY_MODE         | "02"  | Direct credit (default)          |

---

## 3. Fields the Caller Must Supply

### 3.1 Identity (Non-editable after BSE registration)

| Field         | Type         | Constraints                                    |
|---------------|--------------|------------------------------------------------|
| UCC           | string       | Max 10 chars. Unique per BSE member.           |
| First name    | string       | Max 70 chars. Required.                        |
| Middle name   | string       | Max 70 chars. Optional, usually empty.         |
| Last name     | string       | Max 70 chars. Optional but recommended.        |
| Tax status    | code (2-dig) | v1: must be "01" (Individual). See §4.1.       |
| Gender        | code (1-char)| M / F / O. See §4.2.                          |
| Date of birth | date         | Format: DD/MM/YYYY for UCC, MM/DD/YYYY for FATCA (same date, different format per call). |
| PAN           | string       | 10 chars. Regex: `[A-Z]{5}[0-9]{4}[A-Z]`. Uppercase. |
| Occupation    | code (2-dig) | See §4.3.                                      |

### 3.2 Contact

| Field  | Type   | Constraints                                        |
|--------|--------|----------------------------------------------------|
| Email  | string | Max 50 chars. Used for COMM_MODE = E.              |
| Phone  | string | 10 digits, no country code. Indian mobile only.    |

### 3.3 Address (Indian residential address)

| Field         | Type        | Constraints                            |
|---------------|-------------|----------------------------------------|
| Address line 1| string      | Max 40 chars. Required.                |
| Address line 2| string      | Max 40 chars. Optional.                |
| Address line 3| string      | Max 40 chars. Optional.                |
| City          | string      | Max 35 chars.                          |
| State         | code (2-char)| BSE 2-letter state codes. See §4.7.  |
| Pincode       | string      | Exactly 6 digits.                      |

Note: BSE splits long addresses across line1/2/3. If a full address is passed
in line1, the serialiser should handle wrapping.

### 3.4 Bank Accounts

- Minimum 1, maximum 5 bank accounts per investor.
- Exactly one must be marked as the default account.
- BSE silently drops accounts beyond 5 — the serialiser should warn, not silently drop.

Per account:

| Field          | Type        | Constraints                                       |
|----------------|-------------|---------------------------------------------------|
| Account type   | code        | v1: SAVINGS ("SB") or CURRENT ("CB") only. See §4.5. |
| Account number | string      | Max 40 chars.                                     |
| IFSC           | string      | Format: 4 alpha + "0" + 6 alphanumeric. e.g. HDFC0001234. |
| MICR           | string      | Optional. 9 digits if provided.                   |
| Is default     | bool        | Exactly one account must be default.              |

### 3.5 Nominees

- Optional. Empty list = investor opts out of nomination.
- Maximum 3 nominees.
- If any nominee is provided, share percentages across all nominees must sum to 100.

Per nominee:

| Field            | Type   | Constraints                                          |
|------------------|--------|------------------------------------------------------|
| Name             | string | Max 40 chars.                                        |
| Relation         | code   | See §4.8.                                            |
| Share percentage | int    | 1–100. All nominees must sum to 100.                 |
| Is minor         | bool   | Whether nominee is a minor.                          |
| ID type          | code   | Optional. See §4.9.                                  |
| ID number        | string | Required if ID type is set. Aadhaar: last 4 digits only. |

Note: Nominee DOB and guardian fields exist in BSE but are not collected in
v1 (matching SBNRI practice). Minor nominees may be rejected by BSE without
these fields — advise callers to use `is_minor=False` unless full data available.

### 3.6 FATCA Details

| Field            | Type              | Constraints                                    |
|------------------|-------------------|------------------------------------------------|
| Place of birth   | string            | Max 50 chars. BSE strips special chars.        |
| Country of birth | ISO 3166-1 alpha-2| 2-letter code e.g. "IN". See §5.              |
| Source of wealth | code              | See §4.10.                                     |
| Annual income    | code              | Income slab code. See §4.11.                  |
| Tax residences   | list              | 0–4 entries. See §3.7.                        |

### 3.7 Tax Residences (FATCA)

For a Resident Indian with no foreign ties, this should have one entry: India ("IN").
Maximum 4 entries.

Per entry:

| Field        | Type              | Constraints                        |
|--------------|-------------------|------------------------------------|
| Country code | ISO 3166-1 alpha-2| 2-letter code. Different from BSE's 3-digit numeric codes used in UCC. |
| Tax ID number| string            | Max 25 chars.                      |
| Tax ID type  | code              | See §4.12.                        |

---

## 4. Codes and Valid Values

### 4.1 Tax Status
2-digit codes. v1 accepts only "01".

| Code | Meaning              |
|------|----------------------|
| 01   | Individual           |
| 02   | On Behalf of Minor   |
| 03   | HUF                  |
| 11   | NRI - Others         |
| 21   | NRE                  |
| 24   | NRO                  |
| ...  | (many more — see BSE PDF p.32–33 for full table) |

### 4.2 Gender
1-char codes.

| Code | Meaning |
|------|---------|
| M    | Male    |
| F    | Female  |
| O    | Other   |

Source: BSE Enhanced UCC Process Note p.18.

### 4.3 Occupation Code
2-digit codes. SBNRI defaults to SERVICE ("02") when unknown — pybse does NOT
silently default; callers must supply a value.

| Code | Meaning                  | Notes                              |
|------|--------------------------|------------------------------------|
| 01   | Business                 |                                    |
| 02   | Service                  |                                    |
| 03   | Professional             |                                    |
| 04   | Agriculture              |                                    |
| 05   | Retired                  |                                    |
| 06   | Housewife                |                                    |
| 07   | Student                  |                                    |
| 08   | Others                   | Prefer over 99 for new registrations |
| 09   | Doctor                   | Extended code from SBNRI           |
| 41   | Private Sector Service   | Extended code from SBNRI           |
| 42   | Public Sector Service    | Extended code from SBNRI           |
| 43   | Forex Dealer             | Extended code from SBNRI           |
| 44   | Government Service       | Extended code from SBNRI           |
| 99   | Unknown / Not Applicable | Avoid for new registrations        |

Source: BSE Enhanced UCC Process Note p.34 (codes 01–08). Codes 09, 41–44, 99
from SBNRI internal map.

### 4.4 Occupation Type
FATCA-specific. A coarser grouping. Derived automatically from Occupation Code
by the serialiser — callers never set this.

| Code | Meaning  | Derived from occupation codes     |
|------|----------|-----------------------------------|
| B    | Business | 01 (Business), 43 (Forex Dealer)  |
| S    | Service  | 02, 03, 09, 41, 42, 44            |
| O    | Others   | 04, 05, 06, 07, 08, 99            |

### 4.5 Account Type

| Code | Meaning  | v1 allowed? |
|------|----------|-------------|
| SB   | Savings  | ✅ Yes      |
| CB   | Current  | ✅ Yes      |
| NE   | NRE      | ❌ No       |
| NO   | NRO      | ❌ No       |

Source: BSE Enhanced UCC Process Note p.29. TAX STATUS WITH ACCOUNT TYPE table
confirms RI Individual (01) → SB/CB only.

### 4.6 Holding Nature
v1 always uses SI. Others present for forward compatibility.

| Code | Meaning             |
|------|---------------------|
| SI   | Single              |
| JO   | Joint               |
| AS   | Anyone or Survivor  |

### 4.7 Indian State Codes
2-letter codes. Notable discrepancies between BSE PDF and SBNRI live data:

- UTTARAKHAND = "UL" (SBNRI uses "UL"; BSE PDF says "UC" — use "UL")
- DELHI = "DL" (in SBNRI map; absent from BSE PDF states table)
- NEW_DELHI = "ND" (in BSE PDF; prefer "DL" for addresses)
- SIKKIM = "SI" (visually collides with HoldingNature "SI" — separate fields, no runtime conflict)

Source: BSE Enhanced UCC Process Note p.42–43, cross-checked with SBNRI map.

### 4.8 Nominee Relation Codes

| Code | Meaning                  | Notes                          |
|------|--------------------------|--------------------------------|
| 01   | Aunt                     |                                |
| 02   | Brother-in-law           |                                |
| 03   | Brother                  |                                |
| 04   | Daughter                 |                                |
| 05   | Daughter-in-law          |                                |
| 06   | Father                   |                                |
| 07   | Father-in-law            |                                |
| 08   | Granddaughter            |                                |
| 09   | Grandfather              |                                |
| 10   | Grandmother              |                                |
| 11   | Grandson                 |                                |
| 12   | Mother-in-law            |                                |
| 13   | Mother                   |                                |
| 14   | Nephew                   |                                |
| 15   | Niece                    |                                |
| 16   | Sister                   |                                |
| 17   | Sister-in-law            |                                |
| 18   | Son                      |                                |
| 19   | Son-in-law               |                                |
| 20   | Spouse                   | Covers both husband and wife   |
| 21   | Uncle                    |                                |
| 22   | Others                   |                                |
| 23   | Court Appointed Guardian |                                |

Note: No separate code for husband/wife — use SPOUSE ("20") for both.
Source: SBNRI `BSE_RELATIONSHIP_CODES`.

### 4.9 Nominee ID Type

| Code | Meaning          | Notes                                        |
|------|------------------|----------------------------------------------|
| 01   | PAN              |                                              |
| 02   | Aadhaar          | Only last 4 digits sent per BSE privacy rules|
| 03   | Passport         |                                              |
| 04   | Voter ID         |                                              |
| 05   | Driving Licence  |                                              |
| 06   | Others           |                                              |

### 4.10 Source of Wealth (FATCA)

| Code | Meaning              |
|------|----------------------|
| 01   | Salary               |
| 02   | Business Income      |
| 03   | Gift                 |
| 04   | Ancestral Property   |
| 05   | Rental Income        |
| 06   | Prize Money          |
| 07   | Royalty              |
| 08   | Others               |

Source: SBNRI `SOURCE_OF_WEALTH_MAP`.

### 4.11 Income Slab (FATCA)
Annual income in Indian Rupees.

| Code | Meaning                        |
|------|--------------------------------|
| 31   | Below ₹1 Lac                   |
| 32   | Above ₹1 Lac up to ₹5 Lac      |
| 33   | Above ₹5 Lac up to ₹10 Lac     |
| 34   | Above ₹10 Lac up to ₹25 Lac    |
| 35   | Above ₹25 Lac up to ₹1 Crore   |
| 36   | Above ₹1 Crore                 |

Source: SBNRI `INCOME_SLAB_MAP`.

### 4.12 FATCA Tax ID Type

| Code | Meaning           | Notes                                                |
|------|-------------------|------------------------------------------------------|
| A    | Passport          |                                                      |
| B    | Election ID       |                                                      |
| D    | PAN               | ⚠️ UNVERIFIED — SBNRI flagged as TODO, pending BSE confirmation |
| E    | Driving Licence   |                                                      |
| G    | Aadhaar           |                                                      |
| H    | NREGA Job Card    |                                                      |
| T    | TIN               | Foreign tax ID. Most common for non-India residences |
| O    | Others            |                                                      |
| X    | Not Categorized   |                                                      |

Note: For v1 Resident Indians, TIN ("T") and Aadhaar ("G") are the most common
for the India TaxResidence entry.

Source: SBNRI `IDENTIFICATION_TYPE` map.

### 4.13 KYC Type
v1 always uses KRA_COMPLIANT. Pre-flight check must confirm CVLKRA status
before submission.

| Code | Meaning        |
|------|----------------|
| K    | KRA Compliant  |
| C    | CKYC Compliant |
| B    | Biometric KYC  |
| E    | Aadhaar eKYC   |

Source: BSE Enhanced UCC Process Note p.27.

### 4.14 FATCA Address Type
⚠️ UNVERIFIED — only partial values confirmed. Verify full set against BSE FATCA API doc.

| Code | Meaning     |
|------|-------------|
| 1    | Residential |
| 2    | Business    |
| 3    | Registered  |

---

## 5. Country Codes

BSE uses **two different country code systems** depending on the API:

- **UCC API**: 3-digit numeric codes (BSE proprietary, NOT ISO-3166). 243 entries.
  Example: India = "101".
- **FATCA API**: Standard ISO 3166-1 alpha-2 (2-letter codes).
  Example: India = "IN".

These are completely separate — do not mix them.

---

## 6. Date Formats

BSE is inconsistent about date formats across calls:

| Call             | Format     |
|------------------|------------|
| UCC Registration | DD/MM/YYYY |
| FATCA Upload     | MM/DD/YYYY |

Same date, different format. The serialiser must handle this per call.

---

## 7. Known Quirks and Gotchas

- **SBNRI defaults vs pybse policy**: SBNRI silently defaults several fields
  (e.g. occupation → SERVICE when unknown). pybse does NOT silently default —
  callers must supply values. No hidden behaviour.

- **Aadhaar nominee ID**: Only the last 4 digits should be sent per BSE privacy
  rules. The serialiser does NOT truncate — callers must supply the 4-digit suffix.

- **Excess bank accounts**: BSE silently drops accounts beyond 5. pybse should
  raise `BSEValidationError` rather than silently drop.

- **Nomination opt-out**: Empty nominee list = `NOMINATION_OPT = "N"`. Any
  nominee present = `NOMINATION_OPT = "Y"`.

- **Non-editable fields**: First name, last name, middle name, PAN, DOB, and
  tax status cannot be changed after BSE registration. Document this clearly
  to callers.

- **Seafarer codes**: BSE PDF lists 76/77 for NRE/NRO seafarers. SBNRI docs
  mention 77/78. Use 76/77 per the official BSE PDF.

---

## 8. What Still Needs Verification

- ⚠️ `FATCATaxIDType` PAN = "D" — SBNRI flagged as unconfirmed with BSE
- ⚠️ `FATCAAddressType` — only 3 values confirmed (1, 2, 3). Full set unknown.
- ⚠️ AOF Upload API — field requirements not fully documented yet. To be
  researched when AOF implementation begins.
- ⚠️ SOAP buy order auth flow — password fetch mechanism and session lifetime
  not documented here yet. Separate research needed.