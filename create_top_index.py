#!/usr/bin/env python3
"""
Create a top-level index.html for existing group backups.
Use this to add the convenient top-level index to backups created before this feature.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def main():
    if len(sys.argv) < 2:
        print("Usage: python create_top_index.py <backup_directory>")
        print("Example: python create_top_index.py groups_backup_20260314_123456")
        sys.exit(1)
    
    backup_dir = Path(sys.argv[1])
    
    if not backup_dir.exists():
        print(f"Error: Directory {backup_dir} does not exist")
        sys.exit(1)
    
    # Check if html/groups_index.html exists
    groups_index = backup_dir / "html" / "groups_index.html"
    if not groups_index.exists():
        print(f"Error: {groups_index} not found")
        print("This script is for backups that already have HTML generated.")
        print("Run regenerate_groups_html.py first if needed.")
        sys.exit(1)
    
    # Load metadata
    messages_file = backup_dir / "all_messages.json"
    groups_file = backup_dir / "groups.json"
    
    num_messages = 0
    num_groups = 0
    num_threads = 0
    
    if messages_file.exists():
        with open(messages_file, "r", encoding="utf-8") as f:
            messages = json.load(f)
            num_messages = len(messages)
            # Count unique threads
            threads = set()
            for msg in messages:
                url = msg.get("url", "")
                # Extract thread identifier
                if "/td-p/" in url:
                    thread_id = url.split("/td-p/")[1].split("/")[0].split("#")[0].split("?")[0]
                elif "/m-p/" in url:
                    thread_id = url.split("/m-p/")[1].split("/")[0].split("#")[0].split("?")[0]
                else:
                    thread_id = url
                threads.add(thread_id)
            num_threads = len(threads)
    
    if groups_file.exists():
        with open(groups_file, "r", encoding="utf-8") as f:
            groups = json.load(f)
            num_groups = len(groups)
    
    # Create top-level index.html
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
                <span class="info-label">Groups Backed Up:</span> {num_groups}
            </div>
            <div class="info-item">
                <span class="info-label">Total Messages:</span> {num_messages}
            </div>
            <div class="info-item">
                <span class="info-label">Total Threads:</span> {num_threads}
            </div>
            <div class="info-item">
                <span class="info-label">Index Created:</span> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
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
    
    with open(top_index_file, "w", encoding="utf-8") as f:
        f.write(top_index_content)
    
    print(f"✅ Created {top_index_file}")
    print(f"🌐 Open {top_index_file.resolve()} in your browser")

if __name__ == "__main__":
    main()

# Made with Bob