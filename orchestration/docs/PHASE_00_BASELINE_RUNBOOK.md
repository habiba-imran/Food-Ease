# Phase 0 baseline runbook

This runbook only prepares and inspects the independent packages. It does not
implement or activate final orchestration. Stop after Phase 0.

## Setup in ordinary Windows PowerShell

Prerequisites: Git, uv and Node installed; Python 3.12 for Habiba's packages and
3.11 for the website (matching its existing pin). No API keys are needed. Do not
copy or edit .env for this baseline. These commands run from the repository root:

```powershell
uv --version
node --version
uv python list --only-installed

# If the declared interpreters are not already installed:
# uv python install 3.12 3.11

uv sync --locked --project voice-agent --python 3.12
uv sync --locked --project orchestration --python 3.12
uv sync --locked --project website --python 3.11
```

The website now includes uv.lock; orchestration now explicitly pins Python 3.12.
Existing locks were preserved. To use a workspace-local package cache, prepend
`--cache-dir C:\HCI-PROJECT\.tools\uv-cache` after `uv`. The ignored `.tools/`
directory is disposable tooling cache, never application state or secrets.

During this Codex session, sandboxed Python invocation reported a misleading
`No Python at ...` because its base interpreter directory was inaccessible. The
same interpreter worked with the required execution access. In an ordinary
PowerShell terminal, verify the commands below before recreating any environment.
Do not interpret a sandbox access denial as proof that Python is missing.

```powershell
.\voice-agent\.venv\Scripts\python.exe --version
.\orchestration\.venv\Scripts\python.exe --version
.\website\.venv\Scripts\python.exe --version
```

The agent README's UTF-16LE encoding prevented uv_build from reading package
metadata. Phase 0 converted it to UTF-8 with identical decoded text; no shopping
or voice behavior changed.

## Run the offline checks

From the repository root:

```powershell
.\orchestration\.venv\Scripts\python.exe orchestration\tools\phase0_baseline.py `
  --output orchestration\evidence\final\phase-00\run-local
```

The runner uses each package's own interpreter, runs full pytest/lint, agent
pyright, website JavaScript syntax and exact version/API inventory. It validates
all 102 requirements-map rows against their source documents. It disables dotenv,
removes known provider credentials from child environments, forces Hugging Face
offline mode and never starts the voice worker or session dispatch. Existing
component tests may construct clients with fake credentials; they do not run a
live conversation.

Existing acceptance tests regenerate older handover files; the runner preserves
and restores those files byte-for-byte. New output belongs under phase-00 only.
It returns nonzero when checks fail, even for known pre-existing failures. Read
the actual logs; do not change test expectations or suppress failures to turn the
baseline green.

## Standalone website HTTP smoke

Terminal A, from `website/`:

```powershell
$env:PYTHON_DOTENV_DISABLED = '1'
$env:HOST = '127.0.0.1'
$env:PORT = '18080'
$env:ENABLE_MOCK_AGENT = 'false'
$env:RECORD_AUDIO = 'false'
.\.venv\Scripts\python.exe -m foodease_website.main
```

Terminal B, from the repository root:

```powershell
.\orchestration\.venv\Scripts\python.exe orchestration\tools\phase0_website_smoke.py `
  --output orchestration\evidence\final\phase-00\website-http-smoke-local.json
```

Use a fresh disposable server for every smoke run. The script refuses a domain
whose revision is not 1 or whose cart is nonempty. It searches/filters, opens an
item, adds two wraps, changes quantity to one and explicitly confirms a fictional
PKR 900 order. It verifies idempotent replay of the original submission and an
empty final cart. Only the fresh localhost domain is changed. No session service,
worker, database or provider is needed. Stop the server with Ctrl+C when done.

This proves the actual HTTP application operations, not DOM behavior, accessibility
or a voice journey. The output labels browser/voice verification as false.

## Browser walkthrough required to close the manual acceptance gate

Restart the disposable server to reset its in-memory cart, then open
http://127.0.0.1:18080 in a browser. Do not run the API smoke on that same domain
before the walkthrough.

1. Verify the homepage loads and manual controls work without starting assistance.
2. Open Hot Chicken Wrap details, add two, then reduce the cart quantity to one.
3. Verify the line price is PKR 850, service fee PKR 50 and total PKR 900.
4. Open demo checkout, review the visible summary and explicitly confirm.
5. Verify one simulated receipt and an empty cart. Capture browser/version and
   observations; check for JavaScript/network failures and any microphone prompt.

The browser connector exposed no available browser during this Phase 0 run. This
walkthrough is pending, not passed. Human keyboard/screen-reader/live-audio
acceptance is separate and remains pending in the later phases.

## Stop condition

Keep the pre-existing test/lint/type failures visible in the baseline report and
do not begin contract or runtime fixes without the next instruction. Phase 1 has
not started. Phase 0 cannot be labeled fully green while its browser/manual gate
or baseline checks remain unresolved.
