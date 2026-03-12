"""
HTML generation functions for rhlc-backup.py
Generates thread pages with replies in proper order
"""

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List
from bs4 import BeautifulSoup


def slugify(text: str, max_len: int = 80) -> str:
    """Convert text to URL-safe slug."""
    text = text.strip()
    text = text.replace("&", "and").replace("/", "_").replace("\\", "_")
    text = re.sub(r"[^\w\s\-]", "", text)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[_\-]{2,}", "_", text)
    text = text.strip("_-")
    return text[:max_len]


def group_messages_by_thread(messages: List[Dict]) -> Dict[str, List[Dict]]:
    """Group messages by thread URL (remove anchors and query params)."""
    threads = defaultdict(list)
    
    for msg in messages:
        url = msg.get("url", "")
        # Extract base thread URL (remove /jump-to/, anchors, query params)
        base_url = url.split("/jump-to/")[0].split("#")[0].split("?")[0]
        # Also handle /m-p/ vs /td-p/ - they're the same thread
        base_url = base_url.replace("/m-p/", "/td-p/")
        threads[base_url].append(msg)
    
    return threads


def transform_message_html(body: str, downloaded_media: Dict) -> str:
    """Transform message body HTML with local image references."""
    if not body:
        return ""
    
    soup = BeautifulSoup(body, "lxml")
    
    # Replace image URLs with local paths
    for img in soup.find_all("img"):
        src = img.get("src")
        if src and isinstance(src, str):
            # Check if we have this image locally
            local_file = downloaded_media.get("images", {}).get(src)
            if local_file:
                img["src"] = f"../images/{local_file}"
    
    # Extract body content
    body_elem = soup.find("body")
    if body_elem:
        return "".join(str(c) for c in body_elem.children)
    return str(soup)


THREAD_CSS = """
*, *::before, *::after { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
       font-size: 16px; line-height: 1.6; color: #1a1a1a; background: #f5f5f5; margin: 0; padding: 0; }
.container { max-width: 1000px; margin: 0 auto; background: #fff; min-height: 100vh; }
.header { background: #cc0000; color: #fff; padding: 20px 30px; }
.header h1 { margin: 0; font-size: 1.4rem; font-weight: 700; }
.header .subtitle { font-size: 0.85rem; opacity: 0.9; margin-top: 5px; }
.content { padding: 30px; }
.breadcrumb { font-size: 0.85rem; color: #666; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 1px solid #eee; }
.breadcrumb a { color: #cc0000; text-decoration: none; }
.breadcrumb a:hover { text-decoration: underline; }
.thread-title { font-size: 1.8rem; font-weight: 700; color: #1a1a1a; margin: 0 0 20px 0; line-height: 1.3; }
.message { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 20px; overflow: hidden; }
.message-header { background: #f8f8f8; padding: 15px 20px; border-bottom: 1px solid #e0e0e0; }
.message-author { font-weight: 700; color: #1a1a1a; font-size: 1.05rem; }
.message-time { color: #666; font-size: 0.85rem; margin-top: 3px; }
.message-body { padding: 20px; line-height: 1.75; }
.message-body p { margin: 0 0 1em 0; }
.message-body ul, .message-body ol { margin: 0 0 1em 1.5em; }
.message-body img { max-width: 100%; height: auto; border-radius: 4px; margin: 1em 0; }
.message-body pre { background: #f4f4f4; border: 1px solid #ddd; border-left: 4px solid #cc0000; 
                    border-radius: 4px; padding: 15px; overflow-x: auto; margin: 1em 0; }
.message-body code { font-family: 'SFMono-Regular', Consolas, monospace; font-size: 0.9em; 
                     background: #f0f0f0; padding: 2px 5px; border-radius: 3px; }
.message-body pre code { background: none; padding: 0; }
.message-body a { color: #cc0000; word-break: break-word; }
.message-body a:hover { text-decoration: underline; }
.reply-indicator { background: #e8f0fe; border-left: 4px solid #1a73e8; padding: 10px 15px; 
                   margin-bottom: 15px; font-size: 0.9rem; color: #1a73e8; }
.back-link { display: inline-block; color: #cc0000; text-decoration: none; font-weight: 500; 
             margin-bottom: 20px; padding: 8px 15px; background: #f8f8f8; border-radius: 5px; }
.back-link:hover { background: #e8e8e8; }
.footer { margin-top: 40px; padding: 20px 30px; border-top: 1px solid #eee; 
          text-align: center; font-size: 0.8rem; color: #999; }
"""


def generate_thread_html(thread_url: str, messages: List[Dict], downloaded_media: Dict) -> tuple:
    """Generate HTML page for a thread with all replies."""
    if not messages:
        return "", ""
    
    # Sort messages by post time if available
    messages = sorted(messages, key=lambda m: m.get("post_time", ""))
    
    # First message is the thread starter
    first_msg = messages[0]
    subject = first_msg.get("subject", "Untitled Thread")
    
    # Create filename
    filename = f"{slugify(subject)}.html"
    
    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject} - RHLC Backup</title>
    <style>{THREAD_CSS}</style>
