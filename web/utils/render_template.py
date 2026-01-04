from info import BIN_CHANNEL, URL
from utils import temp
import urllib.parse
import html
import logging

# Logger Setup
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 🎨 STREAMING TEMPLATE (Netflix Style - Clean Dark)
# ─────────────────────────────────────────────
watch_tmplt = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{heading}</title>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap">
    <link rel="stylesheet" href="https://cdn.plyr.io/3.7.8/plyr.css" />
    <style>
        :root {{
            --bg-color: #141414; /* Netflix-like deep dark background */
            --surface-color: #1f1f1f;
            --primary-accent: #818cf8; /* Keep bot's accent color for consistency */
            --text-main: #ffffff;
            --text-sub: #a3a3a3;
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 1rem;
        }}
        
        .main-container {{
            width: 100%;
            max-width: 1100px;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }}

        .header {{
            padding: 0.5rem 0;
        }}
        
        .file-title {{
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--text-main);
            word-break: break-all;
            line-height: 1.4;
        }}

        .player-wrapper {{
            width: 100%;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            background: #000;
        }}

        .video-container {{
            position: relative;
            width: 100%;
        }}

        /* Customizing Plyr to blend with dark theme */
        .plyr--video {{
            --plyr-color-main: var(--primary-accent);
            --plyr-video-background: #000;
        }}

        .actions-container {{
            display: flex;
            gap: 1rem;
            margin-top: 0.5rem;
            flex-wrap: wrap;
        }}

        .btn {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.75rem;
            padding: 0.9rem 1.5rem;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 1rem;
            transition: all 0.2s ease;
            cursor: pointer;
            border: none;
            flex: 1;
            min-width: 200px;
        }}

        /* Primary Button (Download) - Prominent */
        .btn-primary {{
            background: var(--text-main);
            color: var(--bg-color);
        }}
        .btn-primary:hover {{
            background: #e6e6e6;
            transform: translateY(-2px);
        }}
        
        /* Secondary Button (Copy Link) - Subtle */
        .btn-secondary {{
            background: rgba(255, 255, 255, 0.15);
            color: var(--text-main);
            backdrop-filter: blur(10px);
        }}
        .btn-secondary:hover {{
            background: rgba(255, 255, 255, 0.25);
        }}

        /* Toast Notification */
        #toast {{
            visibility: hidden;
            min-width: 250px;
            background-color: var(--surface-color);
            color: var(--text-main);
            text-align: center;
            border-radius: 8px;
            padding: 16px;
            position: fixed;
            z-index: 99;
            left: 50%;
            bottom: 30px;
            transform: translateX(-50%);
            font-size: 14px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        #toast.show {{ visibility: visible; -webkit-animation: fadein 0.5s, fadeout 0.5s 2.5s; animation: fadein 0.5s, fadeout 0.5s 2.5s; }}
        
        @keyframes fadein {{ from {{bottom: 0; opacity: 0;}} to {{bottom: 30px; opacity: 1;}} }}
        @keyframes fadeout {{ from {{bottom: 30px; opacity: 1;}} to {{bottom: 0; opacity: 0;}} }}
    </style>
</head>
<body>

    <div class="main-container">
        <div class="header">
            <div class="file-title">{file_name}</div>
        </div>

        <div class="player-wrapper">
            <div class="video-container">
                <video id="player" playsinline>
                    <source src="{src}" type="{mime_type}" />
                </video>
            </div>
        </div>

        <div class="actions-container">
            <a href="{src}" class="btn btn-primary">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                Download Video
            </a>

            <button onclick="copyLink()" class="btn btn-secondary">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                Copy Stream Link
            </button>
        </div>
    </div>

    <div id="toast">Link Copied to Clipboard!</div>

    <script src="https://cdn.plyr.io/3.7.8/plyr.js"></script>
    <script>
        // Initialize Plyr player WITHOUT volume controls
        const player = new Plyr('#player', {{
            controls: ['play-large', 'play', 'progress', 'current-time', 'duration', 'settings', 'pip', 'fullscreen'],
            settings: ['speed'],
            hideControls: true, // Hide controls when idle for cinemtaic feel
        }});

        function copyLink() {{
            const el = document.createElement('textarea');
            el.value = "{src}";
            document.body.appendChild(el);
            el.select();
            document.execCommand('copy');
            document.body.removeChild(el);
            
            var x = document.getElementById("toast");
            x.className = "show";
            setTimeout(function(){{ x.className = x.className.replace("show", ""); }}, 3000);
        }}
    </script>
</body>
</html>
"""

async def media_watch(message_id):
    try:
        media_msg = await temp.BOT.get_messages(BIN_CHANNEL, message_id)
        media = getattr(media_msg, media_msg.media.value, None)
        
        if not media:
            return "<h2>❌ File Not Found or Deleted</h2>"

        # Generate Clean Stream Link
        src = urllib.parse.urljoin(URL, f'download/{message_id}')
        
        # Check MIME Type
        mime_type = getattr(media, 'mime_type', 'video/mp4')
        tag = mime_type.split('/')[0].strip()
        
        if tag == 'video':
            # Clean Data for Template
            file_name = html.escape(media.file_name if hasattr(media, 'file_name') else "Unknown Video")
            heading = f"Watch - {file_name}"
            
            # Fill Template safely
            return watch_tmplt.format(
                heading=heading,
                file_name=file_name,
                src=src,
                mime_type=mime_type
            )
        else:
            # Simplified Error Page for non-video files
            return f"""
            <body style="background:#141414; color:white; display:flex; align-items:center; justify-content:center; height:100vh; font-family:sans-serif;">
                <div style="text-align:center; padding:30px; background:#1f1f1f; border-radius:12px;">
                    <h2 style="margin-bottom:1rem;">⚠️ Not a Playable Video</h2>
                    <p style="color:#a3a3a3; margin-bottom:1.5rem;">This file type ({mime_type}) cannot be streamed directly.</p>
                    <a href="{src}" style="padding:12px 24px; background:white; color:#141414; text-decoration:none; border-radius:8px; font-weight:bold;">Download File</a>
                </div>
            </body>
            """
    except Exception as e:
        logger.error(f"Render Template Error: {e}")
        return f"<h2>⚠️ Error: {str(e)}</h2>"

