# RHLC Full Site Backup Guide

Complete guide for backing up the entire Red Hat Learning Community (learn.redhat.com) using `rhlc-backup.py`.

## Overview

`rhlc-backup.py` is a comprehensive backup tool that uses the Khoros Community REST API v2 to download all accessible content from learn.redhat.com. Unlike `export_community.py` which only exports your personal posts, this script can backup the entire community site (subject to your access permissions).

## Features

- **Complete Site Backup**: Downloads all boards, categories, and messages you have access to
- **Authenticated Access**: Uses your account credentials to access all content (moderator/admin access provides more complete backups)
- **Media Downloads**: Downloads all images and attachments
- **Structured Output**: Saves data in both JSON and HTML formats
- **Rate Limiting**: Respects API rate limits to avoid overloading the server
- **Incremental Backups**: Can backup only content since a specific date
- **Selective Backups**: Can backup specific boards only

## Requirements

### System Requirements
- Python 3.8 or higher
- Internet connection
- Valid Red Hat SSO account (moderator/admin access provides more complete backups)

### Python Dependencies
```bash
# Install dependencies
uv pip install requests beautifulsoup4 lxml playwright

# Install Playwright browser (for authentication)
uv run playwright install chromium
```

## Quick Start

### Option 1: Automatic Login (Recommended)
```bash
# Full backup with automatic browser login
uv run rhlc-backup.py --auto
```

This will:
1. Open a browser window
2. Let you log in to learn.redhat.com
3. Save your session cookies
4. Download all accessible content

### Option 2: Using Exported Cookies
```bash
# Export cookies from your browser first (see below)
uv run rhlc-backup.py --cookies cookies.txt
```

## Authentication Methods

### Method 1: Automatic Browser Login (--auto)

The easiest method. The script opens a browser where you log in normally:

```bash
uv run rhlc-backup.py --auto
```

**Steps:**
1. Browser window opens at learn.redhat.com
2. Click "Sign In" and log in with your Red Hat account
3. Wait until fully logged in
4. Return to terminal and press Enter
5. Script automatically captures cookies and proceeds

**Advantages:**
- No manual cookie export needed
- Cookies are automatically saved for future use
- Works on any system with a display

### Method 2: Manual Cookie Export (--cookies)

Export cookies from your browser manually:

**Steps:**
1. Log in to https://learn.redhat.com in Chrome/Firefox
2. Install "Cookie-Editor" browser extension
3. Click the extension icon
4. Click "Export" → Choose "Netscape" format
5. Save as `cookies.txt`
6. Run: `uv run rhlc-backup.py --cookies cookies.txt`

**Advantages:**
- Works on headless servers (no display needed)
- Can be automated in scripts
- Cookies can be reused across multiple runs

## Usage Examples

### Basic Full Backup
```bash
# Backup everything you have access to
uv run rhlc-backup.py --auto
```

### Backup to Specific Directory
```bash
# Save backup to custom location
uv run rhlc-backup.py --auto --output /path/to/backup
```

### Backup Specific Boards Only
```bash
# Only backup specific boards
uv run rhlc-backup.py --auto --boards "Red Hat Learning" "General Discussion"
```

### Incremental Backup (Since Date)
```bash
# Only backup content posted since January 1, 2024
uv run rhlc-backup.py --auto --since 2024-01-01
```

### Test Run (Limited Messages)
```bash
# Download only 100 messages for testing
uv run rhlc-backup.py --auto --max-messages 100
```

### Skip Media Downloads
```bash
# Skip images and attachments (faster, smaller backup)
uv run rhlc-backup.py --auto --skip-images --skip-attachments
```

### JSON Only (No HTML)
```bash
# Save only raw JSON data, skip HTML generation
uv run rhlc-backup.py --auto --json-only
```

### Reuse Saved Cookies
```bash
# After first run with --auto, cookies are saved
# Subsequent runs can use the saved cookies
uv run rhlc-backup.py --cookies cookies.txt
```

## Command Line Options

### Authentication Options
- `--auto` - Automatic browser login and save cookies
- `--cookies FILE` - Use exported cookies from file
- `--save-cookies` - Save session cookies to cookies.txt

### Content Selection
- `--boards BOARD [BOARD ...]` - Only backup specific boards
- `--since YYYY-MM-DD` - Only backup content since date
- `--max-messages N` - Limit total messages (for testing)

### Output Options
- `--output DIR` - Output directory (default: backup_YYYYMMDD_HHMMSS)
- `--skip-images` - Skip downloading images
- `--skip-attachments` - Skip downloading attachments
- `--skip-users` - Skip downloading user profiles
- `--json-only` - Only save raw JSON, skip HTML generation

## Output Structure

After running, you'll get a directory structure like this:

```
backup_20260312_165530/
├── json/
│   ├── structure.json      # Community structure (categories, boards)
│   ├── messages.json        # All messages with metadata
│   └── media_mapping.json   # URLs to local file mappings
├── images/
│   ├── image_123.png
│   ├── image_456.jpg
│   └── ...
├── attachments/
│   ├── document.pdf
│   ├── spreadsheet.xlsx
│   └── ...
├── html/
│   └── index.html          # Browsable HTML index
└── errors.log              # Any errors encountered
```

### JSON Files

**structure.json**: Contains the community hierarchy
```json
{
  "categories": [...],
  "boards": [
    {
      "id": "board-id",
      "title": "Board Name",
      "description": "...",
      ...
    }
  ],
  "nodes": {...}
}
```

**messages.json**: All downloaded messages
```json
[
  {
    "id": "message-id",
    "subject": "Message Title",
    "body": "<html>...</html>",
    "author": {...},
    "post_time": "2024-01-01T12:00:00Z",
    "attachments": [...],
    "_board_title": "Board Name",
    "_board_id": "board-id"
  },
  ...
]
```

