# Group Hub Backup Guide

This guide explains how to backup Red Hat Learning Community Group Hubs (course discussion groups) using `backup_groups.py`.

## What Are Group Hubs?

Group hubs are course-specific discussion groups on learn.redhat.com, separate from the main community boards. Examples include:

- **RH124** - Red Hat System Administration I
- **RH134** - Red Hat System Administration II  
- **RH294** - Red Hat System Administration III
- And many more course-specific groups

These groups are found at: https://learn.redhat.com/t5/grouphubs/page
## ⚠️ Important: Rate Limiting

**DO NOT run multiple backup scripts simultaneously!** The Red Hat Learning Community site has aggressive rate limiting:

- Running full backup (`rhlc-backup.py`) and group backup (`backup_groups.py`) at the same time will:
  - Double the request rate to the server
  - Trigger frequent 429 (rate limit) errors
  - Potentially get your IP temporarily blocked
  - Significantly slow down both backups
  - Risk incomplete or corrupted data

**Best Practice:** Run backups sequentially, one at a time:
1. Complete the full site backup first
2. Wait for it to finish completely
3. Then run the group backup (or vice versa)

If you encounter rate limiting (429 errors), the scripts will automatically retry with progressive delays (5s, 10s, 15s). However, running multiple scripts simultaneously makes this much worse.


## Quick Start

### 1. Install Prerequisites

```bash
# Install Playwright (one-time setup)
uv pip install playwright
uv run playwright install chromium
```

### 2. Run Full Group Backup

Backup all group hubs (without --fast to ensure threaded replies are captured):

```bash
uv run python backup_groups.py --auto
```

**Important:** Do NOT use `--fast` mode for group backups. The `--fast` flag reduces delays that are necessary for Playwright to properly render JavaScript-loaded threaded replies. Using `--fast` may result in missing reply content.

This will:
1. Open a browser for you to log in
2. Discover all available group hubs
3. Crawl each group's discussions
4. Download all messages and content
5. Generate HTML pages for offline viewing

**Estimated time:** 2-4 hours depending on number of groups and content

### 3. Backup Specific Groups

To backup only specific groups (much faster):

```bash
uv run python backup_groups.py --auto --groups "RH124" "RH134" "RH294"
```

This will only backup groups matching the specified names.

**Note:** Avoid using `--fast` to ensure all threaded replies are properly captured.

## Authentication Options

### Option A: Browser Login (Recommended)

```bash
uv run python backup_groups.py --auto
```

- Opens a browser window
- You log in manually with your Red Hat account
- Cookies are captured automatically

### Option B: Use Saved Cookies

If you've already logged in once:

```bash
uv run python backup_groups.py --cookies cookies.txt
```

### Option C: Save Cookies for Future Use

```bash
uv run python backup_groups.py --auto --save-cookies
```

This saves your session cookies to `cookies.txt` for future runs.

## Command Line Options

### Authentication
- `--auto` - Use Playwright to log in automatically
- `--cookies FILE` - Use exported cookies from browser
- `--save-cookies` - Save session cookies for future use

### Content Selection
- `--groups NAME [NAME...]` - Backup specific groups only
  - Example: `--groups "RH124" "RH134"`
- `--max-pages N` - Limit pages to crawl per group (for testing)
- `--max-messages N` - Limit total messages to download (for testing)

### Performance
- `--fast` - Use faster crawling with reduced delays (**NOT recommended for groups**)
  - Reduces request delay from 0.5s to 0.2s
  - May cause Playwright to miss JavaScript-rendered threaded replies
  - Only use if you don't need complete reply threads

### Output Options
- `--output DIR` - Output directory (default: `groups_backup_YYYYMMDD_HHMMSS`)
- `--skip-images` - Skip downloading images
- `--skip-attachments` - Skip downloading attachments

## Output Structure

```
groups_backup_20260314_123456/
├── index.html               # Top-level landing page (open this!)
├── groups.json              # List of all discovered groups
├── group_RH124RedHat....json  # Messages for RH124 group
├── group_RH134RedHat....json  # Messages for RH134 group
├── all_messages.json        # All messages combined
├── html/                    # HTML pages for viewing
│   ├── groups_index.html   # Main content index
│   ├── thread_*.html       # Individual thread pages
│   └── ...
└── errors.log              # Error log (if any errors occurred)
```

**Note:** Open `index.html` in your browser to start browsing the backup. It provides a convenient landing page with backup statistics and a link to the main content index.

## Usage Examples

### Example 1: Full Backup (All Groups)

```bash
uv run python backup_groups.py --auto
```

**What it does:**
- Opens browser to discover all available group hubs (automatic pagination)
- Backs up every group you have access to
- Uses standard delays to ensure threaded replies are captured

