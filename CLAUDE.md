# CLAUDE.md

Guidance for working in this repo. This file intentionally does not duplicate
the project docs below — read them directly when you need that context:

- **[README.md](README.md)** — quick start, features, tech stack
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — system design, analysis flow, data models, API reference
- **[SECURITY.md](SECURITY.md)** — security policy and best practices
- **[USER_GUIDE.md](USER_GUIDE.md)** — dashboard usage

## Gotchas (not written down anywhere else)

- **Two `login_page.py` files, not one.** `dashboard/login_page.py` holds
  `check_authentication()`/`render_navigation()`/`logout()` and is what every
  real dashboard page imports. `dashboard/pages/login_page.py` is the actual
  Streamlit-routed login page a user sees (`st.switch_page("pages/login_page.py")`)
  and has its **own separate, diverged** `LoginManager` with slightly different
  demo credentials. Editing auth logic in one does not affect the other —
  check both before assuming a change to login behavior is complete.

- **`test_batch_analysis.py` runs `batch_analysis_service_quant.py`**, not the
  similarly-named `batch_analysis_service.py`. The `_quant` version is the one
  using `ThreadPoolExecutor`. Confirm which service a given test/entry point
  actually imports before reasoning about batch behavior.

- **Debug logging is opt-in.** Most per-stock diagnostic output in the
  DCF/calculator/analyzer chain goes through `utils/debug_printer.py`'s
  `debug_print()`, gated by the `DEBUG` env var (default `False` = no-op).
  Raw `print()` calls in analyzer/provider code are rare and mostly confined
  to `except` blocks (error-path only). Don't assume print volume is a
  performance concern without checking whether `DEBUG=true` is set.

- **Dead code — don't assume these are live:**
  - `src/share_insights_v1/ui_1_0/` — an entire parallel Streamlit UI, unreferenced anywhere.
  - `implementations/data_providers/yahoo_provider_original.py` — unreferenced.
  - `implementations/calculators/dcf_yf.py` — superseded by `dcf_yf_new.py`, unreferenced.

- **`resources/stock_dump/nyse.csv` has zero ETF listings.** ETFs like SPY,
  QQQ-equivalents, sector SPDRs, etc. mostly list on NYSE Arca, which this
  file excludes entirely (likely sourced with an NYSE-only exchange filter).
  `nasdaq.csv` does include ETFs. Known, unfixed gap — don't assume NYSE
  batch runs cover ETFs.

- **No CI, no pytest.** The ~65 files under `tests/` are standalone
  run-and-eyeball scripts (no `pytest.ini`/`conftest.py`, zero use
  `import pytest`). There's no automated gate catching regressions — changes
  to shared logic (analyzers, recommendation weighting, classifiers) should
  be spot-checked manually since nothing else will catch a break.

- **Dependencies are split across five unpinned requirements files**
  (`requirements.txt`, `requirements-api.txt`, `requirements_dashboard.txt`,
  `requirements_logging.txt`, `api/requirements.txt`) with no version pins
  and some duplicate/typo'd entries in the root file. Don't assume any one
  file is authoritative or complete.

- **EC2 deployment pulls over plain HTTPS with no stored credential** — the
  repo is public, so read access needs no PAT. Don't add push-capable
  credentials to the deploy box; it only needs to pull.

- **`__pycache__`/`.pyc` are gitignored** (fixed via `chore/remove-pycache`,
  merged to `main`). Don't recommit compiled bytecode.
