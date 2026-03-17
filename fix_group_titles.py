#!/usr/bin/env python3
"""
Fix missing titles in group backup JSON by extracting them from URLs.

This script updates all_messages.json to add titles extracted from URLs
when the title field is empty.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List


def extract_title_from_url(url: str) -> str:
    """
    Extract title from URL.
    
    URL format: /t5/GROUP-NAME/TITLE/td-p/ID or /t5/GROUP-NAME/TITLE/m-p/ID
    Example: /t5/RH124-Red-Hat-System/Guided-Exercise-ch07s07/m-p/57659
    Returns: "Guided Exercise Ch07S07"
    """
    try:
        url_parts = url.split("/")
        # Find index of td-p or m-p
        for i, part in enumerate(url_parts):
            if part in ("td-p", "m-p") and i > 0:
                # Title is the part before td-p/m-p
                title_slug = url_parts[i - 1]
                # Convert URL slug to readable title (replace hyphens with spaces)
                return title_slug.replace("-", " ").title()
    except Exception as e:
        print(f"Warning: Could not extract title from URL {url}: {e}")
    
    return "Untitled"


def fix_titles(backup_dir: Path) -> None:
    """Fix missing titles in all_messages.json."""
    
    messages_file = backup_dir / "all_messages.json"
    
    if not messages_file.exists():
        print(f"Error: {messages_file} not found")
        sys.exit(1)
    
    print(f"Loading messages from {messages_file}")
    with open(messages_file, "r", encoding="utf-8") as f:
        messages: List[Dict] = json.load(f)
    
    print(f"Found {len(messages)} messages")
    
    # Fix empty titles
    fixed_count = 0
    for msg in messages:
        title = msg.get("title", "")
        if not title or (isinstance(title, str) and title.strip() == ""):
            url = msg.get("url", "")
            if url:
                new_title = extract_title_from_url(url)
                msg["title"] = new_title
                fixed_count += 1
                print(f"  Fixed: {url} -> '{new_title}'")
    
    if fixed_count == 0:
        print("No empty titles found - nothing to fix!")
        return
    
    # Save updated messages
    print(f"\nFixed {fixed_count} empty titles")
    print(f"Saving updated messages to {messages_file}")
    
    with open(messages_file, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2, ensure_ascii=False)
    
    print("✅ Done! Now regenerate HTML with:")
    print(f"   uv run python regenerate_groups_html.py {backup_dir.name}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python fix_group_titles.py <backup_directory>")
        print("\nExample:")
        print("  python fix_group_titles.py groups_backup_20260315_201647")
        sys.exit(1)
    
    backup_dir = Path(sys.argv[1])
    
    if not backup_dir.exists():
        print(f"Error: Backup directory not found: {backup_dir}")
        sys.exit(1)
    
    fix_titles(backup_dir)


if __name__ == "__main__":
    main()

# Made with Bob
