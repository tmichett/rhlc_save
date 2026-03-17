# Group Backup Attachment & HTML Generation Fixes

## Critical Issue: Missing Replies (FIXED)

### Problem
The initial group backup only captured thread starter posts (1,018 messages across 411 threads), but missed all reply messages. This is because group listing pages only contain links to thread starters (`/td-p/` URLs), not individual replies (`/m-p/` URLs).

### Root Cause
The [`backup_groups.py`](backup_groups.py) script was only crawling group listing pages, which don't include reply URLs. To get replies, we need to visit each thread page individually.

### Solution: Two-Phase Crawling
**FIXED in [`backup_groups.py`](backup_groups.py:440)** - The main script now implements automatic two-phase crawling:

**Phase 1**: Crawl group listing pages for thread URLs
**Phase 2**: Visit each thread page and extract all reply URLs (`/m-p/`)
**Phase 3**: Download all messages (threads + replies)

Future backups will automatically capture all replies. For existing backups, use [`crawl_missing_replies.py`](crawl_missing_replies.py) to add missing replies.

### Usage

```bash
# Step 1: Crawl missing replies (requires authentication)
uv run python crawl_missing_replies.py groups_backup_20260315_215501

# Step 2: Reprocess attachments if needed
uv run python reprocess_groups.py --backup-dir groups_backup_20260315_215501 --auto

# Step 3: Regenerate HTML with complete data
uv run python regenerate_groups_html.py groups_backup_20260315_215501
```

### Expected Results
- **Before**: 1,018 messages (thread starters only)
- **After**: ~3,000-5,000 messages (threads + replies)
- All thread pages will show complete conversations

### Technical Details
The script:
- Uses Playwright for authentication
- Crawls each thread page with rate limiting (1s delay)
- Extracts all `/m-p/` URLs from thread pages
- Downloads message content, metadata, and media URLs
- Merges with existing data preserving group associations
- Updates `all_messages.json` with complete dataset

## Issues Fixed

### 1. Broken Thread Links (404 errors)
**Problem**: Index page was linking to `threads/filename.html` but files were in the same directory as the index, causing all thread links to fail with 404 errors.

**Root Cause**: The [`html_generator.py`](html_generator.py:378) hardcoded `threads/` prefix in links, which works for full backup (structure: `html/threads/*.html`) but not for group backup (structure: `html/*.html`).

**Solution**: Added optional `thread_path_prefix` parameter to [`generate_index_html()`](html_generator.py:263):
- Full backup: Uses default `"threads/"` prefix
- Group backup: Passes `""` (empty string) for same-directory links

**Code Changes**:
```python
# html_generator.py
def generate_index_html(..., thread_path_prefix: str = "threads/"):
    # Link generation now uses the prefix parameter
    <a href="{thread_path_prefix}{thread['filename']}">
```

Updated all group backup scripts to pass empty prefix:
- [`backup_groups.py`](backup_groups.py:695)
- [`reprocess_groups.py`](reprocess_groups.py:418)
- [`regenerate_groups_html.py`](regenerate_groups_html.py:109)

### 2. Missing Thread Titles (All Showing "Untitled")
**Problem**: All thread titles in the group backup were empty, showing as "Untitled" in the HTML index. The title extraction from the page HTML was failing because group hub pages don't have the expected `<h1 class="lia-message-subject">` element.

**Root Cause**: The [`download_message()`](backup_groups.py:514) function was looking for titles in an HTML element that doesn't exist on group hub pages.

**Solution**: Added fallback title extraction from URL structure:
- Group URLs follow pattern: `/t5/GROUP-NAME/TITLE/td-p/ID`
- Extract the TITLE slug from URL (part before `/td-p/` or `/m-p/`)
- Convert slug to readable title (e.g., "Python-programming" → "Python Programming")

**Code Changes in [`backup_groups.py`](backup_groups.py:519)**:
```python
# Fallback: Extract title from URL if not found in page
if not message_data["title"]:
    try:
        url_parts = url.split("/")
        for i, part in enumerate(url_parts):
            if part in ("td-p", "m-p") and i > 0:
                title_slug = url_parts[i - 1]
                message_data["title"] = title_slug.replace("-", " ").title()
                break
    except Exception as e:
        logger.debug(f"Could not extract title from URL: {e}")
```

**Fixing Existing Backups**: Created [`fix_group_titles.py`](fix_group_titles.py) utility script:
```bash
# Fix titles in existing backup
uv run python fix_group_titles.py groups_backup_20260315_201647

# Then regenerate HTML (no --backup-dir flag needed)
uv run python regenerate_groups_html.py groups_backup_20260315_201647
```

### 2. Rate Limiting (HTTP 429 Errors)
**Problem**: The Red Hat Learning Community site was rate limiting requests during group backup, causing many pages to fail with 429 status codes.

**Solution**: 
- Added `RATE_LIMIT_DELAY = 5` constant for handling 429 errors
- Modified [`fetch_page_with_retries()`](backup_groups.py:235) to detect 429 status and wait progressively longer (5s, 10s, 15s) before retrying
- This allows the backup to continue even when rate limited

**Code Changes**:
```python
elif response.status_code == 429:
    # Rate limited - wait longer
    wait_time = RATE_LIMIT_DELAY * (attempt + 1)
    logger.warning(f"Rate limited (429), waiting {wait_time}s before retry...")
    time.sleep(wait_time)
```

