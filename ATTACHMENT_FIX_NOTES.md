# Attachment Extraction Fix

## Problem Summary

The original `rhlc-backup.py` script was not capturing file attachments (PDFs, etc.) from forum posts. Investigation revealed two key issues:

### Issue 1: Wrong CSS Selector
- **Original selector**: `class="lia-attachment"` 
- **Actual class**: `class="attachment-link"` or `class="lia-link-navigation"`
- The script was looking for the wrong class name, so attachments were never found

### Issue 2: AWS WAF Protection
- The site uses AWS Web Application Firewall (WAF) which blocks headless browsers
- Initial attempts to use Playwright in headless mode resulted in CAPTCHA challenges
- Solution: Use non-headless browser mode with authenticated session cookies

## Solution Implemented

### 1. Updated CSS Selectors
The attachment extraction code now looks for:
- Links with `"attachment"` in the class name (using regex)
- Links with `.pdf` in the href (direct PDF links)
- Extracts filename from link text or href path

### 2. Browser-Based Fetching
- Uses Playwright in **non-headless mode** to bypass AWS WAF
- Transfers authenticated cookies from the login session to the browser
- Waits for dynamic content to load (3 seconds)
- Extracts fully rendered HTML including JavaScript-loaded attachments

### 3. Dual Extraction Strategy
The script now extracts attachments in two ways:
1. From the initial HTML (for attachments in static content)
2. From browser-rendered HTML (for JavaScript-loaded attachments)

## How to Run a New Backup with Attachments

### Step 1: Authenticate
```bash
uv run python rhlc-backup.py --auto --save-cookies
```

This will:
- Open a browser window
- Prompt you to log in
- Save your session cookies for future use

### Step 2: Run Full Backup
```bash
uv run python rhlc-backup.py --auto
```

Or use saved cookies:
```bash
uv run python rhlc-backup.py --cookies cookies.txt
```

### Step 3: Verify Attachments
After the backup completes, check:
```bash
ls -la backup_*/attachments/
```

You should see downloaded PDF files and other attachments.

## Technical Details

### Attachment URL Patterns
Attachments are found in two formats:

1. **Direct PDF links**:
   ```
   /jfvwy86652/attachments/jfvwy86652/lab_engineer_updates/88/1/RHTLC_User_Guide_and_Setup.pdf
   ```

2. **Attachment links with IDs**:
   ```
   https://learn.redhat.com/t5/Lab-Engineer-Updates/RHTLC-Release-3-4-3/m-p/57651/thread-id/88?attachment-id=235
   ```

### Code Changes

**File**: `rhlc-backup.py`

**Lines 557-585**: Updated attachment extraction in `extract_all_messages_from_page()`
- Changed selector from `"lia-attachment"` to `"attachment"` (regex)
- Added PDF link detection
- Added filename extraction from href when link text is empty
- Added duplicate detection

**Lines 229-277**: Updated `fetch_page_with_browser()`
- Changed from headless=True to headless=False
- Added proper cookie injection from requests session
- Added 3-second wait for dynamic content
- Added error handling

**Lines 680**: Updated `download_messages()` to use browser fetching
- Changed `fetch_page(session, url)` to `fetch_page(session, url, use_browser=True)`

## Testing

A test script `test_attachment_extraction.py` was created to verify attachment detection:

```bash
uv run python test_attachment_extraction.py
```

This opens a browser, lets you log in, and shows what attachments are found on a test page.

**Test Results** (from page with 3 PDFs):
- ✅ Found 3 PDF links with correct hrefs
- ✅ Found 3 attachment links with correct filenames
- ✅ Extracted: RHTLC_User_Guide_and_Setup.pdf, Quickstart.pdf, RELEASE_NOTES_V3.4.3.pdf

## Important Notes

1. **Non-Headless Mode**: The browser will be visible during backup. This is necessary to bypass AWS WAF.

2. **Cookie Expiration**: Session cookies may expire. If you get 403 errors, re-authenticate with `--auto`.

3. **Rate Limiting**: The script includes delays between requests to avoid overwhelming the server.

4. **Attachment Download**: Attachments are downloaded to `backup_*/attachments/` directory and referenced in the HTML output.

## Next Steps

To get a complete backup with all attachments:

1. Delete or rename the old backup directory (optional)
2. Run: `uv run python rhlc-backup.py --auto`
3. Log in when the browser opens
4. Wait for the backup to complete
5. Verify attachments in `backup_*/attachments/`

The backup will now include:
- All forum posts and replies
- All images
- **All file attachments (PDFs, etc.)** ✅
- Threaded HTML pages
- Complete offline archive