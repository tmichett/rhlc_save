# Media Verification Guide

This guide explains how to verify downloaded images and attachments in your RHLC backups using the `verify_backup_media.py` script.

## What Does It Check?

The verification script checks for:

- **Missing files**: Media referenced in JSON but not downloaded
- **SAML redirects**: Corrupted files that are actually SAML authentication pages (~6KB HTML files)
- **Zero-byte files**: Empty files that failed to download
- **Suspicious sizes**: Files that are unusually small and may be corrupted
- **File statistics**: Total counts and health status

## Quick Start

### Verify Full Site Backup

```bash
uv run python verify_backup_media.py backup_20260316_142224
```

### Verify Group Hub Backup

```bash
uv run python verify_backup_media.py groups_backup_20260316_130740
```

## Usage Examples

### Example 1: Check Everything (Default)

```bash
uv run python verify_backup_media.py backup_20260316_142224
```

**Output:**
```
🖼️  Images:
  Referenced in JSON: 1,234
  Downloaded files:   1,200
  ✅ OK:              1,150
  ❌ Missing:         34
  🔴 SAML corrupted:  16
  ⚠️  Zero-byte:       0
  ⚠️  Suspicious size: 0

📎 Attachments:
  Referenced in JSON: 456
  Downloaded files:   450
  ✅ OK:              440
  ❌ Missing:         6
  🔴 SAML corrupted:  10
  ⚠️  Zero-byte:       0
  ⚠️  Suspicious size: 0
```

### Example 2: Check Only Attachments

```bash
uv run python verify_backup_media.py backup_20260316_142224 --attachments-only
```

**When to use:**
- You know images are fine
- Faster verification
- Focus on attachment issues

### Example 3: Check Only Images

```bash
uv run python verify_backup_media.py backup_20260316_142224 --images-only
```

**When to use:**
- You know attachments are fine
- Faster verification
- Focus on image issues

### Example 4: Verbose Output

```bash
uv run python verify_backup_media.py backup_20260316_142224 --verbose
```

**Shows detailed information for each file:**
```
🖼️  Checking Images...
  ❌ Missing: image_abc123.png
  🔴 SAML redirect: image_def456.jpg (6,234 bytes)
  ⚠️  Suspicious size: image_ghi789.gif (234 bytes)
  ✅ OK: image_jkl012.png
  ...
```

**When to use:**
- Debugging specific issues
- Need to see which exact files have problems
- Creating a detailed report

## Understanding the Output

### Status Indicators

| Icon | Status | Meaning |
|------|--------|---------|
| ✅ | OK | File downloaded successfully and appears valid |
| ❌ | Missing | File referenced in JSON but not found on disk |
| 🔴 | SAML corrupted | File is a SAML redirect page (session timeout) |
| ⚠️ | Zero-byte | File exists but is empty (0 bytes) |
| ⚠️ | Suspicious size | File is unusually small and may be corrupted |

### SAML Corruption Detection

The script automatically detects SAML redirect pages by:

1. **Size check**: SAML pages are typically ~6KB
2. **Content check**: Looks for SAML-specific strings:
   - `SAMLRequest`
   - `SAMLResponse`
   - `RelayState`
   - `sso.redhat.com`
   - `idp.redhat.com`

**Example SAML corrupted file:**
```
🔴 SAML redirect: attachment_abc123.pdf (6,234 bytes)
```

This means the file is actually an HTML authentication page, not the real PDF.

### Suspicious Size Thresholds

- **Images**: < 1,000 bytes (1KB)
- **Attachments**: < 100 bytes

Files below these thresholds are flagged as potentially corrupted.

## Fixing Issues

### If Issues Are Found

The script will suggest the appropriate reprocessing command:

**For full site backups:**
```bash
uv run python reprocess_attachments.py --backup-dir backup_20260316_142224 --auto
```

**For group hub backups:**
```bash
uv run python reprocess_groups.py --backup-dir groups_backup_20260316_130740 --auto
```

### Reprocessing Options

After identifying issues, you can:

1. **Fix everything** (images + attachments):
   ```bash
   # Full backup
   uv run python reprocess_attachments.py --backup-dir backup_20260316_142224 --auto
   
   # Group backup
   uv run python reprocess_groups.py --backup-dir groups_backup_20260316_130740 --auto
   ```

2. **Fix only attachments**:
   ```bash
   # Full backup
   uv run python reprocess_attachments.py --backup-dir backup_20260316_142224 --auto --skip-images
   
   # Group backup
   uv run python reprocess_groups.py --backup-dir groups_backup_20260316_130740 --auto --skip-images
   ```

3. **Fix only images**:
   ```bash
   # Full backup
   uv run python reprocess_attachments.py --backup-dir backup_20260316_142224 --auto --skip-attachments
   
   # Group backup
   uv run python reprocess_groups.py --backup-dir groups_backup_20260316_130740 --auto --skip-attachments
   ```

