#!/usr/bin/env python3
"""
Regenerate HTML files from existing group backup data.
Use this to fix HTML issues without re-downloading media or requiring authentication.
"""

import json
import sys
from pathlib import Path
from html_generator import group_messages_by_thread, generate_thread_html, generate_index_html

def main():
    if len(sys.argv) < 2:
        print("Usage: python regenerate_groups_html.py <backup_directory>")
        print("Example: python regenerate_groups_html.py groups_backup_20260314_123456")
        sys.exit(1)
    
    backup_dir = Path(sys.argv[1])
    
    if not backup_dir.exists():
        print(f"Error: Directory {backup_dir} does not exist")
        sys.exit(1)
    
    # Load messages
    messages_file = backup_dir / "all_messages.json"
    if not messages_file.exists():
        print(f"Error: {messages_file} not found")
        sys.exit(1)
    
    print(f"Loading messages from {messages_file}...")
    with open(messages_file, "r", encoding="utf-8") as f:
        messages = json.load(f)
    
    print(f"Loaded {len(messages)} messages")
    
    # Load groups
    groups_file = backup_dir / "groups.json"
    groups = []
    if groups_file.exists():
        with open(groups_file, "r", encoding="utf-8") as f:
            groups = json.load(f)
        print(f"Loaded {len(groups)} groups")
    
    # Load downloaded media info
    media_file = backup_dir / "media_mapping.json"
    downloaded_media = {"images": {}, "attachments": {}}
    
    if media_file.exists():
        with open(media_file, "r", encoding="utf-8") as f:
            downloaded_media = json.load(f)
        print(f"Loaded {len(downloaded_media.get('images', {}))} image mappings")
        print(f"Loaded {len(downloaded_media.get('attachments', {}))} attachment mappings")
    else:
        print("No media mapping file found, HTML will show media as not downloaded")
    
    # Check for attachments that exist on disk
    attachments_dir = backup_dir / "attachments"
    if attachments_dir.exists():
        existing_attachments = set(f.name for f in attachments_dir.glob("*") if f.is_file())
        print(f"Found {len(existing_attachments)} attachment files on disk")
    else:
        attachments_dir = None
    
    # Generate HTML pages for each thread
    print("\nGenerating HTML pages for threads...")
    html_dir = backup_dir / "html"
    html_dir.mkdir(parents=True, exist_ok=True)
    
    # Clear existing thread files
    for old_file in html_dir.glob("*.html"):
        if old_file.name != "groups_index.html":  # Keep index for now
            old_file.unlink()
    
    threads = group_messages_by_thread(messages)
    thread_files = []
    used_filenames = set()
    
    for i, (thread_url, thread_messages) in enumerate(threads.items(), 1):
        filename, html = generate_thread_html(
            thread_url,
            thread_messages,
            downloaded_media,
            used_filenames,
            attachments_dir,
            "groups_index.html"  # index_link - files are in same directory
        )
        thread_path = html_dir / filename
        thread_path.write_text(html, encoding="utf-8")
        
        # Store for index - use "subject" key for compatibility with html_generator
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
        
        if i % 100 == 0:
            print(f"  Generated {i}/{len(threads)} thread pages")
    
    print(f"Generated {len(threads)} thread HTML pages")
    
    # Generate main index (use empty prefix since files are in same directory)
    print("\nGenerating main index...")
    index_html = generate_index_html(groups, thread_files, len(messages), downloaded_media, thread_path_prefix="")
    index_file = html_dir / "groups_index.html"
    index_file.write_text(index_html, encoding="utf-8")
    
    # Create top-level index.html for easy access
    from datetime import datetime
    top_index_file = backup_dir / "index.html"
    top_index_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RHLC Group Backup</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
               margin: 0; padding: 0; background: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 50px auto; padding: 40px; background: white;
                     border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #cc0000; margin-top: 0; }}
        .subtitle {{ color: #666; margin-bottom: 30px; }}
        .info {{ background: #f8f8f8; padding: 20px; border-radius: 5px; margin: 20px 0; }}
        .info-item {{ margin: 10px 0; }}
        .info-label {{ font-weight: bold; color: #333; }}
        .button {{ display: inline-block; padding: 15px 30px; background: #cc0000; color: white;
                  text-decoration: none; border-radius: 5px; font-weight: 500; margin-top: 20px; }}
        .button:hover {{ background: #aa0000; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;
                  text-align: center; color: #999; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Red Hat Learning Community</h1>
        <div class="subtitle">Group Hub Backup</div>
        
        <div class="info">
            <div class="info-item">
                <span class="info-label">Groups Backed Up:</span> {len(groups)}
            </div>
            <div class="info-item">
                <span class="info-label">Total Messages:</span> {len(messages)}
            </div>
            <div class="info-item">
                <span class="info-label">Total Threads:</span> {len(threads)}
            </div>
            <div class="info-item">
                <span class="info-label">HTML Regenerated:</span> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            </div>
        </div>
        
        <a href="html/groups_index.html" class="button">📚 Browse Backup Content</a>
        
        <div class="footer">
            <p>This is an offline backup of Red Hat Learning Community group discussions.</p>
            <p>All content is stored locally for archival purposes.</p>
        </div>
    </div>
</body>
</html>
"""
    top_index_file.write_text(top_index_content, encoding="utf-8")
    
    print(f"\n✅ HTML regeneration complete!")
    print(f"📁 Output: {backup_dir.resolve()}")
    print(f"🌐 Open {top_index_file.resolve()} to view")

if __name__ == "__main__":
    main()

# Made with Bob
