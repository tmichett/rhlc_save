#!/usr/bin/env python3
"""
Verify downloaded media files (images and attachments) in backup directories.

This script checks for:
- Missing media files referenced in JSON
- Corrupted files (SAML redirects, 0-byte files)
- File size anomalies
- Provides detailed statistics and reports

Usage:
    # Verify full site backup
    uv run python verify_backup_media.py backup_20260316_142224
    
    # Verify group hub backup
    uv run python verify_backup_media.py groups_backup_20260316_130740
    
    # Check only attachments
    uv run python verify_backup_media.py backup_20260316_142224 --attachments-only
    
    # Check only images
    uv run python verify_backup_media.py backup_20260316_142224 --images-only
    
    # Verbose output with file details
    uv run python verify_backup_media.py backup_20260316_142224 --verbose
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict


def is_saml_redirect(file_path: Path) -> bool:
    """Check if a file is a SAML redirect page (corrupted download)."""
    try:
        # SAML redirects are typically small HTML files (around 6KB)
        if file_path.stat().st_size > 10000:  # > 10KB, probably not SAML
            return False
        
        # Check file content for SAML indicators
        with open(file_path, 'rb') as f:
            content = f.read(1024)  # Read first 1KB
            
        # Look for SAML-specific strings
        saml_indicators = [
            b'SAMLRequest',
            b'SAMLResponse',
            b'RelayState',
            b'name="SAMLRequest"',
            b'name="SAMLResponse"',
            b'sso.redhat.com',
            b'idp.redhat.com'
        ]
        
        return any(indicator in content for indicator in saml_indicators)
    except Exception:
        return False


def check_media_files(backup_dir: Path, check_images: bool = True, 
                     check_attachments: bool = True, verbose: bool = False) -> Dict:
    """Check media files in backup directory for issues."""
    
    results = {
        'images': {
            'total_referenced': 0,
            'total_downloaded': 0,
            'missing': [],
            'corrupted_saml': [],
            'zero_byte': [],
            'suspicious_size': [],
            'ok': 0
        },
        'attachments': {
            'total_referenced': 0,
            'total_downloaded': 0,
            'missing': [],
            'corrupted_saml': [],
            'zero_byte': [],
            'suspicious_size': [],
            'ok': 0
        }
    }
    
    # Load all messages - handle both full backup and group backup structures
    all_messages_file = backup_dir / "all_messages.json"
    json_dir_file = backup_dir / "json" / "messages.json"
    
    if all_messages_file.exists():
        # Group backup structure
        with open(all_messages_file, 'r', encoding='utf-8') as f:
            messages = json.load(f)
        print(f"📊 Loaded {len(messages)} messages from {all_messages_file.name}")
    elif json_dir_file.exists():
        # Full backup structure
        with open(json_dir_file, 'r', encoding='utf-8') as f:
            messages = json.load(f)
        print(f"📊 Loaded {len(messages)} messages from json/{json_dir_file.name}")
    else:
        print(f"❌ Error: No messages file found")
        print(f"   Looked for: {all_messages_file}")
        print(f"   Looked for: {json_dir_file}")
        return results
    
    print()
    
    # Load media mapping if it exists (for full backups)
    media_mapping_file = backup_dir / "json" / "media_mapping.json"
    if not media_mapping_file.exists():
        media_mapping_file = backup_dir / "media_mapping.json"
    
    media_mapping = {}
    if media_mapping_file.exists():
        with open(media_mapping_file, 'r', encoding='utf-8') as f:
            media_mapping = json.load(f)
    
    # Check images
    if check_images:
        print("🖼️  Checking Images...")
        print("-" * 60)
        
        images_dir = backup_dir / "images"
        referenced_images = set()
        
        # Collect all referenced images
        for msg in messages:
            # Group backup structure: downloaded_media dict
            if 'downloaded_media' in msg and 'images' in msg['downloaded_media']:
                for url, filename in msg['downloaded_media']['images'].items():
                    referenced_images.add(filename)
            # Full backup structure: images array of URLs (strings)
            elif 'images' in msg and isinstance(msg['images'], list):
                for url in msg['images']:
                    if url and isinstance(url, str) and media_mapping.get('images', {}).get(url):
                        referenced_images.add(media_mapping['images'][url])
        
        results['images']['total_referenced'] = len(referenced_images)
        
        if images_dir.exists():
            downloaded_images = set(f.name for f in images_dir.iterdir() if f.is_file())
            results['images']['total_downloaded'] = len(downloaded_images)
            
            # Check each referenced image
            for filename in referenced_images:
                file_path = images_dir / filename
                
                if not file_path.exists():
                    results['images']['missing'].append(filename)
                    if verbose:
                        print(f"  ❌ Missing: {filename}")
                else:
                    file_size = file_path.stat().st_size
                    
                    if file_size == 0:
                        results['images']['zero_byte'].append(filename)
                        if verbose:
                            print(f"  ⚠️  Zero-byte: {filename}")
                    elif is_saml_redirect(file_path):
                        results['images']['corrupted_saml'].append(filename)
                        if verbose:
                            print(f"  🔴 SAML redirect: {filename} ({file_size:,} bytes)")
                    elif file_size < 1000:  # Suspiciously small for an image
                        results['images']['suspicious_size'].append((filename, file_size))
                        if verbose:
                            print(f"  ⚠️  Suspicious size: {filename} ({file_size} bytes)")
                    else:
                        results['images']['ok'] += 1
        else:
            print(f"  ⚠️  Images directory not found: {images_dir}")
        
        print()
    
    # Check attachments
    if check_attachments:
        print("📎 Checking Attachments...")
        print("-" * 60)
        
        attachments_dir = backup_dir / "attachments"
        referenced_attachments = set()
        
        # Collect all referenced attachments
        for msg in messages:
            # Group backup structure: downloaded_media dict
            if 'downloaded_media' in msg and 'attachments' in msg['downloaded_media']:
                for url, filename in msg['downloaded_media']['attachments'].items():
                    referenced_attachments.add(filename)
            # Full backup structure: attachments array of dicts with url/filename
            elif 'attachments' in msg and isinstance(msg['attachments'], list):
                for att in msg['attachments']:
                    if isinstance(att, dict) and 'url' in att:
                        url = att['url']
                        if url and media_mapping.get('attachments', {}).get(url):
                            referenced_attachments.add(media_mapping['attachments'][url])
        
        results['attachments']['total_referenced'] = len(referenced_attachments)
        
        if attachments_dir.exists():
            downloaded_attachments = set(f.name for f in attachments_dir.iterdir() if f.is_file())
            results['attachments']['total_downloaded'] = len(downloaded_attachments)
            
            # Check each referenced attachment
            for filename in referenced_attachments:
                file_path = attachments_dir / filename
                
                if not file_path.exists():
                    results['attachments']['missing'].append(filename)
                    if verbose:
                        print(f"  ❌ Missing: {filename}")
                else:
                    file_size = file_path.stat().st_size
                    
                    if file_size == 0:
                        results['attachments']['zero_byte'].append(filename)
                        if verbose:
                            print(f"  ⚠️  Zero-byte: {filename}")
                    elif is_saml_redirect(file_path):
                        results['attachments']['corrupted_saml'].append(filename)
                        if verbose:
                            print(f"  🔴 SAML redirect: {filename} ({file_size:,} bytes)")
                    elif file_size < 100:  # Suspiciously small for an attachment
                        results['attachments']['suspicious_size'].append((filename, file_size))
                        if verbose:
                            print(f"  ⚠️  Suspicious size: {filename} ({file_size} bytes)")
                    else:
                        results['attachments']['ok'] += 1
        else:
            print(f"  ⚠️  Attachments directory not found: {attachments_dir}")
        
        print()
    
    return results


def print_summary(results: Dict, check_images: bool, check_attachments: bool):
    """Print summary of verification results."""
    
    print("=" * 60)
    print("📋 VERIFICATION SUMMARY")
    print("=" * 60)
    print()
    
    if check_images:
        img = results['images']
        print("🖼️  Images:")
        print(f"  Referenced in JSON: {img['total_referenced']}")
        print(f"  Downloaded files:   {img['total_downloaded']}")
        print(f"  ✅ OK:              {img['ok']}")
        print(f"  ❌ Missing:         {len(img['missing'])}")
        print(f"  🔴 SAML corrupted:  {len(img['corrupted_saml'])}")
        print(f"  ⚠️  Zero-byte:       {len(img['zero_byte'])}")
        print(f"  ⚠️  Suspicious size: {len(img['suspicious_size'])}")
        print()
        
        if img['missing']:
            print(f"  Missing files ({len(img['missing'])}):")
            for filename in img['missing'][:10]:
                print(f"    - {filename}")
            if len(img['missing']) > 10:
                print(f"    ... and {len(img['missing']) - 10} more")
            print()
        
        if img['corrupted_saml']:
            print(f"  SAML corrupted files ({len(img['corrupted_saml'])}):")
            for filename in img['corrupted_saml'][:10]:
                print(f"    - {filename}")
            if len(img['corrupted_saml']) > 10:
                print(f"    ... and {len(img['corrupted_saml']) - 10} more")
            print()
    
    if check_attachments:
        att = results['attachments']
        print("📎 Attachments:")
        print(f"  Referenced in JSON: {att['total_referenced']}")
        print(f"  Downloaded files:   {att['total_downloaded']}")
        print(f"  ✅ OK:              {att['ok']}")
        print(f"  ❌ Missing:         {len(att['missing'])}")
        print(f"  🔴 SAML corrupted:  {len(att['corrupted_saml'])}")
        print(f"  ⚠️  Zero-byte:       {len(att['zero_byte'])}")
        print(f"  ⚠️  Suspicious size: {len(att['suspicious_size'])}")
        print()
        
        if att['missing']:
            print(f"  Missing files ({len(att['missing'])}):")
            for filename in att['missing'][:10]:
                print(f"    - {filename}")
            if len(att['missing']) > 10:
                print(f"    ... and {len(att['missing']) - 10} more")
            print()
        
        if att['corrupted_saml']:
            print(f"  SAML corrupted files ({len(att['corrupted_saml'])}):")
            for filename in att['corrupted_saml'][:10]:
                print(f"    - {filename}")
            if len(att['corrupted_saml']) > 10:
                print(f"    ... and {len(att['corrupted_saml']) - 10} more")
            print()
    
    # Overall status
    print("=" * 60)
    total_issues = 0
    if check_images:
        total_issues += (len(results['images']['missing']) + 
                        len(results['images']['corrupted_saml']) +
                        len(results['images']['zero_byte']))
    if check_attachments:
        total_issues += (len(results['attachments']['missing']) + 
                        len(results['attachments']['corrupted_saml']) +
                        len(results['attachments']['zero_byte']))
    
    if total_issues == 0:
        print("✅ All media files verified successfully!")
    else:
        print(f"⚠️  Found {total_issues} issues that need attention")
        print()
        print("To fix corrupted/missing files:")
        print("  Full backup:  uv run python reprocess_attachments.py --backup-dir <backup_dir> --auto")
        print("  Group backup: uv run python reprocess_groups.py --backup-dir <backup_dir> --auto")
    print("=" * 60)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Verify downloaded media files in RHLC backup',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify all media in full backup
  uv run python verify_backup_media.py backup_20260316_142224
  
  # Verify all media in group backup
  uv run python verify_backup_media.py groups_backup_20260316_130740
  
  # Check only attachments
  uv run python verify_backup_media.py backup_20260316_142224 --attachments-only
  
  # Check only images
  uv run python verify_backup_media.py backup_20260316_142224 --images-only
  
  # Verbose output
  uv run python verify_backup_media.py backup_20260316_142224 --verbose
        """
    )
    
    parser.add_argument('backup_dir', help='Backup directory to verify')
    parser.add_argument('--images-only', action='store_true',
                       help='Only check images')
    parser.add_argument('--attachments-only', action='store_true',
                       help='Only check attachments')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed output for each file')
    
    args = parser.parse_args()
    
    backup_dir = Path(args.backup_dir)
    if not backup_dir.exists():
        print(f"❌ Error: Backup directory not found: {backup_dir}")
        sys.exit(1)
    
    # Determine what to check
    check_images = not args.attachments_only
    check_attachments = not args.images_only
    
    print("=" * 60)
    print("🔍 RHLC Backup Media Verification")
    print("=" * 60)
    print(f"Backup directory: {backup_dir}")
    print(f"Checking: ", end="")
    checks = []
    if check_images:
        checks.append("Images")
    if check_attachments:
        checks.append("Attachments")
    print(", ".join(checks))
    print("=" * 60)
    print()
    
    # Run verification
    results = check_media_files(backup_dir, check_images, check_attachments, args.verbose)
    
    # Print summary
    print_summary(results, check_images, check_attachments)


if __name__ == '__main__':
    main()

# Made with Bob
