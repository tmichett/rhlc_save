# Complete RHLC Backup Guide

Comprehensive guide for backing up the entire Red Hat Learning Community site using `rhlc-backup.py`.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Understanding the Backup Process](#understanding-the-backup-process)
4. [Authentication Methods](#authentication-methods)
5. [Running Your First Backup](#running-your-first-backup)
6. [Output Structure](#output-structure)
7. [Reprocessing Attachments](#reprocessing-attachments)
8. [Incremental Backups](#incremental-backups)
9. [Advanced Options](#advanced-options)
10. [Troubleshooting](#troubleshooting)
11. [Best Practices](#best-practices)

---

## Prerequisites

### Required Access
- **Moderator or Admin access** to learn.redhat.com
- Active Red Hat SSO account

### Software Requirements
- **uv** (recommended) — https://docs.astral.sh/uv/getting-started/installation/
- **Python 3.11+** — uv can install this for you
- **Playwright** — for browser-based authentication
- **git** — to clone the repository

### Installation

```bash
# Clone the repository
git clone https://github.com/tmichett/rhlc_save.git
cd rhlc_save

# Install Python 3.11+ with uv (if needed)
uv python install 3.11

# Install dependencies
uv sync

# Install Playwright for authentication
uv pip install playwright
uv run playwright install chromium
```

---

## Quick Start

### First-Time Backup (RECOMMENDED: Use Fast Mode)

```bash
# Fast mode: Skip browser rendering (7-8 hours instead of 50+ hours for ~50K messages)
uv run python rhlc-backup.py --auto --fast
```

This will:
1. Open a browser window for you to log in
2. Wait for you to press Enter after logging in
3. Crawl the entire site structure
4. Download all boards, messages, images, and attachments (WITHOUT browser rendering)
5. Generate HTML pages and JSON data
6. Save everything to `backup_YYYYMMDD_HHMMSS/`

**Why --fast is recommended:**
- Attachments are in the regular HTML (browser rendering not needed)
- **7-8 hours instead of 50+ hours** for ~50,000 messages
- Finds all attachments (proven by testing - same 114 attachments found)
- No data loss compared to browser mode

### Subsequent Backups

```bash
# Use saved cookies and fast mode
uv run python rhlc-backup.py --cookies cookies.txt --fast
```

### Full Browser Mode (NOT Recommended)

```bash
# Only use if you suspect missing data (takes 50+ hours for ~50K messages!)
uv run python rhlc-backup.py --auto
```

**Note:** Browser mode was tested and found the same attachments as fast mode, but takes 7x longer.

---

## Understanding the Backup Process

### What Gets Backed Up

The backup script captures:

1. **Site Structure**
   - All boards and categories
   - Board descriptions and metadata
   - Category hierarchies

2. **Content**
   - All messages (posts and replies)
   - Message bodies with HTML formatting
   - Author information
   - Post timestamps
   - Thread relationships

3. **Media**
   - All embedded images
   - File attachments (PDFs, documents, etc.)
   - Proper file extensions based on Content-Type

4. **Generated Output**
   - Threaded HTML pages for each discussion
   - Main index page with board navigation
   - JSON data for programmatic access

### What Doesn't Get Backed Up

- User profiles (except author names in posts)
- Private messages
- External links (e.g., nvidia.com PDFs referenced in posts)
- User avatars
- Site configuration and themes

### Backup Size Estimates

Typical backup sizes:
- **Small community** (< 1,000 posts): 100-500 MB
- **Medium community** (1,000-10,000 posts): 500 MB - 5 GB
- **Large community** (> 10,000 posts): 5-50+ GB

Time estimates (with `--fast` mode):
- **Small** (< 1,000 messages): 10-30 minutes
- **Medium** (1,000-10,000 messages): 30 minutes - 2 hours
- **Large** (10,000-50,000 messages): 2-8 hours
- **Very Large** (50,000+ messages): 7-10 hours

Time estimates (WITHOUT `--fast`, browser mode):
- **Small** (< 1,000 messages): 1-2 hours
- **Medium** (1,000-10,000 messages): 5-15 hours
- **Large** (10,000-50,000 messages): 15-30 hours
- **Very Large** (50,000+ messages): 50-60 hours (2+ days!)

**Always use `--fast` mode** - it finds the same attachments but is 7x faster.

---

## Authentication Methods

### Method 1: Browser Login (--auto)

**Recommended for first-time use**

```bash
uv run python rhlc-backup.py --auto
```

**What happens:**
1. Opens Chromium browser at learn.redhat.com
2. You manually log in with Red Hat SSO
3. Press Enter in terminal when logged in
4. Script captures cookies and proceeds
5. Optionally saves cookies for future use

**Advantages:**
- Most reliable for initial setup
- Works with any authentication method (SSO, 2FA, etc.)
- Visual confirmation of login success

**Disadvantages:**
- Requires GUI/display server
- Manual interaction needed

### Method 2: Cookie File (--cookies)

**Recommended for repeated backups**

```bash
uv run python rhlc-backup.py --cookies cookies.txt
```

**How to get cookies:**

1. **Option A: Use --auto --save-cookies**
   ```bash
   uv run python rhlc-backup.py --auto --save-cookies
   ```
   Cookies are automatically saved to `cookies.txt`

2. **Option B: Export from browser**
   - Install Cookie-Editor extension ([Chrome](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) / [Firefox](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/))
   - Log in to learn.redhat.com
   - Click extension → Export → Netscape format
   - Save as `cookies.txt`

**Advantages:**
- No GUI required
- Faster (no browser startup)
- Can be automated

**Disadvantages:**
- Cookies expire (typically 1-7 days)
- Need to refresh periodically

---

## Running Your First Backup

### Step-by-Step Guide

#### Step 1: Authenticate and Save Cookies

```bash
uv run python rhlc-backup.py --auto --save-cookies
```

**What to do:**
1. Browser window opens at learn.redhat.com
2. Click "Sign In" in top-right corner
3. Complete Red Hat SSO login
4. Wait for page to fully load
5. Return to terminal and press Enter

The script will save your cookies to `cookies.txt` for future use.

#### Step 2: Monitor Progress

The script will display progress as it runs:

```
12:34:56 [INFO] Starting RHLC backup...
12:34:56 [INFO] Discovering site structure...
12:35:12 [INFO] Found 15 boards
12:35:12 [INFO] Crawling boards for messages...
12:35:45 [INFO] Found 1,234 messages across all boards
12:36:00 [INFO] Downloading 1,234 messages...
12:36:15 [INFO]   Downloaded 100/1234 messages
...
12:45:30 [INFO] Downloading 456 images...
12:50:00 [INFO] Downloading 89 attachments...
12:55:00 [INFO] Generating HTML pages...
12:56:00 [INFO] Backup complete!
```

#### Step 3: Verify Output

```bash
# Check backup directory
ls -la backup_*/

# View main index
open backup_*/index.html  # macOS
xdg-open backup_*/index.html  # Linux
```

---

## Output Structure

After a successful backup, you'll have:

```
backup_20260314_123456/
├── index.html                    # Main index page - open this first
├── threads/                      # Individual discussion pages
│   ├── thread_001.html
│   ├── thread_002.html
│   └── ...
├── images/                       # All downloaded images
│   ├── image_abc123.jpg
│   ├── image_def456.png
│   └── ...
├── attachments/                  # All file attachments
│   ├── User_Guide.pdf
│   ├── Release_Notes.docx
│   └── ...
├── json/                         # Raw data for programmatic access
│   ├── boards.json              # Board structure
│   ├── messages.json            # All messages (pretty-printed)
│   ├── messages.jsonl           # All messages (line-delimited)
│   └── media_mapping.json       # URL to filename mappings
└── error_log.txt                # Only created if errors occurred
```

### Key Files

#### index.html
- Main entry point for browsing the backup
- Lists all boards and categories
- Links to individual thread pages
- Shows statistics (total posts, replies, etc.)

#### threads/*.html
- One file per discussion thread
- Shows original post and all replies
- Preserves threading structure
- Includes embedded images and attachments
- Syntax highlighting for code blocks

#### json/messages.json
- Complete message data in JSON format
- Useful for:
  - Searching content programmatically
  - Analyzing post patterns
  - Migrating to another platform
  - Custom reporting

---

## Reprocessing Attachments

If your initial backup had issues with attachments (authentication timeouts, missing extensions, external URLs), you can reprocess them without re-downloading everything.

### When to Reprocess

Reprocess attachments if you see:
- Files with missing extensions (can't be opened)
- 401/403 authentication errors in logs
- External URLs that shouldn't have been downloaded
- Incomplete or corrupted files

### How to Reprocess

```bash
# Reprocess with fresh authentication
uv run python reprocess_attachments.py --backup-dir backup_20260314_123456 --auto

# Or use saved cookies
uv run python reprocess_attachments.py --backup-dir backup_20260314_123456 --cookies cookies.txt

# Force re-download everything
uv run python reprocess_attachments.py --backup-dir backup_20260314_123456 --auto --force
```

### What Reprocessing Does

1. **Reads existing backup data** from `json/messages.json`
2. **Filters out external URLs** (e.g., nvidia.com)
3. **Fixes malformed filenames** (URLs used as filenames)
4. **Adds missing extensions** based on Content-Type headers
5. **Skips existing files** (unless --force is used)
6. **Retries failed downloads** with exponential backoff

### Reprocessing Output

```
09:30:00 [INFO] Loading messages from backup_20260314_123456/json/messages.json
09:30:01 [INFO] Loaded 1,234 messages
09:30:01 [INFO] Skipped 45 external URLs (not from https://learn.redhat.com)
09:30:01 [INFO] Found 89 attachments to process from https://learn.redhat.com
09:30:02 [INFO] Downloading attachments to backup_20260314_123456/attachments
09:30:03 [INFO] [1/89] Processing User_Guide
09:30:03 [INFO]   Added extension .pdf (Content-Type: application/pdf)
09:30:04 [INFO]   ✓ Downloaded User_Guide.pdf (1234567 bytes)
...
09:35:00 [INFO] ============================================================
09:35:00 [INFO] REPROCESSING COMPLETE
09:35:00 [INFO] ============================================================
09:35:00 [INFO] Total attachments: 89
09:35:00 [INFO] Successfully downloaded: 85
09:35:00 [INFO] Skipped (already exist): 2
09:35:00 [INFO] Failed: 2
```

---

## Incremental Backups

For large communities, you may want to perform incremental backups to capture only new content.

### Using --since Flag

```bash
# Backup only posts since January 1, 2024
uv run python rhlc-backup.py --auto --since 2024-01-01

# Backup only posts from the last 7 days
uv run python rhlc-backup.py --auto --since 7d

# Backup only posts from the last 30 days
uv run python rhlc-backup.py --auto --since 30d
```

### Combining Incremental with Full Backups

**Strategy 1: Weekly Full + Daily Incremental**
```bash
# Sunday: Full backup
uv run python rhlc-backup.py --auto --output backup_full_$(date +%Y%m%d)

# Monday-Saturday: Incremental
uv run python rhlc-backup.py --auto --since 1d --output backup_incr_$(date +%Y%m%d)
```

**Strategy 2: Monthly Full + Weekly Incremental**
```bash
# First of month: Full backup
uv run python rhlc-backup.py --auto --output backup_full_$(date +%Y%m)

# Weekly: Incremental
uv run python rhlc-backup.py --auto --since 7d --output backup_incr_$(date +%Y%m%d)
```

---

## Advanced Options

### Limiting Backup Scope

```bash
# Backup specific boards only
uv run python rhlc-backup.py --auto --boards "Lab Engineer Updates" "General Discussion"

# Limit number of pages (for testing)
uv run python rhlc-backup.py --auto --max-pages 10

# Limit number of messages (for testing)
uv run python rhlc-backup.py --auto --max-messages 100
```

### Skipping Content Types

```bash
# Skip images (faster, smaller backup)
uv run python rhlc-backup.py --auto --skip-images

# Skip attachments
uv run python rhlc-backup.py --auto --skip-attachments

# Skip both (JSON only)
uv run python rhlc-backup.py --auto --skip-images --skip-attachments
```

### Custom Output Directory

```bash
# Specify output directory
uv run python rhlc-backup.py --auto --output /path/to/backup

# Use date-based naming
uv run python rhlc-backup.py --auto --output backup_$(date +%Y%m%d)
```

### Combining Options

```bash
# Fast test backup: 10 pages, no media
uv run python rhlc-backup.py --auto --max-pages 10 --skip-images --skip-attachments

# Incremental backup of specific boards
uv run python rhlc-backup.py --auto --since 7d --boards "Lab Engineer Updates"

# Full backup with custom output
uv run python rhlc-backup.py --auto --output /mnt/backups/rhlc_$(date +%Y%m%d)
```

---

## Troubleshooting

### Authentication Issues

#### Problem: 401/403 Errors During Download

**Cause:** Session cookies expired

**Solution:**
```bash
# Re-authenticate with fresh login
uv run python rhlc-backup.py --auto --save-cookies

# Or export fresh cookies from browser
```

#### Problem: "Browser login failed"

**Cause:** Display server not available (headless system)

**Solutions:**

1. **Use Xvfb (virtual display):**
   ```bash
   sudo dnf install xorg-x11-server-Xvfb
   xvfb-run uv run python rhlc-backup.py --auto
   ```

2. **Export cookies from another machine:**
   ```bash
   # On machine with GUI: export cookies
   # Transfer cookies.txt to server
   uv run python rhlc-backup.py --cookies cookies.txt
   ```

3. **Set DISPLAY variable (if using X11):**
   ```bash
   export DISPLAY=:0
   uv run python rhlc-backup.py --auto
   ```

### Download Issues

#### Problem: External URLs Being Downloaded

**Cause:** Old version of script

**Solution:** Update to latest version - external URLs are now automatically filtered

#### Problem: Attachments Missing File Extensions

**Cause:** Old version or authentication timeout

**Solution:**
```bash
# Reprocess attachments with latest version
uv run python reprocess_attachments.py --backup-dir backup_20260314_123456 --auto
```

#### Problem: "No such file or directory" for Attachments

**Cause:** Filename contains full URL path

**Solution:** Use reprocessing script which sanitizes filenames:
```bash
uv run python reprocess_attachments.py --backup-dir backup_20260314_123456 --auto
```

### Performance Issues

#### Problem: Backup Taking Too Long

**Solutions:**

1. **Use incremental backups:**
   ```bash
   uv run python rhlc-backup.py --auto --since 30d
   ```

2. **Skip media for faster JSON-only backup:**
   ```bash
   uv run python rhlc-backup.py --auto --skip-images --skip-attachments
   ```

3. **Backup specific boards only:**
   ```bash
   uv run python rhlc-backup.py --auto --boards "Important Board"
   ```

#### Problem: Running Out of Disk Space

**Solutions:**

1. **Check backup size before starting:**
   ```bash
   # Estimate: ~1-2 MB per message with media
   # 10,000 messages ≈ 10-20 GB
   ```

2. **Skip images/attachments:**
   ```bash
   uv run python rhlc-backup.py --auto --skip-images --skip-attachments
   ```

3. **Use compression:**
   ```bash
   # After backup completes
   tar -czf backup_20260314.tar.gz backup_20260314_123456/
   ```

### HTML Generation Issues

#### Problem: HTML Pages Not Generated

**Cause:** Error during message download

**Solution:**
```bash
# Check error_log.txt for details
cat backup_*/error_log.txt

# Regenerate HTML from existing JSON
uv run python regenerate_html.py --backup-dir backup_20260314_123456
```

#### Problem: Images Not Showing in HTML

**Cause:** Images not downloaded or incorrect paths

**Solution:**
```bash
# Check if images exist
ls -la backup_*/images/

# Re-download images
uv run python rhlc-backup.py --cookies cookies.txt --skip-attachments
```

---

## Best Practices

### Regular Backup Schedule

**Recommended Schedule:**
- **Full backup:** Monthly
- **Incremental backup:** Weekly
- **Critical content:** Daily

**Example Cron Jobs:**
```bash
# Full backup first of month at 2 AM
0 2 1 * * cd /path/to/rhlc_save && uv run python rhlc-backup.py --cookies cookies.txt --output /backups/full_$(date +\%Y\%m)

# Incremental backup every Sunday at 3 AM
0 3 * * 0 cd /path/to/rhlc_save && uv run python rhlc-backup.py --cookies cookies.txt --since 7d --output /backups/incr_$(date +\%Y\%m\%d)
```

### Cookie Management

1. **Save cookies after first login:**
   ```bash
   uv run python rhlc-backup.py --auto --save-cookies
   ```

2. **Refresh cookies monthly:**
   ```bash
   # Re-authenticate and update cookies.txt
   uv run python rhlc-backup.py --auto --save-cookies
   ```

3. **Keep cookies secure:**
   ```bash
   chmod 600 cookies.txt
   ```

### Storage Management

1. **Compress old backups:**
   ```bash
   tar -czf backup_202603.tar.gz backup_20260314_*/
   rm -rf backup_20260314_*/
   ```

2. **Keep multiple backup generations:**
   - Current month: Uncompressed
   - Last 3 months: Compressed
   - Older: Archived offsite

3. **Verify backup integrity:**
   ```bash
   # Check JSON is valid
   python3 -c "import json; json.load(open('backup_*/json/messages.json'))"
   
   # Check HTML opens
   open backup_*/index.html
   ```

### Monitoring and Alerts

1. **Check for errors after each backup:**
   ```bash
   if [ -f backup_*/error_log.txt ]; then
       echo "Backup completed with errors"
       cat backup_*/error_log.txt
   fi
   ```

2. **Verify backup size:**
   ```bash
   du -sh backup_*/
   ```

3. **Count downloaded items:**
   ```bash
   echo "Messages: $(jq length backup_*/json/messages.json)"
   echo "Images: $(ls backup_*/images/ | wc -l)"
   echo "Attachments: $(ls backup_*/attachments/ | wc -l)"
   ```

---

## Related Documentation

- **[README.md](README.md)** - Project overview and quick start
- **[BACKUP_GUIDE.md](BACKUP_GUIDE.md)** - Original backup guide
- **[ATTACHMENT_REPROCESSING_GUIDE.md](ATTACHMENT_REPROCESSING_GUIDE.md)** - Detailed attachment reprocessing guide
- **[USER_GUIDE.md](USER_GUIDE.md)** - Personal posts export guide (export_community.py)

---

## Support and Contributing

### Getting Help

1. Check this guide and related documentation
2. Review error logs in `backup_*/error_log.txt`
3. Open an issue on GitHub with:
   - Error messages
   - Command used
   - System information (OS, Python version)

### Contributing

Contributions welcome! Areas for improvement:
- Additional authentication methods
- Performance optimizations
- Better error handling
- UI improvements
- Additional export formats

---

## Changelog

### Version 2.0 (March 2024)
- ✅ Fixed external URL filtering
- ✅ Added Content-Type based file extension detection
- ✅ Created reprocessing script for failed attachments
- ✅ Improved authentication handling
- ✅ Better error logging and reporting

### Version 1.0 (Initial Release)
- Basic site backup functionality
- Browser-based authentication
- JSON and HTML output
- Image and attachment downloads