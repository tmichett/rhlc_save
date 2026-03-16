# Quick Start: Backup RHLC Group Hubs in 3 Steps

Backup Red Hat Learning Community course discussion groups (RH124, RH134, RH294, etc.) in just 3 simple steps!


## ⚠️ Important: Don't Run Multiple Backups Simultaneously

**DO NOT** run group backup and full site backup at the same time! This will trigger rate limiting (HTTP 429 errors) and may block your IP. Always run backups one at a time.

---

## Step 1: Install Playwright (One-Time Setup)

```bash
uv pip install playwright
uv run playwright install chromium
```

**What this does:** Installs browser automation for authentication

**Time:** ~2 minutes

---

## Step 2: Run the Backup

```bash
uv run python backup_groups.py --auto --fast
```

**What happens:**
1. **First browser window:** Opens for login
   - Click "Sign In" and log in with your Red Hat account
   - Press Enter in terminal when logged in
2. **Second browser window:** Opens to discover groups
   - Automatically navigates through all group hub pages
   - Extracts all available groups (may take 1-2 minutes)
   - Browser closes automatically when done
3. Script downloads all discussions, messages, images, and attachments
4. Generates HTML pages for offline viewing

**Time:** 2-4 hours for all groups, 15-30 minutes for specific groups

**Note:** The script opens TWO browser windows:
1. First for authentication (you log in manually)
2. Second for discovering groups (automatic pagination)

**Tip:** To backup only specific groups:
```bash
uv run python backup_groups.py --auto --fast --groups "RH124" "RH134" "RH294"
```

---

## Step 3: View Your Backup

```bash
# Open the HTML index in your browser
open groups_backup_*/html/groups_index.html
```

**What you get:**
- ✅ All group discussions backed up
- ✅ Threaded conversations preserved
- ✅ Images and attachments downloaded
- ✅ Searchable HTML pages
- ✅ Works completely offline

---

## Common Issues & Quick Fixes

### Issue: "No groups found to backup"

**Fix:** Make sure you're logged in and have access to group hubs. Visit https://learn.redhat.com/t5/grouphubs/page to verify.

### Issue: Some attachments show "(not downloaded)"

**Fix:** Session timeout during long backup. Reprocess to fix:
```bash
uv run python reprocess_groups.py --backup-dir groups_backup_20260314_123456 --auto --fast
```

### Issue: Want to regenerate HTML without re-downloading

**Fix:** Use the HTML-only regeneration script:
```bash
uv run python regenerate_groups_html.py groups_backup_20260314_123456
```

---

## Next Steps

### Save Cookies for Future Runs

```bash
# First run - save cookies
uv run python backup_groups.py --auto --save-cookies --fast

# Future runs - use saved cookies (no login needed)
uv run python backup_groups.py --cookies cookies.txt --fast
```

### Backup Specific Groups Only

```bash
# RHCSA courses
uv run python backup_groups.py --auto --fast --groups "RH124" "RH134"

# RHCE courses
uv run python backup_groups.py --auto --fast --groups "RH294"

# Multiple specific groups
uv run python backup_groups.py --auto --fast --groups "RH124" "RH134" "RH294" "RH358"
```

### Fix Corrupted or Missing Media

```bash
# Fix everything (images + attachments)
uv run python reprocess_groups.py --backup-dir groups_backup_20260314_123456 --auto --fast

# Fix only attachments (skip images)
uv run python reprocess_groups.py --backup-dir groups_backup_20260314_123456 --auto --skip-images --fast

# Fix only images (skip attachments)
uv run python reprocess_groups.py --backup-dir groups_backup_20260314_123456 --auto --skip-attachments --fast
```

---

## Output Structure

```
groups_backup_20260314_123456/
├── groups.json              # List of all groups
├── all_messages.json        # All messages combined
├── group_RH124*.json        # Messages per group
├── images/                  # Downloaded images
├── attachments/             # Downloaded attachments
├── html/
│   ├── groups_index.html   # Main index page (open this!)
│   └── thread_*.html       # Individual thread pages
└── media_mapping.json      # Media URL to filename mapping
```

---

## Quick Reference

| Task | Command |
|------|---------|
| **Backup all groups** | `uv run python backup_groups.py --auto --fast` |
| **Backup specific groups** | `uv run python backup_groups.py --auto --fast --groups "RH124" "RH134"` |
| **Fix corrupted media** | `uv run python reprocess_groups.py --backup-dir groups_backup_* --auto --fast` |
| **Regenerate HTML only** | `uv run python regenerate_groups_html.py groups_backup_*` |
| **Use saved cookies** | `uv run python backup_groups.py --cookies cookies.txt --fast` |

---

## Differences from Full Site Backup

| Feature | Full Site (rhlc-backup.py) | Groups (backup_groups.py) |
|---------|---------------------------|---------------------------|
| **Target** | Main community boards | Course discussion groups |
| **Access** | Requires moderator access | Requires valid account |
| **URL** | /t5/forums/* | /t5/grouphubs/* |
| **Index** | index.html | groups_index.html |
| **Use Case** | Complete site archive | Course-specific backup |

---

## Need More Help?

- **Full Documentation:** [GROUP_BACKUP_GUIDE.md](GROUP_BACKUP_GUIDE.md)
- **Troubleshooting:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Main README:** [README.md](README.md)

---

**That's it!** You now have a complete offline backup of your RHLC group discussions. 🎉