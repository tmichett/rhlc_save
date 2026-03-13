#!/usr/bin/env python3
"""
Regenerate HTML files from existing backup data.
Use this to fix HTML issues without re-downloading all messages.
"""

import json
import sys
from pathlib import Path
from html_generator import group_messages_by_thread, generate_thread_html, generate_index_html

def main():
    if len(sys.argv) < 2:
        print("Usage: python regenerate_html.py <backup_directory>")
        print("Example: python regenerate_html.py backup_20260312_144215")
        sys.exit(1)
    
    backup_dir = Path(sys.argv[1])
    
    if not backup_dir.exists():
        print(f"Error: Directory {backup_dir} does not exist")
        sys.exit(1)
    
    # Load messages
    messages_file = backup_dir / "json" / "messages.jsonl"
    if not messages_file.exists():
        print(f"Error: {messages_file} not found")
        sys.exit(1)
    
    print(f"Loading messages from {messages_file}...")
    messages = []
    with open(messages_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                messages.append(json.loads(line))
    
    print(f"Loaded {len(messages)} messages")
    
    # Load boards
    boards_file = backup_dir / "json" / "boards.json"
    boards = []
    if boards_file.exists():
        with open(boards_file, "r", encoding="utf-8") as f:
            boards = json.load(f)
        print(f"Loaded {len(boards)} boards")
    
    # Load downloaded media info
    media_file = backup_dir / "json" / "downloaded_media.json"
    downloaded_media = {"images": {}, "attachments": {}}
    if media_file.exists():
        with open(media_file, "r", encoding="utf-8") as f:
            downloaded_media = json.load(f)
        print(f"Loaded {len(downloaded_media.get('images', {}))} image mappings")
    
    # Generate HTML pages for each thread
    print("\nGenerating HTML pages for threads...")
    threads_dir = backup_dir / "threads"
    threads_dir.mkdir(parents=True, exist_ok=True)
    
    # Clear existing thread files
    for old_file in threads_dir.glob("*.html"):
        old_file.unlink()
    
    threads = group_messages_by_thread(messages)
    thread_files = []
    used_filenames = set()
    
    for i, (thread_url, thread_messages) in enumerate(threads.items(), 1):
        filename, html = generate_thread_html(thread_url, thread_messages, downloaded_media, used_filenames)
        thread_path = threads_dir / filename
        thread_path.write_text(html, encoding="utf-8")
        
        # Store for index
        first_msg = thread_messages[0]
        thread_files.append({
            "filename": filename,
            "subject": first_msg.get("subject", "Untitled"),
            "author": first_msg.get("author", "Unknown"),
            "replies": len(thread_messages) - 1,
            "url": thread_url,
            "board_name": first_msg.get("board", "Other")  # Add board info
        })
        
        if i % 100 == 0:
            print(f"  Generated {i}/{len(threads)} thread pages")
    
    print(f"Generated {len(threads)} thread HTML pages")
    
    # Generate main index
    print("\nGenerating main index...")
    index_html = generate_index_html(boards, thread_files, len(messages), downloaded_media)
    (backup_dir / "index.html").write_text(index_html, encoding="utf-8")
    
    print(f"\n✅ HTML regeneration complete!")
    print(f"📁 Output: {backup_dir.resolve()}")
    print(f"🌐 Open {backup_dir.resolve()}/index.html to view")

if __name__ == "__main__":
    main()

# Made with Bob
