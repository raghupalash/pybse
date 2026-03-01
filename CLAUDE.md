# pybse

## Project Overview
pybse is a Python client library for BSE (Bombay Stock Exchange) STAR MF APIs. It abstracts BSE's painful SOAP/REST hybrid into a clean, correct Python interface. The goal is correct and reliable over feature-rich — every error has a named exception, there are no silent failures, and the library is honest about what it doesn't handle yet.

`BSE_INVESTOR_KNOWLEDGE.md` contains all BSE-specific field definitions, valid codes, constraints, and known quirks. Read it before implementing anything related to investor creation or order creation.

---

## Exception Hierarchy
pybse has two distinct exception types:

**Validation errors** — raised before any API call, when the caller passes bad input. Inherits from `ValueError`.
```python
BSEValidationError(ValueError)
```

**API errors** — raised when BSE returns an error. Inherits from `Exception`.
```python
BSEApiError(Exception)
    AuthenticationFailed(BSEApiError)
    InvestorAlreadyExists(BSEApiError)
    InvalidPAN(BSEApiError)
    OrderRejected(BSEApiError)
    BSEUnknownError(BSEApiError)  # catch-all, exposes raw code and message
```

More typed exceptions are added empirically as new error codes are discovered through testing — don't try to map everything upfront.

---

## HTTP Client
- All REST calls use `httpx`. This is a deliberate choice — `httpx` supports both sync and async out of the box, meaning async support can be added later without rewriting the HTTP layer.
- All SOAP calls use `zeep`. SOAP auth is not a single reusable flow — different SOAP APIs have different password flows. Only implement what the current feature requires.

---

## Architecture Decisions

**Investor creation is a three-call flow:**
1. UCC registration
2. FATCA upload
3. AOF upload (deferred — happens after BSE activates the account)

**Input models** are dataclasses with enums. Callers never deal with BSE's raw protocol codes or magic strings — enums hide that entirely.

**Error codes** are handled empirically. Start with what you know (0=success, 1=failure), add typed exceptions as new codes are discovered through testing. Don't try to map everything from docs upfront.

**v1 is scoped to Resident Indians only.** NRI support, multiple holders, and all other investor types are explicitly out of scope.

---

## Project Structure
```
pybse/
    __init__.py
    client.py
    exceptions.py
    models/
        __init__.py
        investor.py
        order.py
    http/
        __init__.py
        rest.py
        soap.py
tests/
    __init__.py
    test_auth.py
    test_investor.py
    test_order.py
pyproject.toml
CHANGELOG.md
CLAUDE.md
README.md
```

---

## Code Style & Tooling
- Type hints everywhere — no untyped functions
- `ruff` for linting and formatting
- `mypy` for type checking
- Pre-commit hooks to enforce both automatically

---

## Instructions for Claude Code

These are non-negotiable. Follow them exactly.

### Before writing any code
1. Check the current git branch. If you're on `main`, stop and create a feature branch first.
2. Branch name must match the Linear ticket e.g. `pal-246-rest-authentication`
3. Confirm the branch with the user before proceeding.

### While writing code
- Write one logical unit at a time — don't implement everything in one go.
- After each logical unit, stop and show what you've written before moving on.
- Do not refactor anything outside the scope of the current ticket.
- Do not create files not listed in the project structure without asking first.
- If you're unsure about a design decision, ask — don't assume.

### Commits
- Commit after each logical unit — not at the end of everything.
- Follow conventional commits format: `feat:`, `fix:`, `test:`, `chore:`
- Commit messages must be descriptive e.g. `feat: add REST auth client with credential injection` not `add auth`
- Never commit directly to `main`.

### When you're done
- All tests must pass.
- Tell the user what was done, what was committed, and what the next step is.

### Pull Requests
- When the ticket is complete, open a PR from the feature branch into `main`.
- PR title must reference the Linear ticket e.g. `[PAL-246] Implement REST authentication`
- PR description must summarise what was done and how to test it.
- Do not merge the PR — that's the user's job.


---

## Development

### Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Running Tests
```bash
pytest
```

---

## Dependencies
- `httpx` — REST HTTP client
- `zeep` — SOAP client
- `pytest` — testing
- `pytest-httpx` — mocking httpx calls in tests
- `ruff` — linting and formatting
- `mypy` — type checking
- `pre-commit` — git hooks

---

## Testing
- `pytest` for all tests
- `pytest-httpx` for mocking REST calls — no real BSE API calls in tests ever
- SOAP via `zeep` — no SOAP mocking for now, revisit when complexity demands it
- Tests mirror the source structure — `tests/test_investor.py` tests `pybse/models/investor.py` etc.
- Every error case that BSE can return should have a corresponding test

---

## v1 Scope

**In scope:**
- REST authentication
- SOAP authentication — scoped to buy order API only (different SOAP APIs have different password flows, only implementing what v1 needs)
- Investor creation (Resident Indians only)
- Buy order creation

**Explicitly out of scope:**
- NRI support, multiple holders, any non-Resident Indian investor types
- Additional order flows — SIP, SWP, STP, Switch, Sell
- Order and investor status management
- API logging

---

## Notes
- Keep API credentials out of source code; use environment variables or a local config file (excluded via .gitignore).