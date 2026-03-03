# RHLC Community Exporter

Export your Red Hat Learning Community posts from `learn.redhat.com` to a
self-contained offline HTML archive with all images and attachments downloaded
locally.

---

## Prerequisites

- **uv** (recommended) — install from https://docs.astral.sh/uv/getting-started/installation/
- **Python 3.11+** — uv can install this for you (see below)
- **git** — to clone the repository
- A `learn.redhat.com` account (Red Hat SSO)
- `my_community_content.json` — your community content export
  _(not needed if you use `--auto`, which downloads it for you)_

### 1. Clone the repository

```bash
git clone https://github.com/tmichett/rhlc_save.git
cd rhlc_save
```

### 2. Install Python 3.11+ with uv (if needed)

If you don't have Python 3.11 or later installed, uv can install it for you:

```bash
# Install Python 3.11 using uv
uv python install 3.11

# Verify installation
uv python list
```

### 3. Install dependencies (first run only)

With uv (recommended):

```bash
uv sync
```

Or with plain pip:

```bash
pip install -r requirements.txt
```

For the fully-automatic mode (`--auto` / `--fetch-json`), also install Playwright:

```bash
uv pip install playwright
uv run playwright install chromium
```

---

## Quick Start

### Option A — Fully automatic (recommended)

The easiest path: one command logs you in, downloads your community JSON, and
runs the full export pipeline automatically.

**Requires Playwright** (install once):

```bash
uv pip install playwright
uv run playwright install chromium
```

Then run:

```bash
uv run export_community.py --auto
```

What `--auto` does:

1. Opens a real Chromium browser window at `learn.redhat.com`
2. **Click "Sign In"** in the top-right corner and log in with your Red Hat account
3. Once fully logged in, press Enter in the terminal
4. The script navigates to your **Advanced Profile** page automatically
5. Clicks **My community content** to download the JSON
6. Saves your session cookies to `cookies.txt` for future runs
7. Runs the full export pipeline (images, attachments, HTML generation)

> **⚠️ Important:** When the browser opens, you will see the RHLC homepage —
> **not** a login form. You must click **Sign In** in the top-right corner
> yourself. The `/t5/s/sso` path is not a valid direct login URL on this site.

> **Tip:** On subsequent runs, if `my_community_content.json` already exists
> and your cookies are still valid, you can skip the download step:
> ```bash
> uv run export_community.py --cookies cookies.txt
> ```

---

## More Information

For full documentation including all authentication options, CLI reference,
output structure, and troubleshooting, see the **[User Guide](USER_GUIDE.md)**.
