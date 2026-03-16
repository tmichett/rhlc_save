# RHLC Community Tools

Three powerful tools for backing up Red Hat Learning Community content from `learn.redhat.com`:

1. **`export_community.py`** - Export your personal posts to a beautiful offline HTML archive
2. **`rhlc-backup.py`** - Complete site backup by crawling the site (backs up all accessible content; moderator/admin access provides more complete backups)
3. **`backup_groups.py`** - Backup course discussion groups (group hubs)


## ⚠️ Important: Rate Limiting Warning

**DO NOT run multiple backup scripts simultaneously!** Running `rhlc-backup.py` and `backup_groups.py` at the same time will trigger aggressive rate limiting (HTTP 429 errors), potentially block your IP, and corrupt your backups. Always run backups sequentially, one at a time.

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

**NEW!** Backup the entire community site by crawling all accessible content:

```bash
# Install Playwright (one-time setup)
uv pip install playwright
uv run playwright install chromium

# Run full site backup with FAST mode (RECOMMENDED - 7x faster!)
uv run python rhlc-backup.py --auto --fast
```

This will:
1. **Open first browser:** For you to log in with your Red Hat account
2. **Open second browser:** To discover all group hubs (automatic pagination)
3. Crawl each group to fetch all accessible content
4. Download all messages, images, and attachments
4. **Automatically filter out external URLs** (e.g., nvidia.com)
5. **Add proper file extensions** based on Content-Type headers
6. Save everything in structured JSON and HTML formats

**Key differences from export_community.py:**
- Backs up **entire site** (not just your posts)
- Backs up **all content your account can access** (moderator/admin access provides more complete backups)
- **Crawls the site** (not JSON export)
- Outputs **raw JSON + threaded HTML** (not styled archive)
- Includes **attachment reprocessing** for failed downloads

**Recent Improvements (v2.0):**
- ✅ External URL filtering (only downloads from learn.redhat.com)
- ✅ Automatic file extension detection from Content-Type headers
- ✅ Reprocessing script for fixing incomplete backups
- ✅ Better authentication handling and error reporting

### Group Hub Backup (backup_groups.py)

**NEW!** Backup course-specific discussion groups (RH124, RH134, RH294, etc.):

```bash
# Install Playwright (one-time setup)
uv pip install playwright
uv run playwright install chromium

# Backup all group hubs (do NOT use --fast to ensure threaded replies are captured)
uv run python backup_groups.py --auto

# Backup specific groups only
uv run python backup_groups.py --auto --groups "RH124" "RH134" "RH294"
```

**Important:** Do NOT use `--fast` mode for group backups - it may cause Playwright to miss JavaScript-rendered threaded replies.

This will:
1. Open a browser for you to log in
2. Discover all available group hubs from https://learn.redhat.com/t5/grouphubs/page
3. Crawl each group's discussions and content
4. Download all messages, images, and attachments
5. Generate HTML pages for offline viewing

**Key features:**
- Backs up **course discussion groups** (separate from main boards)
- Requires **valid account** (not moderator access)
- **Crawls group hubs** (not main community boards)
- Outputs **JSON + threaded HTML** for offline viewing
- Supports **selective backup** of specific groups

**Estimated time:** 2-4 hours for all groups, 15-30 minutes for specific groups

---

## Documentation

### Main Guides
- **[QUICKSTART_FULL_BACKUP.md](QUICKSTART_FULL_BACKUP.md)** - ⚡ **Quick Start: Full site backup in 3 steps!**
- **[QUICKSTART_GROUPS.md](QUICKSTART_GROUPS.md)** - ⚡ **Quick Start: Group hub backup in 3 steps!**
- **[GROUP_BACKUP_GUIDE.md](GROUP_BACKUP_GUIDE.md)** - 📚 **Complete guide for backing up group hubs (course groups)**
- **[USER_GUIDE.md](USER_GUIDE.md)** - Complete guide for `export_community.py` (personal posts)
- **[COMPLETE_BACKUP_GUIDE.md](COMPLETE_BACKUP_GUIDE.md)** - Comprehensive guide for `rhlc-backup.py` (full site backup)
- **[BACKUP_GUIDE.md](BACKUP_GUIDE.md)** - Original backup guide (still valid)

