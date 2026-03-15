#!/usr/bin/env python3
"""
Extract subjects and board names from URLs in the backup data.
This fixes missing subject and board information.
"""

import json
import re
from pathlib import Path
from urllib.parse import unquote

def extract_subject_from_url(url: str) -> str:
    """Extract subject from Khoros URL pattern."""
    # Pattern: /t5/BOARD/SUBJECT/td-p/ID or /t5/BOARD/SUBJECT/m-p/ID
    match = re.search(r'/t5/[^/]+/([^/]+?)/(td-p|m-p)/', url)
    if match:
        subject_slug = match.group(1)
        # Convert slug to readable title
        subject = subject_slug.replace('-', ' ')
        # Decode URL encoding
        subject = unquote(subject)
        # Capitalize first letter of each word
        subject = ' '.join(word.capitalize() for word in subject.split())
        return subject
    return "Untitled"

def extract_board_from_url(url: str) -> str:
    """Extract board name from Khoros URL pattern."""
    # Pattern: /t5/BOARD/...
    match = re.search(r'/t5/([^/]+)/', url)
    if match:
        board_slug = match.group(1)
        # Convert slug to readable name
        board = board_slug.replace('-', ' ')
        board = unquote(board)
        # Capitalize appropriately
        board = ' '.join(word.capitalize() for word in board.split())
        return board
    return "Unknown Board"

def main():
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python fix_subjects_and_boards.py <backup_directory>")
        print("Example: python fix_subjects_and_boards.py backup_20260312_144215")
        sys.exit(1)
    
    backup_dir = Path(sys.argv[1])
    messages_file = backup_dir / "json" / "messages.jsonl"
    
    if not messages_file.exists():
        print(f"Error: {messages_file} not found")
        sys.exit(1)
    
    print(f"Reading messages from {messages_file}...")
    messages = []
    with open(messages_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                messages.append(json.loads(line))
    
    print(f"Loaded {len(messages)} messages")
    
    # Fix subjects and add board info
    fixed_count = 0
    board_count = 0
    
    for msg in messages:
        url = msg.get("url", "")
        
        # Extract and set subject if missing
        if not msg.get("subject"):
            subject = extract_subject_from_url(url)
            msg["subject"] = subject
            fixed_count += 1
        
        # Extract and add board name
        board = extract_board_from_url(url)
        msg["board"] = board
        board_count += 1
    
    print(f"Fixed {fixed_count} missing subjects")
    print(f"Added board info to {board_count} messages")
    
    # Write back to file
    print(f"\nWriting updated messages to {messages_file}...")
    with open(messages_file, "w", encoding="utf-8") as f:
        for msg in messages:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
    
    print("✅ Done! Messages updated with subjects and board names")
    print("\nNow run: uv run regenerate_html.py", sys.argv[1])

if __name__ == "__main__":
    main()

# Made with Bob