**When to use:** 
- First-time backup
- Comprehensive archive needed
- You want everything

### Example 2: Specific Course Groups

```bash
uv run python backup_groups.py --auto --groups "RH124" "RH134" "RH294"
```

**What it does:**
- Only backs up the specified groups
- Much faster than full backup
- Focused on specific courses

**When to use:**
- You only need certain courses
- Quick targeted backup
- Testing the script

### Example 3: Test Run (Limited)

```bash
uv run python backup_groups.py --auto --max-pages 2 --max-messages 50
```

**What it does:**
- Limits to 2 pages per group
- Stops after 50 total messages
- Quick test of functionality

**When to use:**
- Testing the script
- Verifying authentication
- Checking output format

### Example 4: Using Saved Cookies

```bash
# First run - save cookies
uv run python backup_groups.py --auto --save-cookies

# Subsequent runs - use saved cookies
uv run python backup_groups.py --cookies cookies.txt
```

**What it does:**
- First run saves your session
- Later runs reuse the session
- No need to log in again

**When to use:**
- Running multiple backups
- Automated/scheduled backups
- Avoiding repeated logins

## Viewing the Backup

After the backup completes:

1. Open the HTML index page:
   ```bash
   open groups_backup_20260314_123456/html/index.html
   ```

2. Browse groups and threads in your web browser


## Reprocessing Existing Backups

The `reprocess_groups.py` script handles both images and attachments, with automatic corruption detection and HTML regeneration. This is useful when your initial backup had session timeout issues or missing media.

### Full Reprocessing (Images + Attachments + HTML)

```bash
uv run python reprocess_groups.py --backup-dir groups_backup_20260314_123456 --auto
```

**What it does:**
1. Scans for missing or corrupted images
2. Scans for missing or corrupted attachments  
3. Detects SAML redirect corruption (6KB HTML files)
4. Re-downloads corrupted/missing files
5. Regenerates all HTML pages with proper media references

**When to use:**
- After a backup with session timeout issues
- When attachments show as "not downloaded"
- When images are missing or corrupted
- After manually deleting corrupted files

### Attachments Only (Skip Images)

```bash
uv run python reprocess_groups.py --backup-dir groups_backup_20260314_123456 --auto --skip-images
```

**What it does:**
- Only processes attachments
- Skips image processing entirely
- Regenerates HTML with attachment references

**When to use:**
- Images are fine, only attachments need fixing
- Faster processing when images aren't needed
- Parallel to `reprocess_attachments.py` for full backups

### Images Only (Skip Attachments)

```bash
uv run python reprocess_groups.py --backup-dir groups_backup_20260314_123456 --auto --skip-attachments
```

**What it does:**
- Only processes images
- Skips attachment processing entirely
- Regenerates HTML with image references

**When to use:**
- Attachments are fine, only images need fixing
- Faster processing when attachments aren't needed

### Force Re-download Everything

```bash
uv run python reprocess_groups.py --backup-dir groups_backup_20260314_123456 --auto --force
```

**What it does:**
- Re-downloads ALL media files, even if they exist
- Useful for fixing file corruption issues
- Takes longer but ensures fresh downloads

**When to use:**
- Suspect widespread corruption
- Want to ensure all files are fresh
- Previous reprocessing didn't fix issues

### Reprocessing Options Reference

| Option | Description |
|--------|-------------|
| `--auto` | Use browser login for authentication |
| `--cookies FILE` | Use saved cookies file |
| `--force` | Re-download all media (even if they exist) |
| `--skip-images` | Skip image processing (attachments only) |
| `--skip-attachments` | Skip attachment processing (images only) |
| `--fast` | Use faster processing (**not recommended - may miss replies**) |

### Reprocessing vs Regenerating HTML

**Use `reprocess_groups.py` when:**
- ✅ You need to download missing/corrupted media
- ⚠️ **Requires authentication** (browser login)
- ✅ Handles both images and attachments
- ✅ Automatically regenerates HTML after downloading

**Use `regenerate_groups_html.py` when:**
- ✅ Media files are already downloaded and fine
- ✅ **No authentication required** (works offline)
- ✅ Quick HTML formatting fixes
- ✅ Just fixing the KeyError: 'subject' issue
- See "Regenerating HTML Only" section below

**Why does reprocessing need login?**
The reprocessing script downloads images and attachments from learn.redhat.com, which requires authentication. If you only need to fix the HTML (like the KeyError: 'subject' issue), use `regenerate_groups_html.py` instead - it works entirely offline using the existing JSON data.

3. All content is available offline

## Differences from rhlc-backup.py