### Specialized Guides
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - 🔧 **Complete troubleshooting guide for common issues**
- **[ATTACHMENT_REPROCESSING_GUIDE.md](ATTACHMENT_REPROCESSING_GUIDE.md)** - ⚠️ **Fix corrupted/missing attachments in existing backups**
- **[ATTACHMENT_FIX_NOTES.md](ATTACHMENT_FIX_NOTES.md)** - Technical details on attachment fixes
- **[BACKUP_STRATEGY.md](BACKUP_STRATEGY.md)** - Backup planning and strategies

### Quick Reference

| Task | Script | Command |
|------|--------|---------|
| Export my posts | `export_community.py` | `uv run export_community.py --auto` |
| **Backup entire site (FAST)** | `rhlc-backup.py` | `uv run python rhlc-backup.py --auto --fast` |
| **Backup group hubs** | `backup_groups.py` | `uv run python backup_groups.py --auto` |
| Backup specific groups | `backup_groups.py` | `uv run python backup_groups.py --auto --groups "RH124" "RH134"` |
| Backup entire site (slow) | `rhlc-backup.py` | `uv run python rhlc-backup.py --auto` |
| Export with saved cookies | `export_community.py` | `uv run export_community.py --cookies cookies.txt` |
| Backup specific boards | `rhlc-backup.py` | `uv run python rhlc-backup.py --auto --fast --boards "Board Name"` |
| **Fix corrupted attachments (full backup)** | `reprocess_attachments.py` | `uv run python reprocess_attachments.py --backup-dir backup_20260314_123456 --auto` |
| **Fix corrupted media (group backup)** | `reprocess_groups.py` | `uv run python reprocess_groups.py --backup-dir groups_backup_20260314_123456 --auto` |
| Regenerate HTML (full backup) | `regenerate_html.py` | `uv run python regenerate_html.py backup_20260314_123456` |
| Regenerate HTML (group backup) | `regenerate_groups_html.py` | `uv run python regenerate_groups_html.py groups_backup_20260314_123456` |
| Check for corruption | `count_corrupted.py` | `uv run python count_corrupted.py` |
| Test corruption detection | `test_corruption_detection.py` | `uv run python test_corruption_detection.py` |

---

## New Features

### Auto-Expanding Navigation (v2.3.0)
When viewing threads in the HTML backup, the board containing that thread automatically expands when you return to the index page. This provides seamless navigation without losing your place.

**How it works:**
- Click any thread link → view thread → browser back button
- The board you were viewing automatically expands
- All manually expanded boards remain expanded
- State persists across browser sessions

**Clear navigation state:**
```javascript
// Open browser console (F12) and run:
localStorage.clear()
```

### Automatic Corruption Detection (v2.3.0)
The reprocessing script now automatically detects corrupted attachments (6KB SAML redirect pages) and re-downloads them without manual intervention.

**Features:**
- Detects files < 10KB with SAML authentication markers
- Preserves valid files (no unnecessary re-downloads)
- Adds missing file extensions from Content-Type headers
- Provides detailed progress logging

**Usage:**
```bash
uv run python reprocess_attachments.py --backup-dir backup_20260314_123456 --auto
```

### Smart Attachment Detection (v2.3.0)
HTML generation now checks for attachments on disk even if they're not in the mapping file, ensuring all re-downloaded attachments display correctly.

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
- ✅ Preserve all accessible community content
- ✅ Get structured JSON data for analysis
- ✅ Create incremental backups
- 💡 **Note:** Moderator/admin access provides more complete backups, but any valid account can backup accessible content

### Use `backup_groups.py` if you want to:
- ✅ Backup course discussion groups (RH124, RH134, etc.)
- ✅ Archive group hub content
- ✅ Preserve course-specific discussions
- ✅ Backup without moderator access
- ✅ Focus on specific course groups

### Use multiple scripts!
Many users combine scripts for comprehensive coverage:
- `export_community.py` for a personal, styled archive
- `rhlc-backup.py` for comprehensive site backups (moderator/admin access provides more complete backups)
- `backup_groups.py` for course discussion groups
