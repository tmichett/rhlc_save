# Full Site Backup - Quick Start Guide

Get a complete backup of learn.redhat.com in 3 simple steps!

---

## Prerequisites

- **uv** installed (https://docs.astral.sh/uv/getting-started/installation/)
- **Red Hat SSO account** (moderator/admin access provides more complete backups)
- **~10GB free disk space**

---

## Step 1: Clone and Setup (One-Time)

```bash
# Clone repository
git clone https://github.com/tmichett/rhlc_save.git
cd rhlc_save

# Install dependencies
uv sync

# Install Playwright for browser automation
uv pip install playwright
uv run playwright install chromium
```

---

## Step 2: Run Backup (Recommended - Fast Mode)

```bash
uv run python rhlc-backup.py --auto --fast
```

**What happens:**
1. Browser opens to learn.redhat.com
2. Click "Sign In" and log in with your Red Hat account
3. Press Enter in terminal after logging in
4. Backup runs automatically (7-8 hours)

**Output:**
- `backup_YYYYMMDD_HHMMSS/` directory created
- All messages, boards, images, and attachments downloaded
- HTML pages generated for offline viewing

---

## Step 3: View Your Backup

```bash
# Open in browser
open backup_YYYYMMDD_HHMMSS/index.html
```

Or navigate to the backup directory and double-click `index.html`.

---

## That's It! 🎉

Your complete backup includes:
- ✅ All messages and threads
- ✅ All boards and categories  
- ✅ All images and attachments
- ✅ Searchable HTML interface
- ✅ PDF previews inline
- ✅ Auto-expanding navigation

---

## Common Issues & Solutions

### Issue: Corrupted Attachments (6KB files)

**Symptoms:** Some PDFs are 6KB and won't open

**Fix:**
```bash
# Check for corruption
uv run python count_corrupted.py

# Re-download corrupted files
uv run python reprocess_attachments.py --backup-dir backup_YYYYMMDD_HHMMSS --auto

# Regenerate HTML
uv run python regenerate_html.py backup_YYYYMMDD_HHMMSS
```

### Issue: Backup Taking Too Long (50+ hours)

**Solution:** Use `--fast` mode (already recommended above)
```bash
uv run python rhlc-backup.py --auto --fast
```

This skips browser rendering and completes in 7-8 hours instead of 50+ hours.

### Issue: Browser Won't Open

**Solution:** Install Playwright
```bash
uv pip install playwright
uv run playwright install chromium
```

### Issue: Authentication Errors

**Solution:** Re-run with fresh login
```bash
uv run python rhlc-backup.py --auto --fast
```

---

## Backup Specific Boards Only

```bash
# Single board
uv run python rhlc-backup.py --auto --fast --boards "Lab Engineers"

# Multiple boards
uv run python rhlc-backup.py --auto --fast --boards "Lab Engineers" "Instructors"
```

---

## Incremental Backups

To update an existing backup with new content:

```bash
uv run python rhlc-backup.py --auto --fast --incremental backup_YYYYMMDD_HHMMSS
```

This only downloads new messages since the last backup.

---

## Advanced Options

### Save Cookies for Future Use
```bash
uv run python rhlc-backup.py --auto --fast --save-cookies
```

Creates `cookies.txt` for reuse without browser login.

### Use Saved Cookies
```bash
uv run python rhlc-backup.py --cookies cookies.txt --fast
```

### Slow Mode (Full Browser Rendering)
```bash
uv run python rhlc-backup.py --auto
```

Only use if `--fast` mode has issues. Takes 50+ hours.

---

## File Structure

```
backup_YYYYMMDD_HHMMSS/
├── index.html              # Main page (start here!)
├── threads/                # Individual thread pages
│   └── *.html
├── attachments/            # Downloaded PDFs, docs, etc.
│   └── *.pdf
├── images/                 # Downloaded images
│   └── *.png, *.jpg
└── json/                   # Raw data
    ├── messages.jsonl      # All messages
    ├── boards.json         # Board structure
    └── media_mapping.json  # File mappings
```

---

## Backup Size Estimates

- **Messages only**: ~70MB JSON
- **With images**: ~500MB - 2GB
- **With attachments**: ~2GB - 10GB
- **Total backup time**: 7-8 hours (fast mode)

---

## Need More Help?

📚 **Detailed Guides:**
- [COMPLETE_BACKUP_GUIDE.md](COMPLETE_BACKUP_GUIDE.md) - Comprehensive guide with all options
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Solutions for common problems
- [ATTACHMENT_REPROCESSING_GUIDE.md](ATTACHMENT_REPROCESSING_GUIDE.md) - Fix corrupted attachments

💬 **Quick Commands:**
```bash
# Check backup status
ls -lh backup_*/

# Count messages
wc -l backup_*/json/messages.jsonl

# Check for corrupted attachments
uv run python count_corrupted.py

# Regenerate HTML after fixes
uv run python regenerate_html.py backup_YYYYMMDD_HHMMSS
```

---

## Tips for Success

1. **Use `--fast` mode** - 7x faster than slow mode
2. **Run overnight** - Backup takes 7-8 hours
3. **Check for corruption** - Run `count_corrupted.py` after backup
4. **Keep cookies** - Use `--save-cookies` for future backups
5. **Incremental updates** - Use `--incremental` to update existing backups

---

**Ready to start?** Run this command:

```bash
uv run python rhlc-backup.py --auto --fast
```

Then sit back and let it run! ☕