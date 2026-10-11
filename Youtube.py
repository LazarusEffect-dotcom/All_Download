import os
import sys
import json
import time
import re
import uuid
import subprocess
import threading
import urllib.parse
from io import BytesIO
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import yt_dlp
import requests
import urllib3

# Suppress insecure SSL warnings for multi-platform metadata lookups
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Ensure console logging handles unicode gracefully on all platforms
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# --- Global Configuration & Theme Setup ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

APP_NAME = "Universal Video Downloader Pro"
APP_VERSION = "v4.0.0"
HISTORY_FILE = "download_history.json"
OLD_HISTORY_FILE = "download_history.txt"
SETTINGS_FILE = "settings.json"

COLOR_BG = "#0F1015"
COLOR_CARD = "#181A20"
COLOR_CARD_HOVER = "#222630"
COLOR_ACCENT = "#FF0033"          # Vibrant Red
COLOR_ACCENT_HOVER = "#CC0029"
COLOR_TEXT_MAIN = "#FFFFFF"
COLOR_TEXT_MUTED = "#A0A5B5"
COLOR_SUCCESS = "#28A745"
COLOR_WARNING = "#FFA500"
COLOR_DANGER = "#DC3545"
COLOR_CYAN = "#00D2FF"
COLOR_PURPLE = "#8A2BE2"

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller bundle."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_ffmpeg_path():
    """Find ffmpeg binary location dynamically."""
    candidates = [
        resource_path("dist/ffmpeg/ffmpeg.exe"),
        resource_path("ffmpeg/ffmpeg.exe"),
        resource_path("ffmpeg.exe"),
        os.path.join(os.path.abspath("."), "dist", "ffmpeg", "ffmpeg.exe"),
        os.path.join(os.path.abspath("."), "ffmpeg", "ffmpeg.exe"),
        "ffmpeg"
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return "ffmpeg"

def load_settings():
    default_settings = {
        "save_folder": os.path.join(os.path.expanduser("~"), "Downloads"),
        "theme": "Dark",
        "default_quality": "Best Available (Max 4K/8K)",
        "download_subtitles": False,
        "audio_bitrate": "320 kbps (Best)",
        "cookie_source": "Auto Detect Browser",
        "max_concurrent_downloads": 2
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_settings.update(data)
        except Exception:
            pass
    return default_settings

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print("Failed to save settings:", e)

def apply_cookie_and_bypass_opts(ydl_opts, cookie_source="Auto Detect Browser"):
    """
    Configures yt-dlp options with anti-bot bypasses, user-agents, client fallbacks,
    and browser cookie extraction to download YouTube Premium, member-only, and private content.
    """
    ydl_opts['nocheckcertificate'] = True
    ydl_opts['geo_bypass'] = True
    ydl_opts['user_agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    ydl_opts['extractor_args'] = {
        'youtube': {
            'player_client': ['android', 'ios', 'web', 'mweb', 'tv'],
            'player_skip': ['configs']
        }
    }

    cookies_path = resource_path('cookies.txt')
    if os.path.exists(cookies_path) and os.path.getsize(cookies_path) > 0:
        ydl_opts['cookiefile'] = cookies_path
        return ydl_opts

    if cookie_source == "None / Public Only":
        return ydl_opts

    browser_map = {
        "Chrome": ["chrome"],
        "Edge": ["edge"],
        "Firefox": ["firefox"],
        "Brave": ["brave"],
        "Opera": ["opera"],
        "Vivaldi": ["vivaldi"],
        "Auto Detect Browser": ["chrome", "edge", "firefox", "brave", "opera", "vivaldi"]
    }

    browsers_to_try = browser_map.get(cookie_source, ["chrome", "edge", "firefox", "brave", "opera", "vivaldi"])

    for browser in browsers_to_try:
        try:
            test_opts = dict(ydl_opts)
            test_opts['cookiesfrombrowser'] = (browser,)
            test_opts['quiet'] = True
            with yt_dlp.YoutubeDL(test_opts) as ydl:
                pass
            ydl_opts['cookiesfrombrowser'] = (browser,)
            break
        except Exception:
            continue

    return ydl_opts

def is_valid_url(query):
    """Check if input is a web URL from any source or a search keyword."""
    query = query.strip()
    if re.match(r'^(https?://|www\.)', query, re.IGNORECASE):
        return True
    if "." in query.split("/")[0] and not " " in query:
        return True
    return False

class DownloadPausedException(Exception):
    """Exception raised to pause download gracefully preserving the .part file."""
    pass


# ==========================================
# AI SEARCH & MULTI-PLATFORM DISCOVERY ENGINE
# ==========================================
class AISearchEngine:
    """
    Intelligent AI Search and Browsing Engine for Universal Video Discovery.
    Supports YouTube, Anime (Crunchyroll / Funimation / MAL with Studio names),
    Netflix, Amazon Prime Video, Disney+, Hulu, and Universal Web.
    """

    @staticmethod
    def search_youtube(query, max_results=8, cookie_source="None / Public Only"):
        results = []
        try:
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                res = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            
            for item in res.get("entries", []):
                duration = item.get("duration")
                dur_str = ""
                if duration:
                    m, s = divmod(int(duration), 60)
                    h, m = divmod(m, 60)
                    dur_str = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
                
                channel_name = item.get("uploader") or item.get("channel") or "YouTube Creator"
                video_url = item.get("url") or item.get("webpage_url") or f"https://www.youtube.com/watch?v={item.get('id')}"
                
                thumb = item.get("thumbnail")
                if not thumb and item.get("thumbnails"):
                    thumb = item.get("thumbnails")[-1].get("url")

                results.append({
                    "platform": "YouTube",
                    "title": item.get("title", "Untitled Video"),
                    "channel_or_studio": channel_name,
                    "channel_type": "Channel",
                    "url": video_url,
                    "thumbnail": thumb or "",
                    "duration": dur_str,
                    "views": item.get("view_count", 0),
                    "score": None,
                    "year": None,
                    "episodes": None,
                    "genres": ["Video"],
                    "description": item.get("description", "")[:180] if item.get("description") else "",
                    "downloadable": True,
                    "platform_url": video_url
                })
        except Exception as e:
            print("YouTube search error:", e)
        return results

    @staticmethod
    def search_anime(query, max_results=6):
        results = []
        try:
            gql_query = '''
            query ($search: String, $perPage: Int) {
              Page(page: 1, perPage: $perPage) {
                media(search: $search, type: ANIME) {
                  id
                  title { romaji english native }
                  studios(isMain: true) { nodes { name } }
                  episodes
                  averageScore
                  genres
                  seasonYear
                  description(asHtml: false)
                  coverImage { medium large }
                  siteUrl
                }
              }
            }
            '''
            r = requests.post(
                'https://graphql.anilist.co',
                json={'query': gql_query, 'variables': {'search': query, 'perPage': max_results}},
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'},
                verify=False,
                timeout=8
            )
            if r.status_code == 200:
                data = r.json()
                for m in data.get('data', {}).get('Page', {}).get('media', []):
                    studios = [s['name'] for s in m.get('studios', {}).get('nodes', [])]
                    studio_name = ", ".join(studios) if studios else "Unknown Studio"
                    
                    title_eng = m['title'].get('english')
                    title_rom = m['title'].get('romaji')
                    display_title = title_eng if title_eng else title_rom
                    
                    score_val = m.get('averageScore')
                    score_str = f"★ {score_val/10:.1f}/10" if score_val else "N/A"
                    
                    cover = m.get('coverImage', {}).get('large') or m.get('coverImage', {}).get('medium')
                    desc = m.get('description', '') or ''
                    desc = re.sub(r'<[^>]+>', '', desc).strip()[:200]
                    
                    crunchyroll_url = f"https://www.crunchyroll.com/search?q={urllib.parse.quote(display_title)}"
                    
                    results.append({
                        "platform": "Crunchyroll / Anime",
                        "title": display_title,
                        "channel_or_studio": studio_name,
                        "channel_type": "Animation Studio",
                        "url": crunchyroll_url,
                        "thumbnail": cover or "",
                        "duration": None,
                        "views": None,
                        "score": score_str,
                        "year": m.get('seasonYear'),
                        "episodes": f"{m.get('episodes')} Episodes" if m.get('episodes') else "Anime Series",
                        "genres": m.get('genres', [])[:3],
                        "description": desc,
                        "downloadable": False,
                        "platform_url": crunchyroll_url,
                        "search_query": f"{display_title} anime"
                    })
        except Exception as e:
            print("Anime search error:", e)
        return results

    @staticmethod
    def search_shows_and_movies(query, platform_filter=None, max_results=6):
        results = []
        try:
            url = f"https://api.tvmaze.com/search/shows?q={urllib.parse.quote(query)}"
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, verify=False, timeout=8)
            if r.status_code == 200:
                data = r.json()
                for item in data[:max_results]:
                    show = item.get('show', {})
                    network = show.get('webChannel') or show.get('network') or {}
                    network_name = network.get('name') if isinstance(network, dict) else "Original Studio / Network"
                    
                    platform = network_name
                    net_lower = network_name.lower()
                    if "netflix" in net_lower:
                        platform = "Netflix"
                    elif "prime" in net_lower or "amazon" in net_lower:
                        platform = "Prime Video"
                    elif "hulu" in net_lower:
                        platform = "Hulu"
                    elif "disney" in net_lower:
                        platform = "Disney+"
                    elif "apple" in net_lower:
                        platform = "Apple TV+"
                    elif "hbo" in net_lower:
                        platform = "HBO Max"
                    
                    if platform_filter:
                        pf_lower = platform_filter.lower()
                        if "netflix" in pf_lower and platform != "Netflix":
                            continue
                        elif "prime" in pf_lower and platform != "Prime Video":
                            continue

                    rating = show.get('rating', {}).get('average')
                    rating_str = f"★ {rating}/10" if rating else "N/A"
                    
                    premiered = show.get('premiered', '')
                    year = premiered.split('-')[0] if premiered else None
                    
                    summary = show.get('summary', '') or ''
                    summary = re.sub(r'<[^>]+>', '', summary).strip()[:200]
                    
                    img = show.get('image', {}) or {}
                    cover = img.get('medium') or img.get('original')
                    
                    title = show.get('name', 'Untitled Show')
                    
                    if platform == "Netflix":
                        plat_url = f"https://www.netflix.com/search?q={urllib.parse.quote(title)}"
                    elif platform == "Prime Video":
                        plat_url = f"https://www.amazon.com/s?k={urllib.parse.quote(title)}"
                    else:
                        plat_url = show.get('url', f"https://www.google.com/search?q={urllib.parse.quote(title + ' watch online')}")

                    results.append({
                        "platform": platform,
                        "title": title,
                        "channel_or_studio": network_name,
                        "channel_type": "Studio / Network",
                        "url": plat_url,
                        "thumbnail": cover or "",
                        "duration": None,
                        "views": None,
                        "score": rating_str,
                        "year": year,
                        "episodes": f"Status: {show.get('status', 'Released')}",
                        "genres": show.get('genres', [])[:3],
                        "description": summary,
                        "downloadable": False,
                        "platform_url": plat_url,
                        "search_query": title
                    })
        except Exception as e:
            print("Shows search error:", e)
        return results

    @classmethod
    def ai_smart_search(cls, query, platform="All", max_total=16):
        query = query.strip()
        if not query:
            return []
        
        results = []
        p_lower = platform.lower()
        
        if "youtube" in p_lower:
            return cls.search_youtube(query, max_results=max_total)
            
        elif "anime" in p_lower or "crunchyroll" in p_lower:
            anime_res = cls.search_anime(query, max_results=8)
            yt_trailers = cls.search_youtube(f"{query} anime trailer episode", max_results=4)
            return anime_res + yt_trailers
            
        elif "netflix" in p_lower:
            net_res = cls.search_shows_and_movies(query, platform_filter="Netflix", max_results=8)
            if not net_res:
                net_res = cls.search_shows_and_movies(query, max_results=6)
            yt_trailers = cls.search_youtube(f"{query} netflix official trailer", max_results=4)
            return net_res + yt_trailers
            
        elif "prime" in p_lower:
            prime_res = cls.search_shows_and_movies(query, platform_filter="Prime Video", max_results=8)
            if not prime_res:
                prime_res = cls.search_shows_and_movies(query, max_results=6)
            yt_trailers = cls.search_youtube(f"{query} prime video trailer", max_results=4)
            return prime_res + yt_trailers
        
        # Universal Smart AI Search across all sources
        is_anime_intent = any(k in query.lower() for k in ["anime", "studio", "mappa", "ufotable", "toei", "bones", "madhouse", "cloverworks", "wit", "shonen", "manga", "jujutsu", "demon slayer", "naruto", "attack on titan", "one piece", "bleach"])
        
        anime_items = cls.search_anime(query, max_results=4)
        tv_items = cls.search_shows_and_movies(query, max_results=4)
        yt_items = cls.search_youtube(query, max_results=6)
        
        if is_anime_intent and anime_items:
            results.extend(anime_items)
            results.extend(yt_items)
            results.extend(tv_items)
        else:
            results.extend(yt_items)
            results.extend(anime_items)
            results.extend(tv_items)
            
        return results[:max_total]


# ==========================================
# DOWNLOAD QUEUE ITEM & MANAGER
# ==========================================
class QueueItem:
    """Represents a single downloadable item in the queue with Pause, Resume, and Retry state."""
    def __init__(self, url, title=None, mode="video", quality="Best Available (Max 4K/8K)",
                 cookie_source="Auto Detect Browser", subtitles=False, save_folder="",
                 channel_or_studio="", platform="Web"):
        self.id = str(uuid.uuid4())
        self.url = url
        self.title = title or url
        self.mode = mode
        self.quality = quality
        self.cookie_source = cookie_source
        self.subtitles = subtitles
        self.save_folder = save_folder or os.path.join(os.path.expanduser("~"), "Downloads")
        self.channel_or_studio = channel_or_studio or platform
        self.platform = platform
        self.thumbnail_url = ""
        self.final_filepath = ""
        
        # Lifecycle States: QUEUED, DOWNLOADING, PAUSED, COMPLETED, FAILED, CANCELLED
        self.status = "QUEUED"
        self.progress = 0.0
        self.downloaded_bytes = 0
        self.total_bytes = 0
        self.speed_str = "-- MB/s"
        self.eta_str = "--:--"
        self.error_message = ""
        self.last_progress_time = 0
        self.last_downloaded_bytes = 0
        
        self.is_paused = False
        self.is_cancelled = False
        self.thread = None
        self.card_widget = None

    def pause(self):
        if self.status == "DOWNLOADING":
            self.is_paused = True
            self.status = "PAUSED"

    def resume(self):
        if self.status in ["PAUSED", "FAILED", "CANCELLED"]:
            self.is_paused = False
            self.is_cancelled = False
            self.error_message = ""
            self.status = "QUEUED"

    def retry(self):
        self.is_paused = False
        self.is_cancelled = False
        self.error_message = ""
        self.status = "QUEUED"

    def cancel(self):
        self.is_cancelled = True
        self.status = "CANCELLED"


# ==========================================
# MAIN APPLICATION WINDOW
# ==========================================
class DownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.settings = load_settings()
        ctk.set_appearance_mode(self.settings.get("theme", "Dark"))

        self.title(f"{APP_NAME} {APP_VERSION} - Queue Manager & AI Multi-Platform Discovery")
        self.geometry("1240x820")
        self.minsize(1020, 720)

        # Set App Window Icon
        icon_path = resource_path("Assets/icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # State Variables
        self.save_folder = self.settings.get("save_folder", os.path.join(os.path.expanduser("~"), "Downloads"))
        self.current_video_info = None
        self.search_results = []
        self.history_items = []
        
        # Single Downloader State
        self.is_single_downloading = False
        self.single_cancel_requested = False
        self.single_download_thread = None
        self.single_last_progress_time = 0
        self.single_last_downloaded_bytes = 0

        # Queue Engine State
        self.queue_items = []
        self.max_concurrent = self.settings.get("max_concurrent_downloads", 2)
        self.is_queue_active = True
        self.queue_lock = threading.Lock()
        self.thumbnail_cache = {}

        self.load_history()

        # Build Main UI Layout
        self.setup_ui()

        # Start Queue Background Dispatcher
        self.queue_dispatcher_running = True
        self.queue_dispatcher_thread = threading.Thread(target=self.queue_dispatcher_loop, daemon=True)
        self.queue_dispatcher_thread.start()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Top Header Bar ---
        header_frame = ctk.CTkFrame(self, fg_color="#14161D", height=65, corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        # Logo / Branding
        brand_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        brand_frame.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        icon_png_path = resource_path("Assets/icon.png")
        if os.path.exists(icon_png_path):
            try:
                img_pil = Image.open(icon_png_path)
                header_icon = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=(32, 32))
                icon_label = ctk.CTkLabel(brand_frame, image=header_icon, text="")
                icon_label.pack(side="left", padx=(0, 10))
            except Exception:
                title_icon = ctk.CTkLabel(brand_frame, text="▶", font=ctk.CTkFont(size=26, weight="bold"), text_color=COLOR_ACCENT)
                title_icon.pack(side="left", padx=(0, 8))
        else:
            title_icon = ctk.CTkLabel(brand_frame, text="▶", font=ctk.CTkFont(size=26, weight="bold"), text_color=COLOR_ACCENT)
            title_icon.pack(side="left", padx=(0, 8))

        title_label = ctk.CTkLabel(
            brand_frame,
            text="UNIVERSAL",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=COLOR_TEXT_MAIN
        )
        title_label.pack(side="left")

        sub_title = ctk.CTkLabel(
            brand_frame,
            text="DOWNLOADER PRO",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLOR_ACCENT
        )
        sub_title.pack(side="left", padx=(6, 0))

        v_badge = ctk.CTkLabel(
            brand_frame,
            text=f" {APP_VERSION} ",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#FFFFFF",
            fg_color="#3A3F4E",
            corner_radius=6
        )
        v_badge.pack(side="left", padx=(10, 0))

        # Header Right Controls & Quick Queue Indicator
        header_controls = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_controls.grid(row=0, column=2, padx=20, pady=10, sticky="e")

        self.queue_badge_lbl = ctk.CTkLabel(
            header_controls,
            text="📑 Queue: 0 active",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
        self.queue_badge_lbl.pack(side="left", padx=12)

        self.theme_switch = ctk.CTkSwitch(
            header_controls,
            text="Dark Mode",
            command=self.toggle_theme,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        if self.settings.get("theme", "Dark") == "Dark":
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()
        self.theme_switch.pack(side="left", padx=10)

        open_folder_btn = ctk.CTkButton(
            header_controls,
            text="📁 Downloads",
            fg_color="#2B2F3A",
            hover_color="#3A3F4E",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.open_save_folder,
            height=34
        )
        open_folder_btn.pack(side="left", padx=5)

        # --- Main Navigation Tabs ---
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=COLOR_BG,
            segmented_button_fg_color="#181A20",
            segmented_button_selected_color=COLOR_ACCENT,
            segmented_button_selected_hover_color=COLOR_ACCENT_HOVER,
            segmented_button_unselected_color="#232730",
            segmented_button_unselected_hover_color="#2E3340"
        )
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=15, pady=(5, 15))

        self.tab_downloader = self.tabview.add(" 📥 Single Downloader ")
        self.tab_queue = self.tabview.add(" 📑 Download Queue ")
        self.tab_ai_search = self.tabview.add(" 🤖 AI Video Discovery ")
        self.tab_history = self.tabview.add(" 📜 Download History ")
        self.tab_settings = self.tabview.add(" ⚙ Settings & Updates ")

        # Build Individual Tabs
        self.build_downloader_tab()
        self.build_queue_tab()
        self.build_ai_search_tab()
        self.build_history_tab()
        self.build_settings_tab()

    # ==========================================
    # TAB 1: SINGLE DOWNLOADER
    # ==========================================
    def build_downloader_tab(self):
        tab = self.tab_downloader
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=2)
        tab.grid_rowconfigure(1, weight=1)

        # URL Input Bar
        url_card = ctk.CTkFrame(tab, fg_color=COLOR_CARD, corner_radius=12)
        url_card.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 10))
        url_card.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            url_card,
            placeholder_text="Paste ANY link (YouTube, TikTok, Anime, Twitch, Netflix, Prime, Twitter, Vimeo...) or search...",
            font=ctk.CTkFont(size=13),
            height=42,
            border_width=1,
            border_color="#2E3340"
        )
        self.url_entry.grid(row=0, column=0, padx=(15, 10), pady=12, sticky="ew")
        self.url_entry.bind("<Return>", lambda e: self.start_fetch_info_thread())

        paste_btn = ctk.CTkButton(
            url_card,
            text="📋 Paste",
            width=85,
            height=40,
            fg_color="#2B2F3A",
            hover_color="#3A3F4E",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.paste_clipboard
        )
        paste_btn.grid(row=0, column=1, padx=(0, 8), pady=12)

        fetch_btn = ctk.CTkButton(
            url_card,
            text="🔍 Fetch Info",
            width=100,
            height=40,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.start_fetch_info_thread
        )
        fetch_btn.grid(row=0, column=2, padx=(0, 15), pady=12)

        # Left Column: Video Preview Card
        self.preview_card = ctk.CTkFrame(tab, fg_color=COLOR_CARD, corner_radius=12)
        self.preview_card.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)
        self.preview_card.grid_columnconfigure(0, weight=1)
        self.preview_card.grid_rowconfigure(0, weight=1)

        self.thumbnail_label = ctk.CTkLabel(
            self.preview_card,
            text="No Video Selected\n\nPaste any video URL or search above to preview metadata.\nSupports YouTube Premium, Private Links, Anime & 1000+ Platforms!",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
            corner_radius=8,
            fg_color="#12131A"
        )
        self.thumbnail_label.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

        self.info_frame = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        self.info_frame.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="ew")

        self.video_title_label = ctk.CTkLabel(
            self.info_frame,
            text="Ready to download",
            font=ctk.CTkFont(size=15, weight="bold"),
            wraplength=520,
            justify="left"
        )
        self.video_title_label.pack(anchor="w", pady=(0, 4))

        self.video_details_label = ctk.CTkLabel(
            self.info_frame,
            text="Channel/Studio: -- | Duration: -- | Views: --",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_MUTED,
            justify="left"
        )
        self.video_details_label.pack(anchor="w")

        # Right Column: Download & Queue Options Card
        options_card = ctk.CTkFrame(tab, fg_color=COLOR_CARD, corner_radius=12)
        options_card.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=5)
        options_card.grid_columnconfigure(0, weight=1)

        opts_header = ctk.CTkLabel(
            options_card,
            text="⚙ Download & Quality Settings",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        opts_header.pack(anchor="w", padx=15, pady=(12, 6))

        # Format Mode
        self.format_mode_var = ctk.StringVar(value="video")
        mode_frame = ctk.CTkFrame(options_card, fg_color="#12131A", corner_radius=8)
        mode_frame.pack(fill="x", padx=15, pady=4)

        self.video_radio = ctk.CTkRadioButton(
            mode_frame,
            text="🎬 Video (MP4)",
            variable=self.format_mode_var,
            value="video",
            command=self.update_quality_options,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLOR_ACCENT
        )
        self.video_radio.pack(side="left", padx=15, pady=10)

        self.audio_radio = ctk.CTkRadioButton(
            mode_frame,
            text="🎵 Audio Only (MP3)",
            variable=self.format_mode_var,
            value="audio",
            command=self.update_quality_options,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLOR_ACCENT
        )
        self.audio_radio.pack(side="left", padx=15, pady=10)

        # Quality Selector
        q_label = ctk.CTkLabel(options_card, text="Select Quality / Format:", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_MUTED)
        q_label.pack(anchor="w", padx=15, pady=(8, 2))

        self.quality_var = ctk.StringVar(value=self.settings.get("default_quality", "Best Available (Max 4K/8K)"))
        self.quality_combo = ctk.CTkComboBox(
            options_card,
            values=["Best Available (Max 4K/8K)", "4K (2160p)", "1440p (2K)", "1080p (Full HD)", "720p (HD)", "480p", "360p"],
            variable=self.quality_var,
            font=ctk.CTkFont(size=12),
            dropdown_font=ctk.CTkFont(size=12),
            height=34
        )
        self.quality_combo.pack(fill="x", padx=15, pady=(0, 6))

        # Cookie / Browser Auth Selector
        cookie_label = ctk.CTkLabel(options_card, text="🔓 Premium / Browser Auth Cookies:", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_MUTED)
        cookie_label.pack(anchor="w", padx=15, pady=(6, 2))

        self.cookie_var = ctk.StringVar(value=self.settings.get("cookie_source", "Auto Detect Browser"))
        self.cookie_combo = ctk.CTkComboBox(
            options_card,
            values=["Auto Detect Browser", "Chrome", "Edge", "Firefox", "Brave", "Opera", "Vivaldi", "Cookies.txt File", "None / Public Only"],
            variable=self.cookie_var,
            command=self.on_cookie_setting_change,
            font=ctk.CTkFont(size=12),
            dropdown_font=ctk.CTkFont(size=12),
            height=34
        )
        self.cookie_combo.pack(fill="x", padx=15, pady=(0, 6))

        # Subtitles Checkbox
        self.subtitles_var = ctk.BooleanVar(value=self.settings.get("download_subtitles", False))
        self.subtitles_chk = ctk.CTkCheckBox(
            options_card,
            text="Download Subtitles / Captions (.srt)",
            variable=self.subtitles_var,
            font=ctk.CTkFont(size=12),
            fg_color=COLOR_ACCENT
        )
        self.subtitles_chk.pack(anchor="w", padx=15, pady=4)

        # Save Folder Selector
        folder_label = ctk.CTkLabel(options_card, text="Save Directory:", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_MUTED)
        folder_label.pack(anchor="w", padx=15, pady=(8, 2))

        folder_box = ctk.CTkFrame(options_card, fg_color="transparent")
        folder_box.pack(fill="x", padx=15, pady=(0, 8))
        folder_box.grid_columnconfigure(0, weight=1)

        self.folder_entry = ctk.CTkEntry(folder_box, font=ctk.CTkFont(size=11), height=34)
        self.folder_entry.insert(0, self.save_folder)
        self.folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        browse_btn = ctk.CTkButton(folder_box, text="📁 Browse", width=75, height=34, fg_color="#2B2F3A", hover_color="#3A3F4E", command=self.choose_save_folder)
        browse_btn.grid(row=0, column=1)

        # Status Box
        self.progress_frame = ctk.CTkFrame(options_card, fg_color="#12131A", corner_radius=10)
        self.progress_frame.pack(fill="x", padx=15, pady=6)

        self.status_label = ctk.CTkLabel(self.progress_frame, text="Status: Ready", font=ctk.CTkFont(size=12, weight="bold"), anchor="w")
        self.status_label.pack(fill="x", padx=12, pady=(6, 2))

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, progress_color=COLOR_ACCENT, height=10)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=12, pady=2)

        self.details_label = ctk.CTkLabel(self.progress_frame, text="0.0% | -- MB/s | ETA: --:--", font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED, anchor="w")
        self.details_label.pack(fill="x", padx=12, pady=(2, 6))

        # Main Download & Add to Queue Buttons
        actions_frame = ctk.CTkFrame(options_card, fg_color="transparent")
        actions_frame.pack(fill="x", padx=15, pady=(4, 10))
        actions_frame.grid_columnconfigure(0, weight=2)
        actions_frame.grid_columnconfigure(1, weight=2)
        actions_frame.grid_columnconfigure(2, weight=1)

        self.download_btn = ctk.CTkButton(
            actions_frame,
            text="⬇ START NOW",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            height=42,
            corner_radius=8,
            command=self.start_single_download_thread
        )
        self.download_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.add_queue_btn = ctk.CTkButton(
            actions_frame,
            text="➕ ADD TO QUEUE",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            height=42,
            corner_radius=8,
            command=self.add_current_to_queue
        )
        self.add_queue_btn.grid(row=0, column=1, sticky="ew", padx=(0, 4))

        self.cancel_btn = ctk.CTkButton(
            actions_frame,
            text="✖ Stop",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#3A2025",
            hover_color="#5A252D",
            text_color="#FF6B6B",
            height=42,
            corner_radius=8,
            state="disabled",
            command=self.cancel_single_download
        )
        self.cancel_btn.grid(row=0, column=2, sticky="ew")

    def update_quality_options(self):
        mode = self.format_mode_var.get()
        if mode == "audio":
            self.quality_combo.configure(values=["320 kbps (Best)", "256 kbps", "192 kbps", "128 kbps", "M4A Format", "WAV Format"])
            self.quality_var.set("320 kbps (Best)")
        else:
            self.quality_combo.configure(values=["Best Available (Max 4K/8K)", "4K (2160p)", "1440p (2K)", "1080p (Full HD)", "720p (HD)", "480p", "360p"])
            self.quality_var.set("Best Available (Max 4K/8K)")

    def on_cookie_setting_change(self, choice):
        self.settings["cookie_source"] = choice
        save_settings(self.settings)

    def paste_clipboard(self):
        try:
            text = self.clipboard_get().strip()
            if text:
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, text)
                self.start_fetch_info_thread()
        except Exception:
            pass

    def choose_save_folder(self):
        folder = filedialog.askdirectory(initialdir=self.save_folder)
        if folder:
            self.save_folder = folder
            self.folder_entry.delete(0, tk.END)
            self.folder_entry.insert(0, folder)
            self.settings["save_folder"] = folder
            save_settings(self.settings)

    def open_save_folder(self):
        folder = self.folder_entry.get().strip() or self.save_folder
        if not os.path.exists(folder):
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception:
                pass
        if os.path.exists(folder):
            if sys.platform == "win32":
                os.startfile(folder)
            else:
                subprocess.Popen(["xdg-open", folder])

    # Metadata Fetching
    def start_fetch_info_thread(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Required", "Please enter or paste a video URL or search query.")
            return

        self.status_label.configure(text="Status: Extracting video information...")
        self.thumbnail_label.configure(text="Loading video preview...", image=None)
        threading.Thread(target=self.fetch_info_worker, args=(url,), daemon=True).start()

    def fetch_info_worker(self, query):
        try:
            cookie_choice = self.cookie_var.get()
            target_url = query if is_valid_url(query) else f"ytsearch1:{query}"
            if is_valid_url(query) and not query.startswith(('http://', 'https://')):
                target_url = f"https://{query}"

            ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': False}
            apply_cookie_and_bypass_opts(ydl_opts, cookie_choice)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(target_url, download=False)

            if "entries" in info and info["entries"]:
                info = info["entries"][0]

            self.current_video_info = info
            self.after(0, lambda: self.update_preview_ui(info))
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda: self.handle_fetch_error(err_msg))

    def handle_fetch_error(self, error):
        self.status_label.configure(text="Status: Failed to fetch video info")
        self.thumbnail_label.configure(text=f"Error loading preview:\n{error[:140]}")
        messagebox.showerror("Metadata Error", f"Could not retrieve video information:\n\n{error}")

    def update_preview_ui(self, info):
        title = info.get("title", "Unknown Title")
        uploader = info.get("uploader") or info.get("channel") or info.get("extractor_key") or "Channel / Studio"
        duration_sec = info.get("duration", 0)
        views = info.get("view_count", 0)
        webpage_url = info.get("webpage_url", "")

        if webpage_url:
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, webpage_url)

        if duration_sec:
            mins, secs = divmod(int(duration_sec), 60)
            hrs, mins = divmod(mins, 60)
            duration_str = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs else f"{mins:02d}:{secs:02d}"
        else:
            duration_str = "N/A"
            
        views_str = f"{views:,}" if views else "N/A"

        self.video_title_label.configure(text=title)
        self.video_details_label.configure(text=f"Channel/Studio: {uploader}  |  Duration: {duration_str}  |  Views: {views_str}")
        self.status_label.configure(text="Status: Ready to Download or Add to Queue")

        thumbnail_url = info.get("thumbnail")
        if thumbnail_url:
            threading.Thread(target=self.load_thumbnail_image, args=(thumbnail_url,), daemon=True).start()

    def load_thumbnail_image(self, url):
        try:
            resp = requests.get(url, timeout=10, verify=False)
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            img = img.resize((450, 253), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(450, 253))
            self.after(0, lambda: self.thumbnail_label.configure(image=ctk_img, text=""))
        except Exception as e:
            print("Thumbnail load error:", e)

    # Single Download Actions
    def start_single_download_thread(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Missing", "Please enter a valid video URL or keyword.")
            return

        if self.is_single_downloading:
            messagebox.showinfo("In Progress", "A single download is already active.")
            return

        self.is_single_downloading = True
        self.single_cancel_requested = False
        self.download_btn.configure(state="disabled", fg_color="#3A3F4E")
        self.cancel_btn.configure(state="normal", fg_color="#E53935")
        self.progress_bar.set(0)
        self.status_label.configure(text="Status: Starting download...")

        self.single_last_progress_time = time.time()
        self.single_last_downloaded_bytes = 0

        self.single_download_thread = threading.Thread(target=self.single_download_worker, args=(url,), daemon=True)
        self.single_download_thread.start()

    def single_progress_hook(self, d):
        if self.single_cancel_requested:
            raise yt_dlp.utils.DownloadCancelled("Download cancelled by user.")

        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            now = time.time()
            elapsed = now - self.single_last_progress_time
            
            speed_str = "-- MB/s"
            eta_str = "--:--"
            if elapsed > 0.4:
                bytes_diff = downloaded - self.single_last_downloaded_bytes
                speed = bytes_diff / elapsed
                self.single_last_progress_time = now
                self.single_last_downloaded_bytes = downloaded
                speed_str = f"{speed / (1024*1024):.2f} MB/s"
                if total > downloaded and speed > 0:
                    eta_sec = int((total - downloaded) / speed)
                    m, s = divmod(eta_sec, 60)
                    h, m = divmod(m, 60)
                    eta_str = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

            pct = (downloaded / total) if total > 0 else 0
            down_mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            detail_txt = f"{pct*100:.1f}% | {speed_str} | ETA: {eta_str} | ({down_mb:.1f} MB / {total_mb:.1f} MB)"
            self.after(0, lambda: self.update_single_progress(pct, detail_txt, "Downloading..."))
            
        elif d['status'] == 'finished':
            self.after(0, lambda: self.update_single_progress(1.0, "Merging media files...", "Finalizing..."))

    def update_single_progress(self, pct, details, status):
        self.progress_bar.set(pct)
        self.details_label.configure(text=details)
        self.status_label.configure(text=f"Status: {status}")

    def single_download_worker(self, query):
        out_folder = self.folder_entry.get().strip() or self.save_folder
        mode = self.format_mode_var.get()
        quality_choice = self.quality_var.get()
        cookie_choice = self.cookie_var.get()
        subtitles = self.subtitles_var.get()
        ffmpeg_bin = get_ffmpeg_path()

        target_url = query if is_valid_url(query) else f"ytsearch1:{query}"
        if is_valid_url(query) and not query.startswith(('http://', 'https://')):
            target_url = f"https://{query}"

        ydl_opts = {
            'outtmpl': os.path.join(out_folder, '%(title)s.%(ext)s'),
            'progress_hooks': [self.single_progress_hook],
            'ffmpeg_location': ffmpeg_bin,
            'quiet': True,
            'no_warnings': True,
            'continuedl': True,
            'nopart': False
        }

        apply_cookie_and_bypass_opts(ydl_opts, cookie_choice)

        if mode == "audio":
            ydl_opts['format'] = 'bestaudio/best'
            ext = 'mp3'
            if "M4A" in quality_choice: ext = 'm4a'
            elif "WAV" in quality_choice: ext = 'wav'
            bitrate = "320"
            if "256" in quality_choice: bitrate = "256"
            elif "192" in quality_choice: bitrate = "192"
            elif "128" in quality_choice: bitrate = "128"
            ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': ext, 'preferredquality': bitrate}]
        else:
            height_map = {"4K (2160p)": 2160, "1440p (2K)": 1440, "1080p (Full HD)": 1080, "720p (HD)": 720, "480p": 480, "360p": 360}
            if "Best" in quality_choice:
                ydl_opts['format'] = "bestvideo+bestaudio/best"
            else:
                target_h = height_map.get(quality_choice, 1080)
                ydl_opts['format'] = f"bestvideo[height<={target_h}]+bestaudio/best[height<={target_h}]/best"
            ydl_opts['merge_output_format'] = 'mp4'

        if subtitles:
            ydl_opts['writesubtitles'] = True
            ydl_opts['subtitlesformat'] = 'srt'
            ydl_opts['embedsubtitles'] = True

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(target_url, download=True)
                if "entries" in info and info["entries"]:
                    info = info["entries"][0]
            
            title = info.get("title", "Video Download")
            filepath = ydl.prepare_filename(info)
            if mode == "audio":
                filepath = os.path.splitext(filepath)[0] + "." + ext
            elif mode == "video" and not filepath.endswith(".mp4"):
                filepath = os.path.splitext(filepath)[0] + ".mp4"

            self.save_to_history(title, query, filepath, quality_choice)
            self.after(0, lambda: self.handle_single_download_success(title))
        except yt_dlp.utils.DownloadCancelled:
            self.after(0, self.handle_single_download_cancelled)
        except Exception as e:
            err = str(e)
            self.after(0, lambda: self.handle_single_download_error(err))

    def cancel_single_download(self):
        if self.is_single_downloading:
            self.single_cancel_requested = True
            self.status_label.configure(text="Status: Cancelling download...")

    def handle_single_download_success(self, title):
        self.is_single_downloading = False
        self.download_btn.configure(state="normal", fg_color=COLOR_ACCENT)
        self.cancel_btn.configure(state="disabled", fg_color="#3A2025")
        self.progress_bar.set(1.0)
        self.status_label.configure(text="Status: Download Complete! 🎉")
        self.details_label.configure(text=f"Saved: {title[:50]}")
        messagebox.showinfo("Success", f"Download Completed Successfully!\n\n'{title}'")

    def handle_single_download_cancelled(self):
        self.is_single_downloading = False
        self.download_btn.configure(state="normal", fg_color=COLOR_ACCENT)
        self.cancel_btn.configure(state="disabled", fg_color="#3A2025")
        self.progress_bar.set(0)
        self.status_label.configure(text="Status: Download Cancelled")
        self.details_label.configure(text="Cancelled by user.")

    def handle_single_download_error(self, error):
        self.is_single_downloading = False
        self.download_btn.configure(state="normal", fg_color=COLOR_ACCENT)
        self.cancel_btn.configure(state="disabled", fg_color="#3A2025")
        self.status_label.configure(text="Status: Download Failed")
        self.details_label.configure(text="Error occurred.")
        messagebox.showerror("Download Error", f"An error occurred while downloading:\n\n{error}")

    def add_current_to_queue(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Missing", "Please enter a valid video URL or search query.")
            return

        title = self.video_title_label.cget("text")
        if title == "Ready to download":
            title = url

        mode = self.format_mode_var.get()
        quality = self.quality_var.get()
        cookie = self.cookie_var.get()
        subs = self.subtitles_var.get()
        folder = self.folder_entry.get().strip() or self.save_folder

        item = QueueItem(
            url=url,
            title=title,
            mode=mode,
            quality=quality,
            cookie_source=cookie,
            subtitles=subs,
            save_folder=folder,
            channel_or_studio="Single Downloader",
            platform="Web"
        )
        
        self.add_queue_item(item)
        messagebox.showinfo("Queue", f"Added to Download Queue:\n\n'{title[:60]}'")
        self.tabview.set(" 📑 Download Queue ")


    # ==========================================
    # TAB 2: DOWNLOAD QUEUE MANAGER
    # ==========================================
    def build_queue_tab(self):
        tab = self.tab_queue
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # Queue Toolbar
        toolbar = ctk.CTkFrame(tab, fg_color=COLOR_CARD, corner_radius=12)
        toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        toolbar.grid_columnconfigure(5, weight=1)

        batch_btn = ctk.CTkButton(
            toolbar,
            text="➕ Add URL(s)",
            fg_color="#1E3A8A",
            hover_color="#1D4ED8",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            command=self.open_batch_add_dialog
        )
        batch_btn.grid(row=0, column=0, padx=(12, 6), pady=10)

        resume_all_btn = ctk.CTkButton(
            toolbar,
            text="▶ Resume All",
            fg_color=COLOR_SUCCESS,
            hover_color="#218838",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            command=self.resume_all_queue
        )
        resume_all_btn.grid(row=0, column=1, padx=4, pady=10)

        pause_all_btn = ctk.CTkButton(
            toolbar,
            text="⏸ Pause All",
            fg_color="#D97706",
            hover_color="#B45309",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            command=self.pause_all_queue
        )
        pause_all_btn.grid(row=0, column=2, padx=4, pady=10)

        retry_all_btn = ctk.CTkButton(
            toolbar,
            text="🔄 Retry Failed",
            fg_color="#4B5563",
            hover_color="#374151",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            command=self.retry_failed_queue
        )
        retry_all_btn.grid(row=0, column=3, padx=4, pady=10)

        clear_done_btn = ctk.CTkButton(
            toolbar,
            text="🧹 Clear Completed",
            fg_color="#2B2F3A",
            hover_color="#3A3F4E",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            command=self.clear_completed_queue
        )
        clear_done_btn.grid(row=0, column=4, padx=4, pady=10)

        # Concurrency selector
        conc_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        conc_frame.grid(row=0, column=6, padx=(0, 15), pady=10, sticky="e")

        conc_lbl = ctk.CTkLabel(conc_frame, text="Parallel:", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_MUTED)
        conc_lbl.pack(side="left", padx=(0, 6))

        self.conc_combo = ctk.CTkComboBox(
            conc_frame,
            values=["1 Download", "2 Downloads", "3 Downloads"],
            width=125,
            height=34,
            command=self.on_concurrency_change
        )
        self.conc_combo.set(f"{self.max_concurrent} Downloads")
        self.conc_combo.pack(side="left")

        # Scrollable Queue Items Frame
        self.queue_scroll = ctk.CTkScrollableFrame(
            tab,
            fg_color=COLOR_BG,
            corner_radius=10,
            label_text="Active & Queued Downloads",
            label_font=ctk.CTkFont(size=14, weight="bold")
        )
        self.queue_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.queue_scroll.grid_columnconfigure(0, weight=1)

        self.queue_empty_label = ctk.CTkLabel(
            self.queue_scroll,
            text="No items in download queue.\n\nAdd videos from Single Downloader, AI Video Discovery, or click '➕ Add URL(s)' above.",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_MUTED
        )
        self.queue_empty_label.pack(pady=60)

    def on_concurrency_change(self, choice):
        try:
            val = int(choice.split()[0])
            self.max_concurrent = val
            self.settings["max_concurrent_downloads"] = val
            save_settings(self.settings)
        except Exception:
            pass

    def add_queue_item(self, item):
        with self.queue_lock:
            self.queue_items.append(item)
        self.render_queue_list()

    def add_batch_urls(self, urls_text, mode, quality):
        lines = [line.strip() for line in urls_text.splitlines() if line.strip()]
        if not lines:
            return
        
        folder = self.folder_entry.get().strip() or self.save_folder
        cookie = self.cookie_var.get()
        subs = self.subtitles_var.get()

        added_count = 0
        for url in lines:
            item = QueueItem(
                url=url,
                title=url,
                mode=mode,
                quality=quality,
                cookie_source=cookie,
                subtitles=subs,
                save_folder=folder,
                channel_or_studio="Batch Import",
                platform="Web"
            )
            with self.queue_lock:
                self.queue_items.append(item)
            added_count += 1

        self.render_queue_list()
        messagebox.showinfo("Queue", f"Added {added_count} items to the download queue!")

    def open_batch_add_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("➕ Batch Add URLs to Queue")
        dialog.geometry("600x460")
        dialog.minsize(500, 380)
        dialog.transient(self)
        dialog.grab_set()

        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        lbl = ctk.CTkLabel(dialog, text="Paste Video URLs (One per line):", font=ctk.CTkFont(size=14, weight="bold"))
        lbl.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")

        txt_box = ctk.CTkTextbox(dialog, font=ctk.CTkFont(size=12))
        txt_box.grid(row=1, column=0, padx=20, pady=5, sticky="nsew")

        # Format selector in modal
        opt_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        opt_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        mode_var = ctk.StringVar(value="video")
        r_vid = ctk.CTkRadioButton(opt_frame, text="🎬 MP4 Video", variable=mode_var, value="video")
        r_vid.pack(side="left", padx=(0, 15))
        r_aud = ctk.CTkRadioButton(opt_frame, text="🎵 MP3 Audio", variable=mode_var, value="audio")
        r_aud.pack(side="left", padx=(0, 15))

        q_var = ctk.StringVar(value="Best Available (Max 4K/8K)")
        q_combo = ctk.CTkComboBox(opt_frame, values=["Best Available (Max 4K/8K)", "1080p (Full HD)", "720p (HD)", "320 kbps (Best)"], variable=q_var, width=180)
        q_combo.pack(side="right")

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=20, pady=(5, 15), sticky="ew")

        def on_add():
            content = txt_box.get("1.0", tk.END).strip()
            if content:
                self.add_batch_urls(content, mode_var.get(), q_var.get())
                dialog.destroy()
            else:
                messagebox.showwarning("Input Missing", "Please paste at least one URL.")

        add_btn = ctk.CTkButton(btn_frame, text="➕ Add All to Queue", fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, font=ctk.CTkFont(size=13, weight="bold"), height=38, command=on_add)
        add_btn.pack(side="right", padx=(10, 0))

        cancel_d_btn = ctk.CTkButton(btn_frame, text="Cancel", fg_color="#2B2F3A", hover_color="#3A3F4E", height=38, command=dialog.destroy)
        cancel_d_btn.pack(side="right")

    def render_queue_list(self):
        for child in self.queue_scroll.winfo_children():
            child.destroy()

        with self.queue_lock:
            items = list(self.queue_items)

        if not items:
            self.queue_empty_label = ctk.CTkLabel(
                self.queue_scroll,
                text="No items in download queue.\n\nAdd videos from Single Downloader, AI Video Discovery, or click '➕ Add URL(s)' above.",
                font=ctk.CTkFont(size=13),
                text_color=COLOR_TEXT_MUTED
            )
            self.queue_empty_label.pack(pady=60)
            self.update_header_queue_badge()
            return

        for item in items:
            card = self.create_queue_card(item)
            card.pack(fill="x", padx=5, pady=6)
            item.card_widget = card

        self.update_header_queue_badge()

    def create_queue_card(self, item):
        card = ctk.CTkFrame(self.queue_scroll, fg_color=COLOR_CARD, corner_radius=10)
        card.grid_columnconfigure(1, weight=1)

        # Left Thumbnail / Platform icon placeholder
        thumb_box = ctk.CTkFrame(card, fg_color="#12131A", width=80, height=60, corner_radius=8)
        thumb_box.grid(row=0, column=0, padx=12, pady=12, sticky="ns")
        thumb_box.pack_propagate(False)

        icon_char = "🎬" if item.mode == "video" else "🎵"
        thumb_lbl = ctk.CTkLabel(thumb_box, text=icon_char, font=ctk.CTkFont(size=24))
        thumb_lbl.pack(expand=True)

        # Center Info
        center_f = ctk.CTkFrame(card, fg_color="transparent")
        center_f.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="ew")

        # Title & Status Row
        title_row = ctk.CTkFrame(center_f, fg_color="transparent")
        title_row.pack(fill="x")
        title_row.grid_columnconfigure(0, weight=1)

        t_lbl = ctk.CTkLabel(
            title_row,
            text=item.title[:65] + ("..." if len(item.title) > 65 else ""),
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        )
        t_lbl.grid(row=0, column=0, sticky="w")

        # Color-coded Status Badge
        badge_color = "#3A3F4E"
        if item.status == "QUEUED": badge_color = "#D97706"
        elif item.status == "DOWNLOADING": badge_color = COLOR_ACCENT
        elif item.status == "PAUSED": badge_color = "#B45309"
        elif item.status == "COMPLETED": badge_color = COLOR_SUCCESS
        elif item.status == "FAILED": badge_color = COLOR_DANGER
        elif item.status == "CANCELLED": badge_color = "#6B7280"

        status_badge = ctk.CTkLabel(
            title_row,
            text=f" {item.status} ",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=badge_color,
            text_color="#FFFFFF",
            corner_radius=6
        )
        status_badge.grid(row=0, column=1, sticky="e", padx=(6, 0))

        # Metadata Row
        meta_txt = f"{item.channel_or_studio}  |  {item.mode.upper()} ({item.quality})"
        meta_lbl = ctk.CTkLabel(center_f, text=meta_txt, font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED, anchor="w")
        meta_lbl.pack(fill="x", pady=(2, 4))

        # Progress Bar
        p_bar = ctk.CTkProgressBar(center_f, progress_color=COLOR_ACCENT, height=8)
        p_bar.set(item.progress)
        p_bar.pack(fill="x", pady=2)

        # Details Row (Speed, ETA, Size)
        det_txt = f"{item.progress*100:.1f}% | {item.speed_str} | ETA: {item.eta_str}"
        if item.status == "FAILED" and item.error_message:
            det_txt = f"Error: {item.error_message[:60]}"
        elif item.status == "COMPLETED":
            det_txt = "Download Finished Successfully ✅"

        det_lbl = ctk.CTkLabel(center_f, text=det_txt, font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED, anchor="w")
        det_lbl.pack(fill="x", pady=(1, 0))

        # Store widgets on item for real-time progress updates without re-rendering entire card
        item.ui_pbar = p_bar
        item.ui_det = det_lbl
        item.ui_badge = status_badge
        item.ui_title = t_lbl

        # Right Action Buttons
        btn_f = ctk.CTkFrame(card, fg_color="transparent")
        btn_f.grid(row=0, column=2, padx=12, pady=10, sticky="e")

        if item.status == "DOWNLOADING":
            pause_btn = ctk.CTkButton(btn_f, text="⏸ Pause", width=70, height=30, fg_color="#D97706", hover_color="#B45309", font=ctk.CTkFont(size=11, weight="bold"), command=lambda it=item: self.pause_queue_item(it))
            pause_btn.pack(side="left", padx=3)
            cancel_btn = ctk.CTkButton(btn_f, text="✖ Stop", width=65, height=30, fg_color="#3A2025", hover_color="#5A252D", text_color="#FF6B6B", font=ctk.CTkFont(size=11, weight="bold"), command=lambda it=item: self.cancel_queue_item(it))
            cancel_btn.pack(side="left", padx=3)

        elif item.status == "PAUSED":
            resume_btn = ctk.CTkButton(btn_f, text="▶ Resume", width=75, height=30, fg_color=COLOR_SUCCESS, hover_color="#218838", font=ctk.CTkFont(size=11, weight="bold"), command=lambda it=item: self.resume_queue_item(it))
            resume_btn.pack(side="left", padx=3)
            del_btn = ctk.CTkButton(btn_f, text="🗑 Delete", width=65, height=30, fg_color="#2B2F3A", hover_color="#3A3F4E", font=ctk.CTkFont(size=11), command=lambda it=item: self.remove_queue_item(it))
            del_btn.pack(side="left", padx=3)

        elif item.status in ["FAILED", "CANCELLED"]:
            retry_btn = ctk.CTkButton(btn_f, text="🔄 Retry", width=70, height=30, fg_color="#1E3A8A", hover_color="#1D4ED8", font=ctk.CTkFont(size=11, weight="bold"), command=lambda it=item: self.retry_queue_item(it))
            retry_btn.pack(side="left", padx=3)
            del_btn = ctk.CTkButton(btn_f, text="🗑 Delete", width=65, height=30, fg_color="#2B2F3A", hover_color="#3A3F4E", font=ctk.CTkFont(size=11), command=lambda it=item: self.remove_queue_item(it))
            del_btn.pack(side="left", padx=3)

        elif item.status == "COMPLETED":
            if item.final_filepath and os.path.exists(item.final_filepath):
                play_btn = ctk.CTkButton(btn_f, text="▶ Play", width=65, height=30, fg_color=COLOR_SUCCESS, hover_color="#218838", font=ctk.CTkFont(size=11, weight="bold"), command=lambda p=item.final_filepath: self.open_file(p))
                play_btn.pack(side="left", padx=3)
            del_btn = ctk.CTkButton(btn_f, text="❌", width=36, height=30, fg_color="#2B2F3A", hover_color="#3A3F4E", command=lambda it=item: self.remove_queue_item(it))
            del_btn.pack(side="left", padx=3)

        else: # QUEUED
            del_btn = ctk.CTkButton(btn_f, text="❌ Remove", width=75, height=30, fg_color="#3A2025", hover_color="#5A252D", text_color="#FF6B6B", font=ctk.CTkFont(size=11), command=lambda it=item: self.remove_queue_item(it))
            del_btn.pack(side="left", padx=3)

        return card

    def pause_queue_item(self, item):
        item.pause()
        self.render_queue_list()

    def resume_queue_item(self, item):
        item.resume()
        self.render_queue_list()

    def retry_queue_item(self, item):
        item.retry()
        self.render_queue_list()

    def cancel_queue_item(self, item):
        item.cancel()
        self.render_queue_list()

    def remove_queue_item(self, item):
        if item.status == "DOWNLOADING":
            item.cancel()
        with self.queue_lock:
            if item in self.queue_items:
                self.queue_items.remove(item)
        self.render_queue_list()

    def pause_all_queue(self):
        with self.queue_lock:
            for item in self.queue_items:
                if item.status in ["DOWNLOADING", "QUEUED"]:
                    item.pause()
        self.render_queue_list()

    def resume_all_queue(self):
        with self.queue_lock:
            for item in self.queue_items:
                if item.status in ["PAUSED", "FAILED"]:
                    item.resume()
        self.render_queue_list()

    def retry_failed_queue(self):
        with self.queue_lock:
            for item in self.queue_items:
                if item.status in ["FAILED", "CANCELLED"]:
                    item.retry()
        self.render_queue_list()

    def clear_completed_queue(self):
        with self.queue_lock:
            self.queue_items = [it for it in self.queue_items if it.status != "COMPLETED"]
        self.render_queue_list()

    def update_header_queue_badge(self):
        active_count = sum(1 for it in self.queue_items if it.status == "DOWNLOADING")
        queued_count = sum(1 for it in self.queue_items if it.status == "QUEUED")
        self.queue_badge_lbl.configure(text=f"📑 Queue: {active_count} active, {queued_count} queued")

    # Queue Worker & Dispatcher Loop
    def queue_dispatcher_loop(self):
        while self.queue_dispatcher_running:
            time.sleep(0.5)
            if not self.is_queue_active:
                continue

            with self.queue_lock:
                active_count = sum(1 for it in self.queue_items if it.status == "DOWNLOADING")
                available_slots = self.max_concurrent - active_count

                if available_slots > 0:
                    for item in self.queue_items:
                        if item.status == "QUEUED" and available_slots > 0:
                            item.status = "DOWNLOADING"
                            item.is_paused = False
                            item.is_cancelled = False
                            item.thread = threading.Thread(target=self.queue_download_worker, args=(item,), daemon=True)
                            item.thread.start()
                            available_slots -= 1
                            self.after(0, self.render_queue_list)

    def queue_download_worker(self, item):
        out_folder = item.save_folder
        mode = item.mode
        quality_choice = item.quality
        cookie_choice = item.cookie_source
        subtitles = item.subtitles
        ffmpeg_bin = get_ffmpeg_path()

        query = item.url
        target_url = query if is_valid_url(query) else f"ytsearch1:{query}"
        if is_valid_url(query) and not query.startswith(('http://', 'https://')):
            target_url = f"https://{query}"

        def item_progress_hook(d):
            if item.is_paused:
                raise DownloadPausedException("Paused by user")
            if item.is_cancelled:
                raise yt_dlp.utils.DownloadCancelled("Cancelled by user")

            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes', 0)
                now = time.time()
                elapsed = now - item.last_progress_time
                
                if elapsed > 0.4:
                    bytes_diff = downloaded - item.last_downloaded_bytes
                    speed = bytes_diff / elapsed
                    item.last_progress_time = now
                    item.last_downloaded_bytes = downloaded
                    item.speed_str = f"{speed / (1024*1024):.2f} MB/s"
                    if total > downloaded and speed > 0:
                        eta_sec = int((total - downloaded) / speed)
                        m, s = divmod(eta_sec, 60)
                        h, m = divmod(m, 60)
                        item.eta_str = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

                item.progress = (downloaded / total) if total > 0 else 0
                item.downloaded_bytes = downloaded
                item.total_bytes = total
                
                # Live UI update on card widget
                self.after(0, lambda it=item: self.update_queue_item_ui(it))

        ydl_opts = {
            'outtmpl': os.path.join(out_folder, '%(title)s.%(ext)s'),
            'progress_hooks': [item_progress_hook],
            'ffmpeg_location': ffmpeg_bin,
            'quiet': True,
            'no_warnings': True,
            'continuedl': True,
            'nopart': False
        }

        apply_cookie_and_bypass_opts(ydl_opts, cookie_choice)

        if mode == "audio":
            ydl_opts['format'] = 'bestaudio/best'
            ext = 'mp3'
            if "M4A" in quality_choice: ext = 'm4a'
            elif "WAV" in quality_choice: ext = 'wav'
            bitrate = "320"
            if "256" in quality_choice: bitrate = "256"
            elif "192" in quality_choice: bitrate = "192"
            elif "128" in quality_choice: bitrate = "128"
            ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': ext, 'preferredquality': bitrate}]
        else:
            height_map = {"4K (2160p)": 2160, "1440p (2K)": 1440, "1080p (Full HD)": 1080, "720p (HD)": 720, "480p": 480, "360p": 360}
            if "Best" in quality_choice:
                ydl_opts['format'] = "bestvideo+bestaudio/best"
            else:
                target_h = height_map.get(quality_choice, 1080)
                ydl_opts['format'] = f"bestvideo[height<={target_h}]+bestaudio/best[height<={target_h}]/best"
            ydl_opts['merge_output_format'] = 'mp4'

        if subtitles:
            ydl_opts['writesubtitles'] = True
            ydl_opts['subtitlesformat'] = 'srt'
            ydl_opts['embedsubtitles'] = True

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(target_url, download=True)
                if "entries" in info and info["entries"]:
                    info = info["entries"][0]
            
            title = info.get("title", item.title)
            filepath = ydl.prepare_filename(info)
            if mode == "audio":
                filepath = os.path.splitext(filepath)[0] + "." + ext
            elif mode == "video" and not filepath.endswith(".mp4"):
                filepath = os.path.splitext(filepath)[0] + ".mp4"

            item.title = title
            item.final_filepath = filepath
            item.status = "COMPLETED"
            item.progress = 1.0
            self.save_to_history(title, query, filepath, quality_choice)
            self.after(0, self.render_queue_list)

        except DownloadPausedException:
            item.status = "PAUSED"
            item.speed_str = "0 MB/s"
            self.after(0, self.render_queue_list)

        except yt_dlp.utils.DownloadCancelled:
            item.status = "CANCELLED"
            item.speed_str = "0 MB/s"
            self.after(0, self.render_queue_list)

        except Exception as e:
            item.status = "FAILED"
            item.error_message = str(e)
            item.speed_str = "0 MB/s"
            self.after(0, self.render_queue_list)

    def update_queue_item_ui(self, item):
        if hasattr(item, 'ui_pbar') and item.ui_pbar:
            item.ui_pbar.set(item.progress)
        if hasattr(item, 'ui_det') and item.ui_det:
            down_mb = item.downloaded_bytes / (1024 * 1024)
            tot_mb = item.total_bytes / (1024 * 1024)
            det_txt = f"{item.progress*100:.1f}% | {item.speed_str} | ETA: {item.eta_str} | ({down_mb:.1f} MB / {tot_mb:.1f} MB)"
            item.ui_det.configure(text=det_txt)


    # ==========================================
    # TAB 3: AI VIDEO DISCOVERY & BROWSER
    # ==========================================
    def build_ai_search_tab(self):
        tab = self.tab_ai_search
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # AI Search Header Card
        search_card = ctk.CTkFrame(tab, fg_color=COLOR_CARD, corner_radius=12)
        search_card.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        search_card.grid_columnconfigure(0, weight=1)

        self.ai_search_entry = ctk.CTkEntry(
            search_card,
            placeholder_text="🤖 Ask AI: e.g. 'Dark fantasy anime by MAPPA studio', 'Stranger Things Netflix', 'Python tutorials'...",
            font=ctk.CTkFont(size=13),
            height=42
        )
        self.ai_search_entry.grid(row=0, column=0, padx=(15, 10), pady=12, sticky="ew")
        self.ai_search_entry.bind("<Return>", lambda e: self.start_ai_search())

        ai_btn = ctk.CTkButton(
            search_card,
            text="✨ AI Search",
            width=130,
            height=42,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.start_ai_search
        )
        ai_btn.grid(row=0, column=1, padx=(0, 15), pady=12)

        # Platform Filter Chips Bar
        filters_frame = ctk.CTkFrame(tab, fg_color="transparent")
        filters_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))

        self.platform_var = ctk.StringVar(value="All Platforms")
        platforms = [
            ("🌟 All Platforms", "All"),
            ("▶ YouTube", "YouTube"),
            ("🎌 Anime & Crunchyroll", "Anime"),
            ("🍿 Netflix", "Netflix"),
            ("📺 Prime Video", "Prime Video")
        ]

        for idx, (label, val) in enumerate(platforms):
            btn = ctk.CTkRadioButton(
                filters_frame,
                text=label,
                variable=self.platform_var,
                value=val,
                command=self.start_ai_search,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=COLOR_ACCENT
            )
            btn.pack(side="left", padx=10)

        # Results Scrollable Frame
        self.ai_results_scroll = ctk.CTkScrollableFrame(
            tab,
            fg_color=COLOR_BG,
            corner_radius=10,
            label_text="AI Video Discovery Results (Shows Channel Name & Animation Studio)",
            label_font=ctk.CTkFont(size=14, weight="bold")
        )
        self.ai_results_scroll.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.ai_results_scroll.grid_columnconfigure(0, weight=1)

        # Initial Empty State
        self.ai_placeholder = ctk.CTkLabel(
            self.ai_results_scroll,
            text="Explore videos from YouTube, Netflix, Crunchyroll, Prime Video & Anime Studios.\n\nType any query or prompt above to see rich cards with Channel names, Studio names, and 1-Click Queueing.",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_TEXT_MUTED
        )
        self.ai_placeholder.pack(pady=60)

    def start_ai_search(self):
        query = self.ai_search_entry.get().strip()
        if not query:
            return

        for child in self.ai_results_scroll.winfo_children():
            child.destroy()

        loading_lbl = ctk.CTkLabel(
            self.ai_results_scroll,
            text=f"🤖 AI searching across platforms for '{query}'...",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_CYAN
        )
        loading_lbl.pack(pady=50)

        platform = self.platform_var.get()
        threading.Thread(target=self.ai_search_worker, args=(query, platform), daemon=True).start()

    def ai_search_worker(self, query, platform):
        try:
            results = AISearchEngine.ai_smart_search(query, platform=platform, max_total=18)
            self.after(0, lambda: self.render_ai_results(results))
        except Exception as e:
            err = str(e)
            self.after(0, lambda: self.render_ai_error(err))

    def render_ai_error(self, err):
        for child in self.ai_results_scroll.winfo_children():
            child.destroy()
        lbl = ctk.CTkLabel(self.ai_results_scroll, text=f"Search failed:\n{err}", text_color=COLOR_DANGER)
        lbl.pack(pady=50)

    def render_ai_results(self, results):
        for child in self.ai_results_scroll.winfo_children():
            child.destroy()

        if not results:
            lbl = ctk.CTkLabel(self.ai_results_scroll, text="No results found for your query.", font=ctk.CTkFont(size=14), text_color=COLOR_TEXT_MUTED)
            lbl.pack(pady=50)
            return

        for idx, item in enumerate(results):
            card = self.create_ai_result_card(idx, item)
            card.pack(fill="x", padx=5, pady=6)

    def create_ai_result_card(self, idx, item):
        card = ctk.CTkFrame(self.ai_results_scroll, fg_color=COLOR_CARD, corner_radius=10)
        card.grid_columnconfigure(1, weight=1)

        # Platform Badge Color
        plat = item.get("platform", "Web")
        p_color = COLOR_ACCENT
        if "Anime" in plat or "Crunchyroll" in plat: p_color = COLOR_PURPLE
        elif "Netflix" in plat: p_color = "#E50914"
        elif "Prime" in plat: p_color = "#00A8E1"

        # Left Column: Platform Badge / Thumbnail preview
        thumb_f = ctk.CTkFrame(card, fg_color="#12131A", width=120, height=85, corner_radius=8)
        thumb_f.grid(row=0, column=0, padx=12, pady=12, sticky="ns")
        thumb_f.pack_propagate(False)

        badge_lbl = ctk.CTkLabel(
            thumb_f,
            text=plat,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#FFFFFF",
            fg_color=p_color,
            corner_radius=6
        )
        badge_lbl.pack(anchor="nw", padx=6, pady=6)

        t_icon = "🎬" if item.get("downloadable") else "🎌"
        icon_lbl = ctk.CTkLabel(thumb_f, text=t_icon, font=ctk.CTkFont(size=22))
        icon_lbl.pack(expand=True)

        # Center Column: Rich Metadata
        info_f = ctk.CTkFrame(card, fg_color="transparent")
        info_f.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="ew")

        # Title
        title_lbl = ctk.CTkLabel(
            info_f,
            text=f"{idx+1}. {item.get('title', 'Unknown')}",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
            justify="left"
        )
        title_lbl.pack(fill="x")

        # Studio / Channel Name Highlight
        channel_type = item.get("channel_type", "Source")
        studio_or_channel = item.get("channel_or_studio", "Unknown")
        
        meta_parts = []
        if "Studio" in channel_type:
            meta_parts.append(f"🎨 Studio: {studio_or_channel}")
        else:
            meta_parts.append(f"👤 Channel: {studio_or_channel}")

        if item.get("score"): meta_parts.append(f"Rating: {item.get('score')}")
        if item.get("year"): meta_parts.append(f"Year: {item.get('year')}")
        if item.get("duration"): meta_parts.append(f"Duration: {item.get('duration')}")
        if item.get("episodes"): meta_parts.append(f"{item.get('episodes')}")

        meta_line = "  |  ".join(meta_parts)
        meta_lbl = ctk.CTkLabel(
            info_f,
            text=meta_line,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_CYAN if "Studio" in channel_type else COLOR_TEXT_MUTED,
            anchor="w"
        )
        meta_lbl.pack(fill="x", pady=(2, 2))

        # Description / Synopsis snippet
        desc = item.get("description", "")
        if desc:
            desc_lbl = ctk.CTkLabel(info_f, text=desc[:160] + ("..." if len(desc) > 160 else ""), font=ctk.CTkFont(size=10), text_color="#8E92A2", anchor="w", justify="left")
            desc_lbl.pack(fill="x")

        # Right Column: Action Buttons
        btn_f = ctk.CTkFrame(card, fg_color="transparent")
        btn_f.grid(row=0, column=2, padx=12, pady=10, sticky="e")

        if item.get("downloadable") or item.get("platform") == "YouTube":
            q_add_btn = ctk.CTkButton(
                btn_f,
                text="➕ Add to Queue",
                width=115,
                height=32,
                fg_color="#1E3A8A",
                hover_color="#1D4ED8",
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda it=item: self.add_ai_item_to_queue(it)
            )
            q_add_btn.pack(side="left", padx=3)

            dl_now_btn = ctk.CTkButton(
                btn_f,
                text="⬇ Download",
                width=90,
                height=32,
                fg_color=COLOR_ACCENT,
                hover_color=COLOR_ACCENT_HOVER,
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda it=item: self.select_ai_item_for_download(it)
            )
            dl_now_btn.pack(side="left", padx=3)

        else:
            # Anime / Netflix / Prime / Series actions
            q_add_btn = ctk.CTkButton(
                btn_f,
                text="➕ Queue Best Video",
                width=135,
                height=32,
                fg_color="#1E3A8A",
                hover_color="#1D4ED8",
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda it=item: self.add_ai_item_to_queue(it)
            )
            q_add_btn.pack(side="left", padx=3)

            watch_btn = ctk.CTkButton(
                btn_f,
                text="🌐 Open Stream",
                width=100,
                height=32,
                fg_color=p_color,
                hover_color="#3A3F4E",
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda u=item.get("platform_url"): self.open_browser_url(u)
            )
            watch_btn.pack(side="left", padx=3)

        copy_btn = ctk.CTkButton(
            btn_f,
            text="🔗 Copy",
            width=60,
            height=32,
            fg_color="#2B2F3A",
            hover_color="#3A3F4E",
            font=ctk.CTkFont(size=11),
            command=lambda u=item.get("url"): self.copy_to_clipboard(u)
        )
        copy_btn.pack(side="left", padx=3)

        return card

    def add_ai_item_to_queue(self, item):
        target_url = item.get("url")
        title = item.get("title", "Video")
        channel_or_studio = item.get("channel_or_studio", "")
        platform = item.get("platform", "Web")
        
        # If anime or non-direct stream, search and queue best available official video / trailer
        if not item.get("downloadable") and platform != "YouTube":
            search_q = item.get("search_query") or f"{title} anime trailer"
            target_url = f"ytsearch1:{search_q}"

        q_item = QueueItem(
            url=target_url,
            title=title,
            mode=self.format_mode_var.get(),
            quality=self.quality_var.get(),
            cookie_source=self.cookie_var.get(),
            subtitles=self.subtitles_var.get(),
            save_folder=self.folder_entry.get().strip() or self.save_folder,
            channel_or_studio=channel_or_studio,
            platform=platform
        )
        
        self.add_queue_item(q_item)
        messagebox.showinfo("Queue", f"Added to Download Queue:\n\n'{title}'\nSource: {channel_or_studio} ({platform})")
        self.tabview.set(" 📑 Download Queue ")

    def select_ai_item_for_download(self, item):
        self.tabview.set(" 📥 Single Downloader ")
        url = item.get("url")
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, url)
        self.start_fetch_info_thread()

    def open_browser_url(self, url):
        if url:
            import webbrowser
            webbrowser.open(url)

    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copied", "Link copied to clipboard!")


    # ==========================================
    # TAB 4: DOWNLOAD HISTORY
    # ==========================================
    def build_history_tab(self):
        tab = self.tab_history
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        hist_header = ctk.CTkFrame(tab, fg_color=COLOR_CARD, corner_radius=12)
        hist_header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        hist_header.grid_columnconfigure(0, weight=1)

        self.history_search_entry = ctk.CTkEntry(
            hist_header,
            placeholder_text="Search download history by title...",
            font=ctk.CTkFont(size=13),
            height=38
        )
        self.history_search_entry.grid(row=0, column=0, padx=(15, 10), pady=10, sticky="ew")
        self.history_search_entry.bind("<KeyRelease>", lambda e: self.render_history_list())

        clear_hist_btn = ctk.CTkButton(
            hist_header,
            text="🗑 Clear History",
            fg_color="#3A2025",
            hover_color="#5A252D",
            text_color="#FF6B6B",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=38,
            command=self.clear_history
        )
        clear_hist_btn.grid(row=0, column=1, padx=(0, 15), pady=10)

        self.history_scroll = ctk.CTkScrollableFrame(
            tab,
            fg_color=COLOR_BG,
            corner_radius=10
        )
        self.history_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.history_scroll.grid_columnconfigure(0, weight=1)

        self.render_history_list()

    def load_history(self):
        self.history_items = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    self.history_items = json.load(f)
                return
            except Exception:
                pass

        if os.path.exists(OLD_HISTORY_FILE):
            try:
                with open(OLD_HISTORY_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split(" | ")
                        if len(parts) >= 2:
                            self.history_items.append({
                                "date": parts[0],
                                "title": parts[1],
                                "url": "",
                                "path": "",
                                "quality": "N/A"
                            })
                self.save_history_file()
            except Exception:
                pass

    def save_history_file(self):
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history_items, f, indent=4)
        except Exception as e:
            print("Failed to save history:", e)

    def save_to_history(self, title, url, path, quality):
        item = {
            "date": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            "title": title,
            "url": url,
            "path": path,
            "quality": quality
        }
        self.history_items.insert(0, item)
        self.save_history_file()
        self.after(0, self.render_history_list)

    def render_history_list(self):
        for child in self.history_scroll.winfo_children():
            child.destroy()

        filter_text = self.history_search_entry.get().strip().lower() if hasattr(self, 'history_search_entry') else ""
        filtered = [item for item in self.history_items if filter_text in item["title"].lower()]

        if not filtered:
            lbl = ctk.CTkLabel(self.history_scroll, text="No download history records found.", font=ctk.CTkFont(size=14), text_color=COLOR_TEXT_MUTED)
            lbl.pack(pady=40)
            return

        for item in filtered:
            card = ctk.CTkFrame(self.history_scroll, fg_color=COLOR_CARD, corner_radius=10)
            card.pack(fill="x", padx=5, pady=6)
            card.grid_columnconfigure(0, weight=1)

            info_c = ctk.CTkFrame(card, fg_color="transparent")
            info_c.grid(row=0, column=0, padx=15, pady=12, sticky="ew")

            t_lbl = ctk.CTkLabel(info_c, text=item["title"], font=ctk.CTkFont(size=13, weight="bold"), anchor="w", justify="left")
            t_lbl.pack(fill="x")

            meta_txt = f"Downloaded: {item['date']}  |  Quality: {item.get('quality', 'N/A')}"
            m_lbl = ctk.CTkLabel(info_c, text=meta_txt, font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED, anchor="w")
            m_lbl.pack(fill="x", pady=(2, 0))

            btn_c = ctk.CTkFrame(card, fg_color="transparent")
            btn_c.grid(row=0, column=1, padx=15, pady=12, sticky="e")

            fpath = item.get("path", "")
            if fpath and os.path.exists(fpath):
                play_btn = ctk.CTkButton(btn_c, text="▶ Play", width=70, height=32, fg_color=COLOR_SUCCESS, hover_color="#218838", font=ctk.CTkFont(size=12, weight="bold"), command=lambda p=fpath: self.open_file(p))
                play_btn.pack(side="left", padx=3)

                show_btn = ctk.CTkButton(btn_c, text="📁 Show in Folder", width=110, height=32, fg_color="#2B2F3A", hover_color="#3A3F4E", command=lambda p=fpath: self.reveal_in_explorer(p))
                show_btn.pack(side="left", padx=3)

            del_btn = ctk.CTkButton(btn_c, text="❌ Delete", width=70, height=32, fg_color="#3A2025", hover_color="#5A252D", text_color="#FF6B6B", command=lambda it=item: self.delete_history_item(it))
            del_btn.pack(side="left", padx=3)

    def open_file(self, path):
        if os.path.exists(path):
            if sys.platform == "win32":
                os.startfile(path)
            else:
                subprocess.Popen(["xdg-open", path])

    def reveal_in_explorer(self, path):
        if os.path.exists(path):
            if sys.platform == "win32":
                subprocess.run(f'explorer /select,"{os.path.normpath(path)}"')
            else:
                folder = os.path.dirname(path)
                subprocess.Popen(["xdg-open", folder])

    def delete_history_item(self, item):
        if item in self.history_items:
            self.history_items.remove(item)
            self.save_history_file()
            self.render_history_list()

    def clear_history(self):
        if not self.history_items:
            return
        if messagebox.askyesno("Clear History", "Are you sure you want to clear all download history records?"):
            self.history_items = []
            self.save_history_file()
            self.render_history_list()


    # ==========================================
    # TAB 5: SETTINGS & YT-DLP UPDATES
    # ==========================================
    def build_settings_tab(self):
        tab = self.tab_settings
        tab.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(tab, fg_color=COLOR_CARD, corner_radius=12)
        card.pack(fill="x", padx=15, pady=15)
        card.grid_columnconfigure(0, weight=1)

        header = ctk.CTkLabel(card, text="⚙ Application & Engine Settings", font=ctk.CTkFont(size=18, weight="bold"))
        header.pack(anchor="w", padx=20, pady=(15, 10))

        # yt-dlp Core Engine Box
        engine_box = ctk.CTkFrame(card, fg_color="#12131A", corner_radius=10)
        engine_box.pack(fill="x", padx=20, pady=10)

        yt_ver = getattr(yt_dlp, 'version', None)
        ver_str = getattr(yt_ver, '__version__', '2026+ Latest') if yt_ver else 'Installed'

        engine_title = ctk.CTkLabel(
            engine_box,
            text=f"yt-dlp Core Extraction Engine (Current Version: {ver_str})",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        engine_title.pack(anchor="w", padx=15, pady=(12, 4))

        engine_desc = ctk.CTkLabel(
            engine_box,
            text="Keep the yt-dlp engine updated to bypass YouTube signature changes, bot checks, and stream updates.",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_MUTED
        )
        engine_desc.pack(anchor="w", padx=15, pady=(0, 10))

        self.update_ytdlp_btn = ctk.CTkButton(
            engine_box,
            text="🔄 Check & Update yt-dlp",
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(size=12, weight="bold"),
            height=36,
            command=self.trigger_ytdlp_update
        )
        self.update_ytdlp_btn.pack(anchor="w", padx=15, pady=(0, 15))

        # App Info Box
        app_box = ctk.CTkFrame(card, fg_color="#12131A", corner_radius=10)
        app_box.pack(fill="x", padx=20, pady=(0, 20))

        info_txt = (
            f"App: {APP_NAME}\n"
            f"Release Version: {APP_VERSION}\n"
            f"Features: Multi-Item Download Queue (Pause/Resume/Retry), AI Video Discovery, Anime Studio & YouTube Channel Explorer\n"
            f"FFmpeg Status: Embedded / Ready"
        )
        app_info_lbl = ctk.CTkLabel(app_box, text=info_txt, font=ctk.CTkFont(size=12), justify="left")
        app_info_lbl.pack(anchor="w", padx=15, pady=15)

    def trigger_ytdlp_update(self):
        self.update_ytdlp_btn.configure(state="disabled", text="Updating yt-dlp...")
        threading.Thread(target=self.update_ytdlp_worker, daemon=True).start()

    def update_ytdlp_worker(self):
        try:
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            self.after(0, lambda: self.handle_ytdlp_update_result(True, "yt-dlp was successfully updated to the latest version!"))
        except Exception as e:
            self.after(0, lambda: self.handle_ytdlp_update_result(False, str(e)))

    def handle_ytdlp_update_result(self, success, msg):
        self.update_ytdlp_btn.configure(state="normal", text="🔄 Check & Update yt-dlp")
        if success:
            messagebox.showinfo("yt-dlp Update", msg)
        else:
            messagebox.showerror("Update Error", f"Failed to update yt-dlp:\n\n{msg}")

    def toggle_theme(self):
        mode = "Dark" if self.theme_switch.get() == 1 else "Light"
        ctk.set_appearance_mode(mode)
        self.settings["theme"] = mode
        save_settings(self.settings)

    def on_closing(self):
        self.queue_dispatcher_running = False
        self.destroy()

if __name__ == "__main__":
    app = DownloaderApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()