**media_mapping.json**: Maps URLs to downloaded files
```json
{
  "images": {
    "https://learn.redhat.com/.../image-id/123/...": "image_123.png"
  },
  "attachments": {
    "https://learn.redhat.com/.../attachment.pdf": "attachment.pdf"
  }
}
```

## Performance Considerations

### Rate Limiting
The script includes built-in rate limiting:
- 0.5 second delay between API requests
- 100 items per API request (batch size)

These can be adjusted in the script if needed:
```python
REQUEST_DELAY = 0.5  # seconds between requests
BATCH_SIZE = 100     # items per request
```

### Backup Size Estimates
- **Text only** (--skip-images --skip-attachments): ~10-50 MB
- **With images**: +500 MB - 5 GB (depends on content)
- **With attachments**: +100 MB - 10 GB (depends on files)
- **Full backup**: 1-20 GB (typical community)

### Backup Duration Estimates
- **1,000 messages**: ~10-15 minutes
- **10,000 messages**: ~1-2 hours
- **100,000 messages**: ~10-20 hours

Times vary based on:
- Number of images/attachments
- Network speed
- API rate limits
- Server load

## Troubleshooting

### Authentication Issues

**Problem**: "Authentication failed" or 401 errors
**Solution**:
1. Verify you're logged in as a moderator/admin
2. Try re-exporting cookies
3. Use `--auto` to log in fresh
4. Check if your session expired

### Display Server Issues (Headless Systems)

**Problem**: "No display server" error with `--auto`
**Solutions**:

1. **Use Xvfb (virtual display)**:
```bash
sudo dnf install xorg-x11-server-Xvfb
xvfb-run uv run rhlc-backup.py --auto
```

2. **Set DISPLAY variable**:
```bash
export DISPLAY=:0
uv run rhlc-backup.py --auto
```

3. **Use cookie export method**:
```bash
# On a machine with GUI, export cookies
# Then transfer cookies.txt to headless server
uv run rhlc-backup.py --cookies cookies.txt
```

### API Access Issues

**Problem**: "Access denied" or 403 errors
**Solution**:
- Verify you have moderator/admin permissions
- Some boards may be restricted even for moderators
- Check with community administrators

### Incomplete Backups

**Problem**: Not all content is downloaded
**Solution**:
1. Check `errors.log` for specific failures
2. Verify your access permissions
3. Try backing up specific boards individually
4. Use `--max-messages` to test smaller batches

### Memory Issues

**Problem**: Script crashes with large backups
**Solution**:
1. Use `--max-messages` to limit batch size
2. Backup specific boards separately
3. Use `--skip-images` and `--skip-attachments` initially
4. Increase system memory or use swap

## Advanced Usage

### Scheduled Backups

Create a cron job for regular backups:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/rhlc_save && uv run rhlc-backup.py --cookies cookies.txt --output /backups/daily
```

### Incremental Backups

Backup only new content since last backup:

```bash
# First backup
uv run rhlc-backup.py --auto --output backup_full

# Later, backup only new content
uv run rhlc-backup.py --cookies cookies.txt --since 2024-03-01 --output backup_incremental
```

### Selective Board Backups

Backup different boards to different locations:

```bash
# Backup technical boards
uv run rhlc-backup.py --cookies cookies.txt \
  --boards "Red Hat Learning" "Technical Discussion" \
  --output backup_technical

# Backup community boards
uv run rhlc-backup.py --cookies cookies.txt \
  --boards "General Discussion" "Announcements" \
  --output backup_community
```

### Combining with export_community.py

Use both scripts for comprehensive backups:

```bash
# 1. Backup entire site (moderator view)
uv run rhlc-backup.py --auto --output site_backup

# 2. Export your personal posts (detailed HTML)
uv run export_community.py --auto --output my_posts
```

## API Endpoints Used

The script uses these Khoros REST API v2 endpoints:

- `GET /api/2.0/categories` - List all categories
- `GET /api/2.0/boards` - List all boards
- `GET /api/2.0/boards/id/{id}/messages` - Get messages from board
- `GET /api/2.0/messages/id/{id}` - Get message details
- `GET /api/2.0/users/id/{id}` - Get user profile

## Security Considerations

### Cookie Security
- Cookies contain authentication tokens
- Store `cookies.txt` securely (chmod 600)
- Don't commit cookies to version control
- Rotate cookies regularly

### Backup Security
- Backups may contain sensitive information
- Store backups in secure locations
- Encrypt backups if needed
- Follow your organization's data policies

### Access Control
- Only backup content you're authorized to access
- Respect community privacy policies
- Don't share backups without permission

## Comparison: rhlc-backup.py vs export_community.py

| Feature | export_community.py | rhlc-backup.py |
|---------|-------------------|----------------|
| **Scope** | Your posts only | Entire site |
| **Access Required** | Regular user | Moderator/admin |
| **Data Source** | JSON export | REST API |
| **HTML Output** | Detailed, styled | Basic index |
| **Speed** | Fast (small dataset) | Slower (large dataset) |
| **Use Case** | Personal archive | Site backup |

**Recommendation**: Use both!
- `export_community.py` for your personal archive
- `rhlc-backup.py` for site-wide backups

## Support and Issues

If you encounter issues:

1. Check `errors.log` in the output directory
2. Verify authentication and permissions
3. Try with `--max-messages 10` to test
4. Check network connectivity
5. Review Khoros API documentation

## License

This script is provided as-is for backing up Red Hat Learning Community content. Ensure you have appropriate permissions before backing up community content.

---

**Last Updated**: March 2026
**Script Version**: 1.0.0