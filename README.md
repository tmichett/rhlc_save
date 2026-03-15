# RHLC Community Tools

Two powerful tools for backing up Red Hat Learning Community content from `learn.redhat.com`:

1. **`export_community.py`** - Export your personal posts to a beautiful offline HTML archive
2. **`rhlc-backup.py`** - Complete site backup using the Khoros API (requires moderator access)

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

### Personal Posts Export (export_community.py)

#### Option A — Fully automatic (recommended)

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

### Full Site Backup (rhlc-backup.py)

**NEW!** For moderators and admins who need to backup the entire community site:

```bash
# Install Playwright (one-time setup)
uv pip install playwright
uv run playwright install chromium

# Run full site backup
uv run python rhlc-backup.py --auto
```

This will:
1. Open a browser for you to log in as a moderator/admin
2. Use the Khoros REST API to fetch all accessible content
3. Download all boards, messages, images, and attachments
4. **Automatically filter out external URLs** (e.g., nvidia.com)
5. **Add proper file extensions** based on Content-Type headers
6. Save everything in structured JSON and HTML formats

**Key differences from export_community.py:**
- Backs up **entire site** (not just your posts)
- Requires **moderator/admin access**
- Uses **Khoros API** (not JSON export)
- Outputs **raw JSON + threaded HTML** (not styled archive)
- Includes **attachment reprocessing** for failed downloads

**Recent Improvements (v2.0):**
- ✅ External URL filtering (only downloads from learn.redhat.com)
- ✅ Automatic file extension detection from Content-Type headers
- ✅ Reprocessing script for fixing incomplete backups
- ✅ Better authentication handling and error reporting

---

## Documentation

### Main Guides
- **[USER_GUIDE.md](USER_GUIDE.md)** - Complete guide for `export_community.py` (personal posts)
- **[COMPLETE_BACKUP_GUIDE.md](COMPLETE_BACKUP_GUIDE.md)** - **NEW!** Comprehensive guide for `rhlc-backup.py` (full site backup)
- **[BACKUP_GUIDE.md](BACKUP_GUIDE.md)** - Original backup guide (still valid)

### Specialized Guides
- **[ATTACHMENT_REPROCESSING_GUIDE.md](ATTACHMENT_REPROCESSING_GUIDE.md)** - Fix attachment issues in existing backups
- **[ATTACHMENT_FIX_NOTES.md](ATTACHMENT_FIX_NOTES.md)** - Technical details on attachment fixes
- **[BACKUP_STRATEGY.md](BACKUP_STRATEGY.md)** - Backup planning and strategies

### Quick Reference

| Task | Script | Command |
|------|--------|---------|
| Export my posts | `export_community.py` | `uv run export_community.py --auto` |
| Backup entire site | `rhlc-backup.py` | `uv run rhlc-backup.py --auto` |
| Export with saved cookies | `export_community.py` | `uv run export_community.py --cookies cookies.txt` |
| Backup specific boards | `rhlc-backup.py` | `uv run rhlc-backup.py --auto --boards "Board Name"` |
| Incremental backup | `rhlc-backup.py` | `uv run rhlc-backup.py --auto --since 2024-01-01` |
| Reprocess attachments | `reprocess_attachments.py` | `uv run python reprocess_attachments.py --backup-dir backup_20260314_123456 --auto` |
| Regenerate HTML | `regenerate_html.py` | `uv run python regenerate_html.py --backup-dir backup_20260314_123456` |

---

## Which Script Should I Use?

### Use `export_community.py` if you want to:
- ✅ Export your own posts and contributions
- ✅ Create a beautiful, styled HTML archive
- ✅ Have a personal backup of your content
- ✅ Share your posts offline

### Use `rhlc-backup.py` if you want to:
- ✅ Backup the entire community site
- ✅ Archive all boards and categories
- ✅ Preserve community content as a moderator/admin
- ✅ Get structured JSON data for analysis
- ✅ Create incremental backups

### Use both!
Many moderators use both scripts:
- `export_community.py` for a personal, styled archive
- `rhlc-backup.py` for comprehensive site backups