4. **Force re-download everything**:
   ```bash
   # Full backup
   uv run python reprocess_attachments.py --backup-dir backup_20260316_142224 --auto --force
   
   # Group backup
   uv run python reprocess_groups.py --backup-dir groups_backup_20260316_130740 --auto --force
   ```

### Verify After Reprocessing

After reprocessing, run the verification script again to confirm issues are fixed:

```bash
uv run python verify_backup_media.py backup_20260316_142224
```

## Common Scenarios

### Scenario 1: Session Timeout During Backup

**Symptoms:**
- Many SAML corrupted files
- Files are ~6KB instead of expected size
- Happened during a long backup

**Solution:**
```bash
# Reprocess to download the corrupted files
uv run python reprocess_attachments.py --backup-dir backup_20260316_142224 --auto

# Verify the fix
uv run python verify_backup_media.py backup_20260316_142224
```

### Scenario 2: Network Issues During Backup

**Symptoms:**
- Many missing files
- Some zero-byte files
- Backup completed but with errors

**Solution:**
```bash
# Reprocess to download missing files
uv run python reprocess_attachments.py --backup-dir backup_20260316_142224 --auto

# Verify the fix
uv run python verify_backup_media.py backup_20260316_142224
```

### Scenario 3: Partial Backup (Testing)

**Symptoms:**
- Used `--max-messages` or `--max-pages`
- Many missing files (expected)
- Want to verify what was downloaded

**Solution:**
```bash
# Just verify - missing files are expected
uv run python verify_backup_media.py backup_20260316_142224

# No reprocessing needed if this was intentional
```

### Scenario 4: Checking Before Archiving

**Symptoms:**
- Backup completed successfully
- Want to verify before archiving/compressing
- Ensure everything is good

**Solution:**
```bash
# Verify everything
uv run python verify_backup_media.py backup_20260316_142224

# If all OK, safe to archive
tar -czf backup_20260316_142224.tar.gz backup_20260316_142224/
```

## Integration with Backup Workflow

### Recommended Workflow

1. **Run backup**:
   ```bash
   uv run python rhlc-backup.py --auto --fast
   ```

2. **Verify media**:
   ```bash
   uv run python verify_backup_media.py backup_20260316_142224
   ```

3. **Fix issues if found**:
   ```bash
   uv run python reprocess_attachments.py --backup-dir backup_20260316_142224 --auto
   ```

4. **Verify again**:
   ```bash
   uv run python verify_backup_media.py backup_20260316_142224
   ```

5. **Archive when clean**:
   ```bash
   tar -czf backup_20260316_142224.tar.gz backup_20260316_142224/
   ```

### Automated Verification Script

Create a script to automate the verification process:

```bash
#!/bin/bash
# verify_and_fix.sh

BACKUP_DIR=$1

echo "Verifying backup: $BACKUP_DIR"
uv run python verify_backup_media.py "$BACKUP_DIR"

read -p "Fix issues? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Reprocessing..."
    if [[ $BACKUP_DIR == groups_backup_* ]]; then
        uv run python reprocess_groups.py --backup-dir "$BACKUP_DIR" --auto
    else
        uv run python reprocess_attachments.py "$BACKUP_DIR" --auto
    fi
    
    echo "Verifying again..."
    uv run python verify_backup_media.py "$BACKUP_DIR"
fi
```

Usage:
```bash
chmod +x verify_and_fix.sh
./verify_and_fix.sh backup_20260316_142224
```

## Command Reference

| Command | Description |
|---------|-------------|
| `verify_backup_media.py <dir>` | Verify all media in backup |
| `verify_backup_media.py <dir> --images-only` | Check only images |
| `verify_backup_media.py <dir> --attachments-only` | Check only attachments |
| `verify_backup_media.py <dir> --verbose` | Show detailed file-by-file output |
| `verify_backup_media.py <dir> -v` | Short form of --verbose |

## Troubleshooting

### "Backup directory not found"

**Cause:** Invalid path or directory doesn't exist

**Solution:**
```bash
# List available backups
ls -d backup_* groups_backup_*

# Use correct path
uv run python verify_backup_media.py backup_20260316_142224
```

### "all_messages.json not found"

**Cause:** Not a valid backup directory or backup incomplete

**Solution:**
1. Verify you're pointing to the correct directory
2. Check if the backup completed successfully
3. Look for `all_messages.json` in the directory

### Script runs but shows no issues when you know there are problems

**Cause:** Files may not be referenced in JSON

**Solution:**
1. Check if files exist in `images/` or `attachments/` directories
2. Verify the JSON has `downloaded_media` entries
3. Use `--verbose` to see what's being checked

## See Also

- [ATTACHMENT_REPROCESSING_GUIDE.md](ATTACHMENT_REPROCESSING_GUIDE.md) - Detailed guide for fixing attachments
- [GROUP_BACKUP_GUIDE.md](GROUP_BACKUP_GUIDE.md) - Group hub backup guide
- [COMPLETE_BACKUP_GUIDE.md](COMPLETE_BACKUP_GUIDE.md) - Full site backup guide
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - General troubleshooting