</head>
<body>
    <div class="header">
        <h1>Red Hat Learning Community</h1>
        <div class="subtitle">Offline Backup</div>
    </div>
    <div class="container">
        <div class="content">
            <a href="../index.html" class="back-link">← Back to Index</a>
            <div class="breadcrumb">
                <a href="../index.html">Home</a> › {subject}
            </div>
            <h1 class="thread-title">{subject}</h1>
"""
    
    # Add each message
    for i, msg in enumerate(messages):
        author = msg.get("author", "Unknown")
        post_time = msg.get("post_time", "")
        body = transform_message_html(msg.get("body", ""), downloaded_media)
        
        reply_indicator = ""
        if i > 0:
            reply_indicator = f'<div class="reply-indicator">Reply #{i}</div>'
        
        html += f"""
            <div class="message">
                <div class="message-header">
                    <div class="message-author">{author}</div>
                    <div class="message-time">{post_time}</div>
                </div>
                <div class="message-body">
                    {reply_indicator}
                    {body}
                </div>
            </div>
"""
    
    html += """
            <div class="footer">
                Exported from learn.redhat.com — Offline Archive
            </div>
        </div>
    </div>
</body>
</html>
"""
    
    return filename, html


def generate_index_html(boards: List[Dict], thread_files: List[Dict], 
                       messages_count: int, downloaded_media: Dict) -> str:
    """Generate main index HTML."""
    from datetime import datetime
    
    # Group threads by first letter for easier navigation
    threads_by_letter = defaultdict(list)
    for thread in sorted(thread_files, key=lambda t: t["subject"].lower()):
        first_letter = thread["subject"][0].upper() if thread["subject"] else "#"
        if not first_letter.isalpha():
            first_letter = "#"
        threads_by_letter[first_letter].append(thread)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RHLC Backup - {datetime.now().strftime('%Y-%m-%d')}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; 
                     padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #cc0000; margin-top: 0; }}
        .stats {{ background: #f8f8f8; padding: 15px; border-radius: 5px; margin: 20px 0; 
                 display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .stat {{ text-align: center; }}
        .stat-value {{ font-size: 2rem; font-weight: 700; color: #cc0000; }}
        .stat-label {{ font-size: 0.85rem; color: #666; text-transform: uppercase; }}
        .letter-section {{ margin: 30px 0; }}
        .letter-header {{ font-size: 1.5rem; font-weight: 700; color: #cc0000; 
                         padding: 10px 0; border-bottom: 2px solid #cc0000; margin-bottom: 15px; }}
        .thread-list {{ list-style: none; padding: 0; margin: 0; }}
        .thread-item {{ padding: 12px; border-bottom: 1px solid #eee; display: flex; 
                       justify-content: space-between; align-items: center; }}
        .thread-item:hover {{ background: #f8f8f8; }}
        .thread-link {{ color: #1a1a1a; text-decoration: none; font-weight: 500; flex: 1; }}
        .thread-link:hover {{ color: #cc0000; }}
        .thread-meta {{ font-size: 0.85rem; color: #666; margin-left: 15px; }}
        .reply-count {{ background: #e8f0fe; color: #1a73e8; padding: 3px 10px; 
                       border-radius: 12px; font-size: 0.8rem; font-weight: 600; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; 
                  text-align: center; font-size: 0.85rem; color: #999; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Red Hat Learning Community - Complete Backup</h1>
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{len(thread_files)}</div>
                <div class="stat-label">Threads</div>
            </div>
            <div class="stat">
                <div class="stat-value">{messages_count}</div>
                <div class="stat-label">Messages</div>
            </div>
            <div class="stat">
                <div class="stat-value">{len(boards)}</div>
                <div class="stat-label">Boards</div>
            </div>
            <div class="stat">
                <div class="stat-value">{len(downloaded_media.get('images', {}))}</div>
                <div class="stat-label">Images</div>
            </div>
        </div>
        
        <h2>All Threads (A-Z)</h2>
"""
    
    for letter in sorted(threads_by_letter.keys()):
        threads = threads_by_letter[letter]
        html += f"""
        <div class="letter-section">
            <div class="letter-header">{letter}</div>
            <ul class="thread-list">
"""
        for thread in threads:
            replies = thread["replies"]
            reply_badge = f'<span class="reply-count">{replies} replies</span>' if replies > 0 else ""
            html += f"""
                <li class="thread-item">
                    <a href="threads/{thread['filename']}" class="thread-link">{thread['subject']}</a>
                    <span class="thread-meta">by {thread['author']} {reply_badge}</span>
                </li>
"""
        html += """
            </ul>
        </div>
"""
    
    html += f"""
        <div class="footer">
            <p>Backup created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Exported from learn.redhat.com</p>
        </div>
    </div>
</body>
</html>
"""
    
    return html

# Made with Bob