### 2. HTML Generation KeyError: 'subject'
**Problem**: The HTML generator ([`html_generator.py`](html_generator.py:352)) expects thread dictionaries to have a `"subject"` key, but group backup scripts were using `"title"` instead. This caused a KeyError when generating the index page.

**Root Cause**: Group hub posts use different field names than regular community posts:
- Regular posts: `subject`, `author`, `replies`
- Group posts: `title`, `author`, `message_count`

**Solution**: Modified all three group backup scripts to include both `"subject"` and `"title"` keys for compatibility:

1. **[`backup_groups.py`](backup_groups.py:640)** - Main backup script
2. **[`reprocess_groups.py`](reprocess_groups.py:399)** - Reprocessing script  
3. **[`regenerate_groups_html.py`](regenerate_groups_html.py:89)** - HTML regeneration script

**Code Pattern Applied**:
```python
# Track thread info for index - use "subject" key for compatibility with html_generator
first_msg = thread_messages[0] if thread_messages else {}
thread_files.append({
    "filename": filename,
    "subject": first_msg.get("title", "Untitled"),  # html_generator expects "subject"
    "title": first_msg.get("title", "Untitled"),    # keep "title" for compatibility
    "board_name": first_msg.get("group_title", "Unknown Group"),
    "author": first_msg.get("author", "Unknown"),
    "replies": len(thread_messages) - 1,
    "message_count": len(thread_messages),
    "url": thread_url
})
```

### 3. Non-Group Content in Backups (FIXED)
**Problem**: The initial group backup accidentally included content from regular community boards (like `/t5/Platform-Linux/`) instead of only group hub content.

**Root Cause**: The [`extract_message_links()`](backup_groups.py:448) function was extracting all message URLs without validating they belonged to group hubs.

**Solution**: Added URL filtering in [`backup_groups.py`](backup_groups.py:424):
- New `is_group_hub_url()` function validates URLs belong to group hubs
- Checks if URL contains the group ID being backed up
- Detects course code patterns (RH###, AD###, DO###, EX###, CL###)
- Filters out regular board URLs like "Platform-Linux", "General-Discussion"

**Code Changes**:
```python
def is_group_hub_url(url: str, group_id: str) -> bool:
    """Check if a URL belongs to a group hub (not a regular board)."""
    # Extract board/group from URL
    match = re.search(r'/t5/([^/]+)/', url)
    if not match:
        return False
    
    url_group = match.group(1)
    
    # Check if URL contains the group ID
    if group_id.lower() in url_group.lower():
        return True
    
    # Check for course code patterns
    if re.search(r'(RH|AD|DO|EX|CL)\d{3}', url_group, re.IGNORECASE):
        return True
    
    return False
```

**Result**: Future backups will only include group hub content, not regular board posts.

### 4. Missing File Extensions on Attachments
**Problem**: Some attachments were downloading without file extensions, making them unopenable.

**Status**: This issue was previously addressed in the main backup system by:
- Checking `Content-Type` headers and mapping MIME types to extensions
- Extracting extensions from `Content-Disposition` headers
- Falling back to URL-based extension detection

**Verification Needed**: The user should verify if this issue still occurs with group backups. If so, the same MIME type mapping logic from [`rhlc-backup.py`](rhlc-backup.py) should be applied to [`backup_groups.py`](backup_groups.py).

## Testing Recommendations

1. **Rate Limiting**: Run a full group backup and monitor for 429 errors. The script should now automatically retry with increasing delays.

2. **HTML Generation**: After backup completes, verify that `groups_index.html` generates successfully without KeyError.

3. **File Extensions**: Check the `attachments/` directory and verify all files have proper extensions. If not, we may need to add MIME type mapping to group backup.

4. **Fix HTML Only (No Login Required)**: If you just need to fix the KeyError: 'subject' issue:
   ```bash
   uv run python regenerate_groups_html.py --backup-dir groups_backup_YYYYMMDD_HHMMSS
   ```
   This works offline and doesn't require authentication.

5. **Reprocess Media (Requires Login)**: If attachments/images are missing or corrupted:
   ```bash
   uv run python reprocess_groups.py --backup-dir groups_backup_YYYYMMDD_HHMMSS --auto
   ```
   This requires authentication because it downloads media from the site.

## Related Files

- [`backup_groups.py`](backup_groups.py) - Main group backup script
- [`reprocess_groups.py`](reprocess_groups.py) - Reprocess corrupted/missing media
- [`regenerate_groups_html.py`](regenerate_groups_html.py) - Regenerate HTML only
- [`html_generator.py`](html_generator.py) - Shared HTML generation logic
- [`QUICKSTART_GROUPS.md`](QUICKSTART_GROUPS.md) - Quick start guide
- [`GROUP_BACKUP_GUIDE.md`](GROUP_BACKUP_GUIDE.md) - Complete documentation

## Next Steps

If issues persist:

1. **For 429 errors**: Increase `RATE_LIMIT_DELAY` or add `--fast` flag to reduce delays between successful requests
2. **For missing extensions**: Add MIME type mapping from main backup to group backup
3. **For authentication timeouts**: Use reprocessing script to re-download failed media with fresh session