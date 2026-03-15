# Attachment Reprocessing Guide

> ⚠️ **IMPORTANT**: If your backup took 12+ hours, you likely have corrupted attachments! See [Corrupted Attachments](#problem-corrupted-attachments-6kb-files) below.

## Problem Summary

After running the initial backup, you may encounter three issues with attachments:

1. **Corrupted Downloads (NEW)**: Attachments are 6KB SAML redirect pages instead of actual files due to session timeout
2. **Authentication Timeout**: Some attachments fail to download with 401/403 errors because the session cookies expire during the long download process
3. **Missing File Extensions**: Some attachments download successfully but lack file extensions, making them unopenable

## Root Causes

### Issue 1: Authentication Timeout
- The browser session closes after extracting attachment URLs from pages
- Later, when downloading attachments, the session cookies may have expired
- The server returns 401/403 errors for unauthenticated requests

### Issue 2: Missing Extensions
- The original code didn't check the `Content-Type` header to determine file type
- Files were saved with whatever filename was in the HTML, which sometimes lacked extensions
- Without extensions, operating systems can't determine how to open the files

## Solutions Implemented

### Fix 1: Enhanced Authentication Handling
Updated [`rhlc-backup.py`](rhlc-backup.py:793-860) to:
- Add better error logging for authentication failures (401/403 status codes)
- Include `allow_redirects=True` to handle authentication redirects
- Log specific status codes to help diagnose issues

### Fix 2: Content-Type Based Extension Detection
Updated [`rhlc-backup.py`](rhlc-backup.py:793-860) to:
- Check the `Content-Type` header from the HTTP response
- Map common MIME types to file extensions (PDF, DOCX, XLSX, ZIP, etc.)
- Automatically append the correct extension if the filename lacks one
- Log when extensions are added for transparency

### Fix 3: Reprocessing Script
Created [`reprocess_attachments.py`](reprocess_attachments.py) to:
- Read existing `messages.json` from a completed backup
- Re-download failed or incomplete attachments
- Add missing file extensions to existing files
- Skip files that already exist and have content (unless `--force` is used)
- Provide detailed progress and error reporting

## How to Reprocess Attachments

### Step 1: Identify Your Backup Directory

Find the backup directory that needs reprocessing:
```bash
ls -la backup_*/
```

Example: `backup_20240314_123456`

### Step 2: Authenticate and Reprocess

**Option A: Use browser login (recommended)**
```bash
uv run python reprocess_attachments.py --backup-dir backup_20240314_123456 --auto
```

This will:
1. Open a browser window
2. Prompt you to log in to learn.redhat.com
3. Wait for you to press Enter after logging in
4. Download all missing/failed attachments with proper extensions

**Option B: Use saved cookies**
```bash
uv run python reprocess_attachments.py --backup-dir backup_20240314_123456 --cookies cookies.txt
```

**Option C: Force re-download everything**
```bash
uv run python reprocess_attachments.py --backup-dir backup_20240314_123456 --auto --force
```

The `--force` flag will re-download all attachments, even if they already exist.

### Step 3: Verify Results

Check the attachments directory:
```bash
ls -la backup_20240314_123456/attachments/
```

You should see:
- All files with proper extensions (.pdf, .docx, .xlsx, etc.)
- File sizes greater than 0 bytes
- No authentication errors in the output

### Step 4: Regenerate HTML (Optional)

If you want to update the HTML pages with the corrected attachment filenames:
```bash
uv run python regenerate_html.py --backup-dir backup_20240314_123456
```

## Understanding the Output

### Success Messages
```
[1/10] Processing RHTLC_User_Guide.pdf
  ✓ Downloaded RHTLC_User_Guide.pdf (1234567 bytes)
```

### Extension Added
```
[2/10] Processing Release_Notes
  Added extension .pdf (Content-Type: application/pdf)
  ✓ Downloaded Release_Notes.pdf (987654 bytes)
```

### Skipped (Already Exists)
```
[3/10] Processing Quickstart.pdf
  Skipping (already exists)
```

### Authentication Failure
```
[4/10] Processing Secure_Document
  ✗ Authentication failed for Secure_Document (status 403)
```

### Download Failure
```
[5/10] Processing Missing_File.pdf
  Attempt 1/3: Status 404 for Missing_File.pdf
  Attempt 2/3: Status 404 for Missing_File.pdf
  Attempt 3/3: Status 404 for Missing_File.pdf
  ✗ Failed to download Missing_File.pdf after 3 attempts
```

## Summary Report

At the end, you'll see a summary:
```
============================================================
REPROCESSING COMPLETE
============================================================
Total attachments: 50
Successfully downloaded: 45
Skipped (already exist): 3
Failed: 2
Attachments directory: backup_20240314_123456/attachments
```

## Troubleshooting

### Problem: Corrupted Attachments (6KB Files)

**Symptoms**:
- Attachments are exactly 6.2KB in size
- Files contain HTML/XML instead of actual content
- Opening files shows SAML authentication redirect pages
- Files have correct names but wrong content

**Cause**: Session cookies expired during long backup process (12+ hours). When downloading attachments, the server returned SAML authentication redirect pages instead of actual files.

**Solution**:
```bash
uv run python reprocess_attachments.py --backup-dir backup_20260314_094400 --auto
```

The script now automatically:
1. Detects files < 10KB (suspicious size)
2. Checks for SAML authentication markers (`SAMLRequest`, `saml2p:AuthnRequest`)
3. Re-downloads any corrupted files with fresh authentication
4. Logs: `Detected corrupted SAML redirect: filename.pdf (6345 bytes)`

**Prevention**: Use `--fast` mode for faster backups (7-8 hours instead of 50+ hours):
```bash
uv run python rhlc-backup.py --auto --fast
```

### Problem: Many 401/403 Errors

**Cause**: Session cookies expired or invalid

**Solution**:
1. Use `--auto` to log in with a fresh browser session
2. Or export fresh cookies from your browser and use `--cookies`

### Problem: Files Still Missing Extensions

**Cause**: Server not sending proper `Content-Type` headers

**Solution**: 
1. Check the original URL in the HTML to see if it has an extension
2. Manually rename files based on their content
3. Use the `file` command to identify file types:
   ```bash
   file backup_*/attachments/*
   ```

### Problem: "Backup directory not found"

**Cause**: Wrong path to backup directory

**Solution**: 
```bash
# List available backups
ls -d backup_*/

# Use the full path
uv run python reprocess_attachments.py --backup-dir ./backup_20240314_123456 --auto
```

### Problem: "Messages file not found"

**Cause**: Backup didn't complete or JSON wasn't generated

**Solution**: 
1. Check if `backup_dir/json/messages.json` exists
2. If not, you may need to re-run the full backup with `rhlc-backup.py`

## Future Backups

For new backups, the fixes are already integrated into [`rhlc-backup.py`](rhlc-backup.py):
- Attachments will download with proper extensions automatically
- Better error handling for authentication issues
- More detailed logging to diagnose problems

Simply run:
```bash
uv run python rhlc-backup.py --auto
```

## Technical Details

### Supported File Types

The reprocessing script recognizes these MIME types:

| Content-Type | Extension |
|--------------|-----------|
| application/pdf | .pdf |
| application/zip | .zip |
| application/vnd.openxmlformats-officedocument.spreadsheetml.sheet | .xlsx |
| application/vnd.openxmlformats-officedocument.wordprocessingml.document | .docx |
| application/vnd.openxmlformats-officedocument.presentationml.presentation | .pptx |
| application/vnd.ms-excel | .xls |
| application/msword | .doc |
| application/vnd.ms-powerpoint | .ppt |
| text/plain | .txt |
| text/csv | .csv |
| application/json | .json |
| application/xml | .xml |
| image/jpeg | .jpg |
| image/png | .png |
| image/gif | .gif |
| image/svg+xml | .svg |

### Retry Logic

The script includes exponential backoff retry logic:
- Attempt 1: Immediate
- Attempt 2: Wait 2 seconds
- Attempt 3: Wait 4 seconds

This helps handle temporary network issues or rate limiting.

### Cookie Management

When using `--auto --save-cookies`, the script saves cookies to `cookies.txt` for future use:
```bash
# First time: log in and save cookies
uv run python reprocess_attachments.py --backup-dir backup_20240314_123456 --auto --save-cookies

# Later: reuse saved cookies
uv run python reprocess_attachments.py --backup-dir backup_20240314_123456 --cookies cookies.txt
```

## Related Files

- [`rhlc-backup.py`](rhlc-backup.py) - Main backup script with attachment fixes
- [`reprocess_attachments.py`](reprocess_attachments.py) - Reprocessing script
- [`ATTACHMENT_FIX_NOTES.md`](ATTACHMENT_FIX_NOTES.md) - Original fix documentation
- [`regenerate_html.py`](regenerate_html.py) - HTML regeneration script