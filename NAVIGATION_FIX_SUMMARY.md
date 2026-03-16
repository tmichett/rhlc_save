# Navigation Fix Summary

## Problem
Group backup HTML files had broken "Back to Index" links pointing to `../index.html` which didn't exist. The index was actually at `html/groups_index.html`.

## Solution
Made the index link configurable in `generate_thread_html()` function to support both backup structures:

### Main Backup Structure (rhlc-backup.py)
```
backup_YYYYMMDD_HHMMSS/
├── index.html              ← Root level index
├── threads/                ← Thread HTML files here
│   ├── thread1.html       ← Links to ../index.html ✓
│   └── thread2.html
```

### Group Backup Structure (backup_groups.py)
```
groups_backup_YYYYMMDD_HHMMSS/
├── index.html              ← New landing page
├── html/                   ← All HTML files here
│   ├── groups_index.html  ← Main content index
│   ├── thread1.html       ← Links to groups_index.html ✓
│   └── thread2.html
```

## Changes Made

### 1. html_generator.py
- Added `index_link` parameter to `generate_thread_html()` with default `"../index.html"`
- Main backup uses default (backward compatible)
- Group backup passes `"groups_index.html"`

### 2. backup_groups.py
- Passes `index_link="groups_index.html"` to `generate_thread_html()`
- Creates top-level `index.html` landing page with statistics

### 3. regenerate_groups_html.py
- Passes `index_link="groups_index.html"` to `generate_thread_html()`
- Creates top-level `index.html` when regenerating

### 4. reprocess_groups.py
- Passes `index_link="groups_index.html"` to `generate_thread_html()`

### 5. create_top_index.py (New)
- Utility script to add top-level index to existing group backups
- Usage: `python create_top_index.py groups_backup_YYYYMMDD_HHMMSS`

## Backward Compatibility

✅ **Main backup (rhlc-backup.py)** - No changes needed, uses default parameter
✅ **Main backup regeneration (regenerate_html.py)** - No changes needed, uses default parameter
✅ **Existing group backups** - Use `create_top_index.py` to add landing page

## Testing

Tested with existing group backup `groups_backup_20260316_130740`:
- Created top-level index.html successfully
- Thread pages now link correctly to groups_index.html
- Navigation works as expected

## Benefits

1. **Better UX**: Single entry point (`index.html`) for all backups
2. **Consistent**: Both backup types now have landing pages
3. **Informative**: Landing page shows backup statistics
4. **Backward Compatible**: Main backup unchanged, group backups enhanced