| Feature | rhlc-backup.py | backup_groups.py |
|---------|----------------|------------------|
| **Target** | Main community boards | Group hubs (course groups) |
| **URL** | /t5/forums/* | /t5/grouphubs/* |
| **Access** | Valid account (moderator/admin for complete backup) | Requires valid account |
| **Content** | All accessible boards | Course discussion groups |
| **Use Case** | Full site backup | Course-specific backup |

## Troubleshooting

### "No groups found to backup"

**Cause:** Authentication failed or no access to groups

**Solution:**
1. Verify you're logged in correctly
2. Check that you have access to group hubs
3. Try visiting https://learn.redhat.com/t5/grouphubs/page manually

### "Access denied" errors

**Cause:** Session expired or insufficient permissions

**Solution:**
1. Re-run with `--auto` to get fresh authentication
2. Verify your account has access to the groups
3. Check if you need to accept terms of service

### Slow performance

**Cause:** Default delays are necessary for capturing threaded replies

**Solution:**
1. Backup specific groups instead of all groups
2. Use `--skip-images` or `--skip-attachments` if not needed
3. Run backups during off-peak hours
4. Be patient - proper delays ensure complete data capture

**Note:** While `--fast` mode exists, it is NOT recommended as it may cause Playwright to miss JavaScript-rendered threaded replies.

### Browser won't close after login

**Cause:** Script waiting for confirmation

**Solution:**
1. After logging in, press Enter in the terminal
2. The browser will close automatically
3. The backup will begin

## Best Practices

### 1. Don't Use Fast Mode

**Do NOT use `--fast` mode** for group backups. The reduced delays prevent Playwright from properly capturing JavaScript-rendered threaded replies:

```bash
# Correct - ensures all replies are captured
uv run python backup_groups.py --auto

# Incorrect - may miss threaded replies
uv run python backup_groups.py --auto --fast
```

### 2. Backup Specific Groups

For regular backups, target specific groups:

```bash
uv run python backup_groups.py --cookies cookies.txt --groups "RH124" "RH294"
```

### 3. Save Cookies

Save cookies on first run to avoid repeated logins:

```bash
uv run python backup_groups.py --auto --save-cookies
```

### 4. Test First

Run a test with limits before full backup:

```bash
uv run python backup_groups.py --auto --max-pages 1 --max-messages 10
```

### 5. Regular Backups

Schedule regular backups of active course groups:

```bash
# Weekly backup of current courses
uv run python backup_groups.py --cookies cookies.txt --groups "RH124" "RH134"
```

## Advanced Usage

### Combining with rhlc-backup.py

You can use both scripts for comprehensive coverage:

```bash
# Backup main community boards (requires moderator access)
uv run python rhlc-backup.py --auto --fast

# Backup group hubs (requires valid account)
# Note: Don't use --fast for groups to ensure threaded replies are captured
uv run python backup_groups.py --auto
```

### Custom Output Directory

Organize backups by date or purpose:

```bash
uv run python backup_groups.py --auto --output ./backups/groups_$(date +%Y%m%d)
```

### Filtering by Course Level

Backup only specific course levels:

```bash
# RHCSA courses (RH124, RH134)
uv run python backup_groups.py --auto --groups "RH124" "RH134"

# RHCE courses (RH294)
uv run python backup_groups.py --auto --groups "RH294"
```

## Support

For issues or questions:

1. Check the error log: `groups_backup_*/errors.log`
2. Review the troubleshooting section above
3. Open an issue on GitHub with:
   - Command you ran
   - Error messages
   - Output from `errors.log`

## Regenerating HTML Only

### Option 1: Using regenerate_groups_html.py (no authentication needed)

If you just want to regenerate HTML from existing data without any authentication:

```bash
uv run python regenerate_groups_html.py groups_backup_20260314_123456
```

This is the simplest option when:
- You've manually fixed media files
- You just need to update HTML formatting
- You don't want to log in again
- You're making quick HTML changes

### Option 2: Using reprocess_groups.py (requires authentication)

If you want to regenerate HTML and check for missing media:

```bash
uv run python reprocess_groups.py --backup-dir groups_backup_20260314_123456 --auto --skip-images --skip-attachments
```

**Key differences:**
- `regenerate_groups_html.py` - No authentication, just regenerates HTML from existing JSON
- `reprocess_groups.py --skip-images --skip-attachments` - Requires authentication, can check for missing media

## See Also

- [QUICKSTART_FULL_BACKUP.md](QUICKSTART_FULL_BACKUP.md) - Quick start for full site backup
- [COMPLETE_BACKUP_GUIDE.md](COMPLETE_BACKUP_GUIDE.md) - Complete guide for rhlc-backup.py
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Comprehensive troubleshooting guide
- [ATTACHMENT_REPROCESSING_GUIDE.md](ATTACHMENT_REPROCESSING_GUIDE.md) - Guide for fixing attachments in full backups
- [README.md](README.md) - Main project documentation