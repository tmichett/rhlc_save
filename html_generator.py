"""
HTML generation functions for rhlc-backup.py
Generates thread pages with replies in proper order
"""

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set
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


def make_unique_filename(base_slug: str, used_filenames: Set[str]) -> str:
    """Generate unique filename by adding counter if needed."""
    filename = f"{base_slug}.html"
    
    if filename not in used_filenames:
        used_filenames.add(filename)
        return filename
    
    # Add counter to make unique
    counter = 2
    while True:
        filename = f"{base_slug}_{counter}.html"
        if filename not in used_filenames:
            used_filenames.add(filename)
            return filename
        counter += 1


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
            # Normalize the URL (handle both relative and absolute)
            from urllib.parse import urljoin
            full_url = urljoin("https://learn.redhat.com", src)
            
            # Check if we have this image locally (try both original and normalized URLs)
            local_file = downloaded_media.get("images", {}).get(src)
            if not local_file:
                local_file = downloaded_media.get("images", {}).get(full_url)
            
            if local_file:
                img["src"] = f"../images/{local_file}"
            else:
                # Keep original src but mark as potentially missing
                alt_text = img.get("alt")
                if alt_text and isinstance(alt_text, str):
                    img["alt"] = alt_text + " [Image not downloaded]"
                else:
                    img["alt"] = "[Image not downloaded]"
    
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
.attachments { margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 6px; border-left: 4px solid #cc0000; }
.attachments h4 { margin: 0 0 10px 0; font-size: 0.95rem; color: #1a1a1a; }
.attachment-list { list-style: none; padding: 0; margin: 0; }
.attachment-list li { padding: 8px 0; border-bottom: 1px solid #e0e0e0; }
.attachment-list li:last-child { border-bottom: none; }
.attachment-link { color: #cc0000; text-decoration: none; font-weight: 500; display: inline-flex; align-items: center; gap: 8px; }
.attachment-link:hover { text-decoration: underline; }
.attachment-missing { color: #999; font-style: italic; }
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


def generate_thread_html(thread_url: str, messages: List[Dict], downloaded_media: Dict,
                        used_filenames: Set[str], attachments_dir: Path | None = None) -> tuple:
    """Generate HTML page for a thread with all replies."""
    if not messages:
        return "", ""
    
    # Sort messages by post time if available
    messages = sorted(messages, key=lambda m: m.get("post_time", ""))
    
    # First message is the thread starter
    first_msg = messages[0]
    subject = first_msg.get("subject", "Untitled Thread")
    
    # Create unique filename
    base_slug = slugify(subject)
    filename = make_unique_filename(base_slug, used_filenames)
    
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
        attachments = msg.get("attachments", [])
        
        reply_indicator = ""
        if i > 0:
            reply_indicator = f'<div class="reply-indicator">Reply #{i}</div>'
        
        # Build attachments HTML
        attachments_html = ""
        if attachments:
            attachments_html = '<div class="attachments"><h4>📎 Attachments:</h4><ul class="attachment-list">'
            for att in attachments:
                att_url = att.get("url", "")
                att_filename = att.get("filename", "attachment")
                # Check if we downloaded this attachment
                local_file = downloaded_media.get("attachments", {}).get(att_url)
                if local_file:
                    attachments_html += f'<li><a href="../attachments/{local_file}" class="attachment-link" download>📄 {att_filename}</a></li>'
                else:
                    attachments_html += f'<li><span class="attachment-missing">📄 {att_filename} (not downloaded)</span></li>'
            attachments_html += '</ul></div>'
        
        html += f"""
            <div class="message">
                <div class="message-header">
                    <div class="message-author">{author}</div>
                    <div class="message-time">{post_time}</div>
                </div>
                <div class="message-body">
                    {reply_indicator}
                    {body}
                    {attachments_html}
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
    """Generate main index HTML with board-based organization."""
    from datetime import datetime
    
    # Group threads by board using the board_name from thread data
    threads_by_board = defaultdict(list)
    
    for thread in thread_files:
        # Use board_name if available (from message data), otherwise try to extract from URL
        board_name = thread.get("board_name", "Other")
        if not board_name or board_name == "Unknown Board":
            board_name = "Other"
        
        thread["board_title"] = board_name
        threads_by_board[board_name].append(thread)
    
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
        .board-section {{ margin: 30px 0; background: #fff; border: 1px solid #e0e0e0;
                         border-radius: 8px; overflow: hidden; }}
        .board-header {{ background: linear-gradient(135deg, #cc0000 0%, #990000 100%);
                        color: #fff; padding: 20px 25px; cursor: pointer;
                        display: flex; justify-content: space-between; align-items: center; }}
        .board-header:hover {{ background: linear-gradient(135deg, #b30000 0%, #800000 100%); }}
        .board-title {{ font-size: 1.3rem; font-weight: 700; margin: 0; }}
        .board-count {{ background: rgba(255,255,255,0.2); padding: 5px 12px;
                       border-radius: 15px; font-size: 0.9rem; }}
        .board-content {{ padding: 0; }}
        .thread-list {{ list-style: none; padding: 0; margin: 0; }}
        .thread-item {{ padding: 15px 25px; border-bottom: 1px solid #f0f0f0;
                       display: flex; justify-content: space-between; align-items: center;
                       transition: background 0.2s; }}
        .thread-item:last-child {{ border-bottom: none; }}
        .thread-item:hover {{ background: #f8f8f8; }}
        .thread-link {{ color: #1a1a1a; text-decoration: none; font-weight: 500;
                       flex: 1; font-size: 1.05rem; }}
        .thread-link:hover {{ color: #cc0000; }}
        .thread-meta {{ font-size: 0.85rem; color: #666; margin-left: 15px;
                       display: flex; gap: 10px; align-items: center; }}
        .reply-count {{ background: #e8f0fe; color: #1a73e8; padding: 4px 12px;
                       border-radius: 12px; font-size: 0.8rem; font-weight: 600; }}
        .author-name {{ color: #666; }}
        .toggle-icon {{ font-size: 1.2rem; transition: transform 0.3s; }}
        .board-content.collapsed {{ display: none; }}
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
        
        <h2>Boards & Threads</h2>
        <p style="color: #666; margin-bottom: 30px;">Click on a board to expand and view threads</p>
"""
    
    # Sort boards alphabetically
    for board_title in sorted(threads_by_board.keys()):
        threads = sorted(threads_by_board[board_title], key=lambda t: t["subject"].lower())
        thread_count = len(threads)
        
        # Create a unique ID for this board
        board_id = slugify(board_title, max_len=50)
        
        html += f"""
        <div class="board-section" data-board-id="{board_id}">
            <div class="board-header" onclick="toggleBoard(this)">
                <div>
                    <div class="board-title">{board_title}</div>
                </div>
                <div style="display: flex; align-items: center; gap: 15px;">
                    <span class="board-count">{thread_count} threads</span>
                    <span class="toggle-icon">▶</span>
                </div>
            </div>
            <div class="board-content collapsed">
                <ul class="thread-list">
"""
        for thread in threads:
            replies = thread["replies"]
            reply_badge = f'<span class="reply-count">{replies} replies</span>' if replies > 0 else ""
            html += f"""
                    <li class="thread-item">
                        <a href="threads/{thread['filename']}" class="thread-link" onclick="localStorage.setItem('lastViewedBoard', '{board_id}')">{thread['subject']}</a>
                        <span class="thread-meta">
                            <span class="author-name">by {thread['author']}</span>
                            {reply_badge}
                        </span>
                    </li>
"""
        html += """
                </ul>
            </div>
        </div>
"""
    
    html += f"""
        <div class="footer">
            <p>Backup created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Exported from learn.redhat.com</p>
        </div>
    </div>
    
    <script>
    // Restore expanded state from localStorage on page load
    document.addEventListener('DOMContentLoaded', function() {{
        const expandedBoards = JSON.parse(localStorage.getItem('expandedBoards') || '[]');
        const lastViewedBoard = localStorage.getItem('lastViewedBoard');
        
        // If returning from a thread, auto-expand that board
        if (lastViewedBoard) {{
            if (!expandedBoards.includes(lastViewedBoard)) {{
                expandedBoards.push(lastViewedBoard);
                localStorage.setItem('expandedBoards', JSON.stringify(expandedBoards));
            }}
            localStorage.removeItem('lastViewedBoard'); // Clear after use
        }}
        
        expandedBoards.forEach(boardId => {{
            const boardSection = document.querySelector(`[data-board-id="${{boardId}}"]`);
            if (boardSection) {{
                const content = boardSection.querySelector('.board-content');
                const icon = boardSection.querySelector('.toggle-icon');
                if (content && icon) {{
                    content.classList.remove('collapsed');
                    icon.textContent = '▼';
                }}
            }}
        }});
    }});
    
    function toggleBoard(header) {{
        const boardSection = header.closest('.board-section');
        const boardId = boardSection.getAttribute('data-board-id');
        const content = header.nextElementSibling;
        const icon = header.querySelector('.toggle-icon');
        
        // Get current expanded boards from localStorage
        let expandedBoards = JSON.parse(localStorage.getItem('expandedBoards') || '[]');
        
        if (content.classList.contains('collapsed')) {{
            // Expand
            content.classList.remove('collapsed');
            icon.textContent = '▼';
            // Add to expanded list if not already there
            if (!expandedBoards.includes(boardId)) {{
                expandedBoards.push(boardId);
            }}
        }} else {{
            // Collapse
            content.classList.add('collapsed');
            icon.textContent = '▶';
            // Remove from expanded list
            expandedBoards = expandedBoards.filter(id => id !== boardId);
        }}
        
        // Save to localStorage
        localStorage.setItem('expandedBoards', JSON.stringify(expandedBoards));
    }}
    </script>
</body>
</html>
"""
    
    return html

# Made with Bob
