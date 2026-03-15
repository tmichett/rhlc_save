# Troubleshooting Guide

This guide helps you fix common issues with RHLC backups, regenerate HTML, and reprocess attachments.

---

## Table of Contents

1. [Corrupted Attachments](#corrupted-attachments)
2. [Regenerating HTML](#regenerating-html)
3. [Reprocessing Attachments](#reprocessing-attachments)
4. [Navigation Issues](#navigation-issues)
5. [Common Error Messages](#common-error-messages)

---

## Corrupted Attachments

### Symptoms
- Attachments show as 6-7KB files
- Opening attachments shows HTML/XML instead of actual content
- Files contain SAML authentication redirect pages
- HTML shows "(not downloaded)" for existing files

### Cause
Session cookies expired during long backup process (12+ hours). The server returned authentication redirect pages instead of actual files.

### Solution

#### Step 1: Verify Corruption
Check how many files are corrupted:
```bash
uv run python count_corrupted.py
```

This will show:
- Total files in attachments directory
- Number of corrupted files (6KB SAML redirects)
- Number of valid files

#### Step 2: Re-download Corrupted Files
```bash
uv run python reprocess_attachments.py --backup-dir backup_20260314_094400 --auto
```

What this does:
1. Opens browser for fresh authentication
2. Automatically detects corrupted files (< 10KB with SAML markers)
3. Re-downloads only corrupted files
4. Preserves valid files
5. Adds missing file extensions

#### Step 3: Regenerate HTML
```bash
uv run python regenerate_html.py backup_20260314_094400
```

This updates all HTML pages to show correct attachment links.

#### Step 4: Verify Fix
```bash
# Check file sizes - should be larger than 10KB
ls -lh backup_20260314_094400/attachments/*.pdf | head -5

# Run corruption check again
uv run python count_corrupted.py
```

### Prevention
Use `--fast` mode for future backups to prevent session timeout:
```bash
uv run python rhlc-backup.py --auto --fast
```

This completes in 7-8 hours instead of 50+ hours.

---

## Regenerating HTML

### When to Regenerate
- After reprocessing attachments
- After fixing corrupted files
- To update attachment links
- To apply new HTML features
- After modifying JSON data

### How to Regenerate

#### Basic Regeneration
```bash
uv run python regenerate_html.py backup_20260314_094400
```

#### What Gets Regenerated
- All 8,000+ thread HTML pages
- Main index.html with board listings
- Attachment links (checks disk for files)
- Navigation state persistence
- Board expand/collapse functionality

#### Output
```
Loading messages from backup_20260314_094400/json/messages.jsonl...
Loaded 50905 messages
Loaded 34 boards
Found 106 attachment files on disk

Generating HTML pages for threads...
  Generated 8178/8178 thread pages

Generating main index...

✅ HTML regeneration complete!
```

### After Regeneration
1. **Hard refresh your browser**: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows/Linux)
2. **Clear localStorage** (if navigation issues persist):
   - Open browser console (F12)
   - Run: `localStorage.clear()`
   - Refresh page

---

## Reprocessing Attachments

### When to Reprocess
- Attachments show "(not downloaded)"
- Files are corrupted (6KB SAML redirects)
- Missing file extensions
- Authentication errors during original backup
- Need to re-download specific files

### Reprocessing Options

#### Option 1: Auto-login (Recommended)
```bash
uv run python reprocess_attachments.py --backup-dir backup_20260314_094400 --auto
```

**Steps:**
1. Browser opens to learn.redhat.com
2. Click "Sign In" and log in
3. Press Enter in terminal after login
4. Script detects and re-downloads corrupted files

#### Option 2: Use Saved Cookies
```bash
uv run python reprocess_attachments.py --backup-dir backup_20260314_094400 --cookies cookies.txt
```

#### Option 3: Force Re-download All
```bash
uv run python reprocess_attachments.py --backup-dir backup_20260314_094400 --auto --force
```

**Warning**: This re-downloads ALL attachments, even valid ones. Only use if necessary.

### Understanding Output

#### Success
```
[1/114] Processing RELEASE_NOTES_V2.2.5.pdf
  Detected corrupted SAML redirect: RELEASE_NOTES_V2.2.5.pdf (6371 bytes)
  Re-downloading corrupted file: RELEASE_NOTES_V2.2.5.pdf
  ✓ Downloaded RELEASE_NOTES_V2.2.5.pdf (403456 bytes)
```

#### Skipped (Valid File)
```
[2/114] Processing Container_Quickstart.pdf
  Skipping Container_Quickstart.pdf (already exists, 2074518 bytes)
```

#### Failed
```
[3/114] Processing Missing_File.pdf
  Attempt 1/3: Status 404 for Missing_File.pdf
  ✗ Failed to download Missing_File.pdf after 3 attempts
```

### After Reprocessing
Always regenerate HTML:
```bash
uv run python regenerate_html.py backup_20260314_094400
```

---

## Navigation Issues

### Board Doesn't Stay Expanded

#### Symptom
When you click a thread and return, the board collapses.

#### Cause
This is actually the correct behavior! The localStorage feature remembers which boards YOU manually expanded. If you never expanded "Lab Engineers" before clicking a thread, it won't be expanded when you return.

#### Solution (Automatic)
The latest version auto-expands the board you just viewed:
1. Click any thread in "Lab Engineers"
2. View the thread
3. Click back button
4. "Lab Engineers" automatically expands!

#### Manual Fix
If auto-expand isn't working:
1. Regenerate HTML with latest code:
   ```bash
   uv run python regenerate_html.py backup_20260314_094400
   ```
2. Hard refresh browser (Cmd+Shift+R or Ctrl+Shift+R)

### Clear Navigation State

If boards are stuck expanded/collapsed:
```javascript
// Open browser console (F12) and run:
localStorage.removeItem('expandedBoards');
localStorage.removeItem('lastViewedBoard');
// Then refresh page
```

---

## Common Error Messages

### "Directory not found"
```
Error: Directory backup_20260314_094400 does not exist
```

**Solution:**
```bash
# List available backups
ls -d backup_*/

# Use correct directory name
uv run python regenerate_html.py backup_20260314_094400
```

### "Messages file not found"
```
Error: Messages file not found: backup_20260314_094400/json/messages.json
```

**Cause**: Backup didn't complete or JSON wasn't generated.

**Solution:**
1. Check if `messages.jsonl` exists:
   ```bash
   ls -lh backup_20260314_094400/json/
   ```
2. If only `messages.jsonl` exists, that's fine - `regenerate_html.py` uses it
3. If no JSON files exist, re-run the backup

### "Authentication failed"
```
✗ Authentication failed for filename.pdf (status 403)
```

**Cause**: Session cookies expired or invalid.

**Solution:**
```bash
# Use --auto to get fresh authentication
uv run python reprocess_attachments.py --backup-dir backup_20260314_094400 --auto
```

### "No attachments to download"
```
Found 0 unique attachments to process
```

**Cause**: No attachments in messages.json or all URLs are external.

**Solution:**
1. Verify messages.json has attachment data:
   ```bash
   grep -c '"attachments"' backup_20260314_094400/json/messages.json
   ```
2. Check if attachments are external URLs (not from learn.redhat.com)

### Browser Won't Open (--auto mode)
```
Error: Playwright not installed
```

**Solution:**
```bash
uv pip install playwright
uv run playwright install chromium
```

---

## Quick Reference Commands

### Check Corruption
```bash
uv run python count_corrupted.py
```

### Fix Corrupted Attachments
```bash
uv run python reprocess_attachments.py --backup-dir backup_20260314_094400 --auto
```

### Regenerate HTML
```bash
uv run python regenerate_html.py backup_20260314_094400
```

### Test Corruption Detection
```bash
uv run python test_corruption_detection.py
```

### List Backups
```bash
ls -d backup_*/
```

### Check Backup Size
```bash
du -sh backup_20260314_094400
```

### Count Files
```bash
# Total messages
wc -l backup_20260314_094400/json/messages.jsonl

# Total attachments
ls backup_20260314_094400/attachments/ | wc -l

# Total threads
ls backup_20260314_094400/threads/ | wc -l
```

---

## Getting Help

If you encounter issues not covered here:

1. **Check the logs** - Look for error messages in terminal output
2. **Verify file structure** - Ensure JSON files and directories exist
3. **Test with small backup** - Try commands on a smaller backup first
4. **Check disk space** - Ensure enough space for re-downloads
5. **Review documentation**:
   - [COMPLETE_BACKUP_GUIDE.md](COMPLETE_BACKUP_GUIDE.md)
   - [ATTACHMENT_REPROCESSING_GUIDE.md](ATTACHMENT_REPROCESSING_GUIDE.md)
   - [README.md](README.md)

---

## Advanced Troubleshooting

### Manually Check File Corruption
```bash
# Check if file contains SAML redirect
head -20 backup_20260314_094400/attachments/RELEASE_NOTES_V2.2.5.pdf

# If you see XML/HTML with "SAMLRequest", it's corrupted
```

### Manually Fix Single File
```bash
# Download with curl (requires authentication)
curl -o backup_20260314_094400/attachments/file.pdf \
  -H "Cookie: your-cookies-here" \
  https://learn.redhat.com/path/to/file.pdf
```

### Rebuild Attachment Mapping
The mapping file (`media_mapping.json`) is optional. If missing, the HTML generator will check disk for files directly.

### Reset Everything
```bash
# Delete HTML files
rm -rf backup_20260314_094400/threads/*.html
rm backup_20260314_094400/index.html

# Regenerate from scratch
uv run python regenerate_html.py backup_20260314_094400
```

---

**Last Updated**: 2026-03-15