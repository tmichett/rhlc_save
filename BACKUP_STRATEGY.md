# Complete Site Backup Strategy

## Current Limitations

The web scraping approach (`rhlc-backup.py`) has limitations:

1. **Discovery Problem**: Can only find content that's linked on pages it visits
2. **Incomplete Coverage**: Misses older posts, archived threads, and content in less-visited boards
3. **No API Access**: The Khoros REST API v2 endpoints return 404 on learn.redhat.com

## Recommended Approach for Complete Backup

### Option 1: Use Your Personal Export + Moderator Tools

Since you're a high-level moderator, you likely have access to:

1. **Admin Export Tools** in the Khoros admin panel
   - Look for: Admin → System → Export/Backup
   - May provide complete database exports
   - Contact Red Hat community admins about bulk export options

2. **Combine Multiple Exports**
   ```bash
   # Your personal posts (detailed HTML)
   uv run export_community.py --auto
   
   # Other users' content (if you can access their JSON exports)
   # Request from other active users or moderators
   ```

### Option 2: Enhanced Crawling Strategy

Modify `rhlc-backup.py` to:

1. **Start from sitemap** (if available)
   - `https://learn.redhat.com/sitemap.xml`
   - Lists all public URLs

2. **Crawl all board pages exhaustively**
   - Visit every page of every board
   - Follow all pagination links
   - Use `--max-pages` to control depth

3. **Use search to find content**
   - Search for date ranges
   - Search by user
   - Search by keywords

### Option 3: Database-Level Access

As a moderator, request:

1. **Database export** from Red Hat IT
2. **API credentials** with full access
3. **Bulk export tool** access

## Immediate Actions

### 1. Check What You Actually Got

```bash
cd backup_20260312_130300

# Count unique threads
jq -r '.url' json/messages.json | sort -u | wc -l

# Count messages per board
jq -r '._board_title' json/messages.json | sort | uniq -c

# List all boards discovered
jq -r '.title' json/boards.json
```

### 2. Run More Comprehensive Crawl

```bash
# Remove page limit to get ALL pages from each board
uv run rhlc-backup.py --cookies cookies.txt --output backup_full

# This will take much longer but get more content
```

### 3. Check for Sitemap

```bash
curl -s https://learn.redhat.com/sitemap.xml | head -50
curl -s https://learn.redhat.com/robots.txt
```

## Why You're Missing Content

**609 messages from 439 threads** suggests:

1. **Pagination limit**: Script may have stopped after first page of each board
2. **Board discovery**: May have only found main/featured boards
3. **URL patterns**: Some content uses different URL patterns not detected

## Next Steps

1. **Verify board discovery**
   - Check `json/boards.json` - does it list ALL boards you know exist?
   - If not, the discovery function needs improvement

2. **Check pagination**
   - Look at script logs - did it say "No more messages found" too early?
   - May need to adjust pagination detection

3. **Manual board list**
   - Create a list of all board URLs you want to backup
   - Modify script to use that list instead of discovery

Would you like me to:
- A) Improve the board discovery to find more boards?
- B) Add manual board URL input option?
- C) Enhance pagination to get all pages?
- D) All of the above?