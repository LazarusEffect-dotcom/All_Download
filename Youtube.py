import os
import sys
import json
import time
import re
import subprocess
import threading
import requests
from io import BytesIO
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import yt_dlp

# --- Global Configuration & Theme Setup ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

APP_NAME = "Universal Video Downloader Pro"
APP_VERSION = "v3.0 Ultra"
HISTORY_FILE = "download_history.json"
OLD_HISTORY_FILE = "download_history.txt"
SETTINGS_FILE = "settings.json"

COLOR_BG = "#0F1015"
COLOR_CARD = "#181A20"
COLOR_CARD_HOVER = "#222630"
COLOR_ACCENT = "#FF0033"  # Vibrant Red
COLOR_ACCENT_HOVER = "#CC0029"
COLOR_TEXT_MAIN = "#FFFFFF"
COLOR_TEXT_MUTED = "#A0A5B5"
COLOR_SUCCESS = "#28A745"
COLOR_WARNING = "#FFC107"

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
    return "ffmpeg"  # Fallback to system PATH

def load_settings():
    default_settings = {
        "save_folder": os.path.join(os.path.expanduser("~"), "Downloads"),
        "theme": "Dark",
        "default_quality": "Best Available (Max 4K/8K)",
        "download_subtitles": False,
        "audio_bitrate": "320 kbps (Best)",
        "cookie_source": "Auto Detect Browser"
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

    # 1. Check cookies.txt file first if present
    cookies_path = resource_path('cookies.txt')
    if os.path.exists(cookies_path) and os.path.getsize(cookies_path) > 0:
        ydl_opts['cookiefile'] = cookies_path
        return ydl_opts

    if cookie_source == "None / Public Only":
        return ydl_opts

    # 2. Browser cookie resolution
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

class DownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.settings = load_settings()
        ctk.set_appearance_mode(self.settings.get("theme", "Dark"))

        self.title(f"{APP_NAME} {APP_VERSION} - Any Source & Premium Supported")
        self.geometry("1180x780")
        self.minsize(980, 680)

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
        self.is_downloading = False
        self.cancel_requested = False
        self.download_thread = None
        self.last_progress_time = 0
        self.last_downloaded_bytes = 0

        self.load_history()

        # Build Main UI Layout
        self.setup_ui()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Top Header Bar ---
        header_frame = ctk.CTkFrame(self, fg_color="#14161D", height=65, corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)

        # Logo / Branding with App Icon Image
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
                title_icon = ctk.CTkLabel(
                    brand_frame, text="▶", font=ctk.CTkFont(size=26, weight="bold"), text_color=COLOR_ACCENT
                )
                title_icon.pack(side="left", padx=(0, 8))
        else:
            title_icon = ctk.CTkLabel(
                brand_frame, text="▶", font=ctk.CTkFont(size=26, weight="bold"), text_color=COLOR_ACCENT
            )
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
            text="VIDEO DOWNLOADER PRO",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=COLOR_ACCENT
        )
        sub_title.pack(side="left", padx=(6, 0))

        # Header Right Controls
        header_controls = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_controls.grid(row=0, column=2, padx=20, pady=10, sticky="e")

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
            text="📁 Downloads Folder",
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

        self.tab_downloader = self.tabview.add(" 📥 Downloader ")
        self.tab_search = self.tabview.add(" 🔍 Search Video ")
        self.tab_history = self.tabview.add(" 📜 Download History ")

        # Build individual tabs
        self.build_downloader_tab()
        self.build_search_tab()
        self.build_history_tab()

    # ==========================================
    # TAB 1: DOWNLOADER
    # ==========================================
    def build_downloader_tab(self):
        tab = self.tab_downloader
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=2)
        tab.grid_rowconfigure(1, weight=1)

        # --- URL Bar Section (Top Full Width) ---
        url_card = ctk.CTkFrame(tab, fg_color=COLOR_CARD, corner_radius=12)
        url_card.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 10))
        url_card.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            url_card,
            placeholder_text="Paste ANY link (YouTube Premium, TikTok, Instagram, Twitter, Facebook, Vimeo, Twitch...) or search...",
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

        # --- Left Column: Video Metadata & Preview Card ---
        self.preview_card = ctk.CTkFrame(tab, fg_color=COLOR_CARD, corner_radius=12)
        self.preview_card.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)
        self.preview_card.grid_columnconfigure(0, weight=1)
        self.preview_card.grid_rowconfigure(0, weight=1)

        # Placeholder canvas/label
        self.thumbnail_label = ctk.CTkLabel(
            self.preview_card,
            text="No Video Selected\n\nPaste any video URL or search above to preview metadata.\nSupports YouTube Premium, Private Links & 1000+ Platforms!",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_TEXT_MUTED,
            corner_radius=8,
            fg_color="#12131A"
        )
        self.thumbnail_label.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")

        # Video Info Text Container
        self.info_frame = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        self.info_frame.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="ew")

        self.video_title_label = ctk.CTkLabel(
            self.info_frame,
            text="Ready to download",
            font=ctk.CTkFont(size=15, weight="bold"),
            wraplength=500,
            justify="left"
        )
        self.video_title_label.pack(anchor="w", pady=(0, 4))

        self.video_details_label = ctk.CTkLabel(
            self.info_frame,
            text="Channel/Source: -- | Duration: -- | Views: --",
            font=ctk.CTkFont(size=12),
            text_color=COLOR_TEXT_MUTED,
            justify="left"
        )
        self.video_details_label.pack(anchor="w")

        # --- Right Column: Download Options & Execution Card ---
        options_card = ctk.CTkFrame(tab, fg_color=COLOR_CARD, corner_radius=12)
        options_card.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=5)
        options_card.grid_columnconfigure(0, weight=1)

        opts_header = ctk.CTkLabel(
            options_card,
            text="⚙ Download & Auth Settings",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        opts_header.pack(anchor="w", padx=15, pady=(12, 6))

        # Download Mode (Video vs Audio)
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
        q_label = ctk.CTkLabel(
            options_card,
            text="Select Quality / Format:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
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

        # Cookie / Browser Auth Selector (For Premium & Member Content)
        cookie_label = ctk.CTkLabel(
            options_card,
            text="🔓 Premium / Browser Auth Cookies:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
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
        folder_label = ctk.CTkLabel(
            options_card,
            text="Save Directory:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT_MUTED
        )
        folder_label.pack(anchor="w", padx=15, pady=(8, 2))

        folder_box = ctk.CTkFrame(options_card, fg_color="transparent")
        folder_box.pack(fill="x", padx=15, pady=(0, 10))
        folder_box.grid_columnconfigure(0, weight=1)

        self.folder_entry = ctk.CTkEntry(
            folder_box,
            font=ctk.CTkFont(size=11),
            height=34
        )
        self.folder_entry.insert(0, self.save_folder)
        self.folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        browse_btn = ctk.CTkButton(
            folder_box,
            text="📁 Browse",
            width=75,
            height=34,
            fg_color="#2B2F3A",
            hover_color="#3A3F4E",
            command=self.choose_save_folder
        )
        browse_btn.grid(row=0, column=1)

        # Separator Line
        sep = ctk.CTkFrame(options_card, fg_color="#2E3340", height=1)
        sep.pack(fill="x", padx=15, pady=4)

        # Download Progress & Status Box
        self.progress_frame = ctk.CTkFrame(options_card, fg_color="#12131A", corner_radius=10)
        self.progress_frame.pack(fill="x", padx=15, pady=8)

        self.status_label = ctk.CTkLabel(
            self.progress_frame,
            text="Status: Ready",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_TEXT_MAIN,
            anchor="w"
        )
        self.status_label.pack(fill="x", padx=12, pady=(8, 3))

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            progress_color=COLOR_ACCENT,
            height=12
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=12, pady=3)

        self.details_label = ctk.CTkLabel(
            self.progress_frame,
            text="0.0% | -- MB/s | ETA: --:--",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED,
            anchor="w"
        )
        self.details_label.pack(fill="x", padx=12, pady=(2, 8))

        # Main Download & Cancel Action Buttons
        actions_frame = ctk.CTkFrame(options_card, fg_color="transparent")
        actions_frame.pack(fill="x", padx=15, pady=(4, 12))
        actions_frame.grid_columnconfigure(0, weight=3)
        actions_frame.grid_columnconfigure(1, weight=1)

        self.download_btn = ctk.CTkButton(
            actions_frame,
            text="⬇ START DOWNLOAD",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            height=44,
            corner_radius=8,
            command=self.start_download_thread
        )
        self.download_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.cancel_btn = ctk.CTkButton(
            actions_frame,
            text="✖ Cancel",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#3A2025",
            hover_color="#5A252D",
            text_color="#FF6B6B",
            height=44,
            corner_radius=8,
            state="disabled",
            command=self.cancel_download
        )
        self.cancel_btn.grid(row=0, column=1, sticky="ew")

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

    # ==========================================
    # VIDEO METADATA FETCHING
    # ==========================================
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
            
            if is_valid_url(query):
                target_url = query if query.startswith(('http://', 'https://')) else f"https://{query}"
            else:
                target_url = f"ytsearch1:{query}"

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False
            }
            
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
        uploader = info.get("uploader") or info.get("extractor_key") or info.get("webpage_url_domain") or "Unknown Source"
        duration_sec = info.get("duration", 0)
        views = info.get("view_count", 0)
        webpage_url = info.get("webpage_url", "")

        # Update entry if searched via keyword
        if webpage_url:
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, webpage_url)

        # Format Duration
        if duration_sec:
            mins, secs = divmod(int(duration_sec), 60)
            hrs, mins = divmod(mins, 60)
            duration_str = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs else f"{mins:02d}:{secs:02d}"
        else:
            duration_str = "N/A"
            
        views_str = f"{views:,}" if views else "N/A"

        self.video_title_label.configure(text=title)
        self.video_details_label.configure(text=f"Source/Channel: {uploader}  |  Duration: {duration_str}  |  Views: {views_str}")
        self.status_label.configure(text="Status: Ready to Download")

        # Load Thumbnail Image
        thumbnail_url = info.get("thumbnail")
        if thumbnail_url:
            threading.Thread(target=self.load_thumbnail_image, args=(thumbnail_url,), daemon=True).start()

    def load_thumbnail_image(self, url):
        try:
            resp = requests.get(url, timeout=10)
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            
            # Resize image maintaining aspect ratio
            img = img.resize((440, 247), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(440, 247))
            
            self.after(0, lambda: self.thumbnail_label.configure(image=ctk_img, text=""))
        except Exception as e:
            print("Thumbnail load error:", e)

    # ==========================================
    # DOWNLOAD LOGIC & MULTI-THREADING
    # ==========================================
    def start_download_thread(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Missing", "Please enter a valid video URL or keyword.")
            return

        if self.is_downloading:
            messagebox.showinfo("In Progress", "A download is already running.")
            return

        self.is_downloading = True
        self.cancel_requested = False
        self.download_btn.configure(state="disabled", fg_color="#3A3F4E")
        self.cancel_btn.configure(state="normal", fg_color="#E53935")
        self.progress_bar.set(0)
        self.status_label.configure(text="Status: Starting download...")

        self.last_progress_time = time.time()
        self.last_downloaded_bytes = 0

        self.download_thread = threading.Thread(target=self.download_worker, args=(url,), daemon=True)
        self.download_thread.start()

    def progress_hook(self, d):
        if self.cancel_requested:
            raise yt_dlp.utils.DownloadCancelled("Download cancelled by user.")

        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            
            now = time.time()
            elapsed = now - self.last_progress_time
            
            speed_str = "-- MB/s"
            eta_str = "--:--"
            
            if elapsed > 0.4:
                bytes_diff = downloaded - self.last_downloaded_bytes
                speed = bytes_diff / elapsed  # bytes/sec
                self.last_progress_time = now
                self.last_downloaded_bytes = downloaded
                
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
            
            self.after(0, lambda: self.update_download_progress(pct, detail_txt, "Downloading..."))
            
        elif d['status'] == 'finished':
            self.after(0, lambda: self.update_download_progress(1.0, "Processing & Merging media files...", "Merging Audio/Video..."))

    def update_download_progress(self, pct, details, status):
        self.progress_bar.set(pct)
        self.details_label.configure(text=details)
        self.status_label.configure(text=f"Status: {status}")

    def download_worker(self, query):
        out_folder = self.folder_entry.get().strip() or self.save_folder
        mode = self.format_mode_var.get()
        quality_choice = self.quality_var.get()
        cookie_choice = self.cookie_var.get()
        subtitles = self.subtitles_var.get()

        ffmpeg_bin = get_ffmpeg_path()

        if is_valid_url(query):
            target_url = query if query.startswith(('http://', 'https://')) else f"https://{query}"
        else:
            target_url = f"ytsearch1:{query}"

        ydl_opts = {
            'outtmpl': os.path.join(out_folder, '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'ffmpeg_location': ffmpeg_bin,
            'quiet': True,
            'no_warnings': True,
        }

        apply_cookie_and_bypass_opts(ydl_opts, cookie_choice)

        if mode == "audio":
            ydl_opts['format'] = 'bestaudio/best'
            ext = 'mp3'
            if "M4A" in quality_choice:
                ext = 'm4a'
            elif "WAV" in quality_choice:
                ext = 'wav'
            
            bitrate = "320"
            if "256" in quality_choice: bitrate = "256"
            elif "192" in quality_choice: bitrate = "192"
            elif "128" in quality_choice: bitrate = "128"

            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': ext,
                'preferredquality': bitrate,
            }]
        else:
            height_map = {
                "4K (2160p)": 2160,
                "1440p (2K)": 1440,
                "1080p (Full HD)": 1080,
                "720p (HD)": 720,
                "480p": 480,
                "360p": 360
            }
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
            self.after(0, lambda: self.handle_download_success(title))

        except yt_dlp.utils.DownloadCancelled:
            self.after(0, self.handle_download_cancelled)
        except Exception as e:
            err = str(e)
            self.after(0, lambda: self.handle_download_error(err))

    def cancel_download(self):
        if self.is_downloading:
            self.cancel_requested = True
            self.status_label.configure(text="Status: Cancelling download...")

    def handle_download_success(self, title):
        self.is_downloading = False
        self.download_btn.configure(state="normal", fg_color=COLOR_ACCENT)
        self.cancel_btn.configure(state="disabled", fg_color="#3A2025")
        self.progress_bar.set(1.0)
        self.status_label.configure(text="Status: Download Complete! 🎉")
        self.details_label.configure(text=f"Saved: {title[:50]}")
        messagebox.showinfo("Success", f"Download Completed Successfully!\n\n'{title}'")

    def handle_download_cancelled(self):
        self.is_downloading = False
        self.download_btn.configure(state="normal", fg_color=COLOR_ACCENT)
        self.cancel_btn.configure(state="disabled", fg_color="#3A2025")
        self.progress_bar.set(0)
        self.status_label.configure(text="Status: Download Cancelled")
        self.details_label.configure(text="Cancelled by user.")

    def handle_download_error(self, error):
        self.is_downloading = False
        self.download_btn.configure(state="normal", fg_color=COLOR_ACCENT)
        self.cancel_btn.configure(state="disabled", fg_color="#3A2025")
        self.status_label.configure(text="Status: Download Failed")
        self.details_label.configure(text="Error occurred during download.")
        messagebox.showerror("Download Error", f"An error occurred while downloading:\n\n{error}")

    # ==========================================
    # TAB 2: SEARCH TAB
    # ==========================================
    def build_search_tab(self):
        tab = self.tab_search
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # Search Input Header
        search_card = ctk.CTkFrame(tab, fg_color=COLOR_CARD, corner_radius=12)
        search_card.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        search_card.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            search_card,
            placeholder_text="Enter search keywords or video topic...",
            font=ctk.CTkFont(size=13),
            height=42
        )
        self.search_entry.grid(row=0, column=0, padx=(15, 10), pady=12, sticky="ew")
        self.search_entry.bind("<Return>", lambda e: self.start_youtube_search())

        do_search_btn = ctk.CTkButton(
            search_card,
            text="🔍 Search Video",
            width=130,
            height=42,
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.start_youtube_search
        )
        do_search_btn.grid(row=0, column=1, padx=(0, 15), pady=12)

        # Results Scrollable Frame
        self.search_scroll = ctk.CTkScrollableFrame(
            tab,
            fg_color=COLOR_BG,
            corner_radius=10,
            label_text="Search Results",
            label_font=ctk.CTkFont(size=14, weight="bold")
        )
        self.search_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.search_scroll.grid_columnconfigure(0, weight=1)

        # Initial Empty State Label
        self.search_placeholder = ctk.CTkLabel(
            self.search_scroll,
            text="Search videos to see interactive result cards here.",
            font=ctk.CTkFont(size=14),
            text_color=COLOR_TEXT_MUTED
        )
        self.search_placeholder.pack(pady=50)

    def start_youtube_search(self):
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showwarning("Search", "Please enter a search keyword.")
            return

        for child in self.search_scroll.winfo_children():
            child.destroy()

        loading_lbl = ctk.CTkLabel(
            self.search_scroll,
            text=f"Searching for '{query}'...",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLOR_ACCENT
        )
        loading_lbl.pack(pady=40)

        threading.Thread(target=self.youtube_search_worker, args=(query,), daemon=True).start()

    def youtube_search_worker(self, query):
        try:
            cookie_choice = self.cookie_var.get()
            ydl_opts = {'quiet': True, 'extract_flat': True}
            apply_cookie_and_bypass_opts(ydl_opts, cookie_choice)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                res = ydl.extract_info(f"ytsearch20:{query}", download=False)

            results = res.get("entries", [])
            self.search_results = results
            self.after(0, lambda: self.render_search_results(results))
        except Exception as e:
            err = str(e)
            self.after(0, lambda: self.render_search_error(err))

    def render_search_error(self, err):
        for child in self.search_scroll.winfo_children():
            child.destroy()
        lbl = ctk.CTkLabel(self.search_scroll, text=f"Search failed:\n{err}", text_color="#FF6B6B")
        lbl.pack(pady=40)

    def render_search_results(self, results):
        for child in self.search_scroll.winfo_children():
            child.destroy()

        if not results:
            lbl = ctk.CTkLabel(self.search_scroll, text="No results found for your search query.")
            lbl.pack(pady=40)
            return

        for idx, item in enumerate(results):
            title = item.get("title", "Unknown Title")
            uploader = item.get("uploader") or item.get("channel") or "Video Channel"
            url = item.get("url") or item.get("webpage_url") or f"https://www.youtube.com/watch?v={item.get('id')}"
            duration = item.get("duration")

            dur_str = ""
            if duration:
                mins, secs = divmod(int(duration), 60)
                hrs, mins = divmod(mins, 60)
                dur_str = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs else f"{mins:02d}:{secs:02d}"

            card = ctk.CTkFrame(self.search_scroll, fg_color=COLOR_CARD, corner_radius=10)
            card.pack(fill="x", padx=5, pady=6)
            card.grid_columnconfigure(0, weight=1)

            # Left Info Container
            info_c = ctk.CTkFrame(card, fg_color="transparent")
            info_c.grid(row=0, column=0, padx=15, pady=12, sticky="ew")

            t_lbl = ctk.CTkLabel(
                info_c,
                text=f"{idx+1}. {title}",
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w",
                justify="left"
            )
            t_lbl.pack(fill="x")

            d_lbl = ctk.CTkLabel(
                info_c,
                text=f"Channel: {uploader}  " + (f"|  Duration: {dur_str}" if dur_str else ""),
                font=ctk.CTkFont(size=11),
                text_color=COLOR_TEXT_MUTED,
                anchor="w"
            )
            d_lbl.pack(fill="x", pady=(2, 0))

            # Action Buttons
            btn_c = ctk.CTkFrame(card, fg_color="transparent")
            btn_c.grid(row=0, column=1, padx=15, pady=12, sticky="e")

            dl_btn = ctk.CTkButton(
                btn_c,
                text="⬇ Select & Download",
                width=140,
                height=34,
                fg_color=COLOR_ACCENT,
                hover_color=COLOR_ACCENT_HOVER,
                font=ctk.CTkFont(size=12, weight="bold"),
                command=lambda u=url: self.select_search_item(u)
            )
            dl_btn.pack(side="left", padx=4)

            copy_btn = ctk.CTkButton(
                btn_c,
                text="🔗 Copy Link",
                width=90,
                height=34,
                fg_color="#2B2F3A",
                hover_color="#3A3F4E",
                command=lambda u=url: self.copy_to_clipboard(u)
            )
            copy_btn.pack(side="left", padx=4)

    def select_search_item(self, url):
        self.tabview.set(" 📥 Downloader ")
        self.url_entry.delete(0, tk.END)
        self.url_entry.insert(0, url)
        self.start_fetch_info_thread()

    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copied", "Link copied to clipboard!")

    # ==========================================
    # TAB 3: DOWNLOAD HISTORY
    # ==========================================
    def build_history_tab(self):
        tab = self.tab_history
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # Header Bar
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

        # Scrollable History List
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
            lbl = ctk.CTkLabel(
                self.history_scroll,
                text="No download history items found.",
                font=ctk.CTkFont(size=14),
                text_color=COLOR_TEXT_MUTED
            )
            lbl.pack(pady=40)
            return

        for item in filtered:
            card = ctk.CTkFrame(self.history_scroll, fg_color=COLOR_CARD, corner_radius=10)
            card.pack(fill="x", padx=5, pady=6)
            card.grid_columnconfigure(0, weight=1)

            # Details
            info_c = ctk.CTkFrame(card, fg_color="transparent")
            info_c.grid(row=0, column=0, padx=15, pady=12, sticky="ew")

            t_lbl = ctk.CTkLabel(
                info_c,
                text=item["title"],
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
                justify="left"
            )
            t_lbl.pack(fill="x")

            meta_txt = f"Downloaded: {item['date']}  |  Quality: {item.get('quality', 'N/A')}"
            m_lbl = ctk.CTkLabel(
                info_c,
                text=meta_txt,
                font=ctk.CTkFont(size=11),
                text_color=COLOR_TEXT_MUTED,
                anchor="w"
            )
            m_lbl.pack(fill="x", pady=(2, 0))

            # Action buttons
            btn_c = ctk.CTkFrame(card, fg_color="transparent")
            btn_c.grid(row=0, column=1, padx=15, pady=12, sticky="e")

            fpath = item.get("path", "")
            if fpath and os.path.exists(fpath):
                play_btn = ctk.CTkButton(
                    btn_c,
                    text="▶ Play",
                    width=70,
                    height=32,
                    fg_color=COLOR_SUCCESS,
                    hover_color="#218838",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    command=lambda p=fpath: self.open_file(p)
                )
                play_btn.pack(side="left", padx=3)

                show_btn = ctk.CTkButton(
                    btn_c,
                    text="📁 Show in Folder",
                    width=110,
                    height=32,
                    fg_color="#2B2F3A",
                    hover_color="#3A3F4E",
                    command=lambda p=fpath: self.reveal_in_explorer(p)
                )
                show_btn.pack(side="left", padx=3)

            del_btn = ctk.CTkButton(
                btn_c,
                text="❌ Delete",
                width=70,
                height=32,
                fg_color="#3A2025",
                hover_color="#5A252D",
                text_color="#FF6B6B",
                command=lambda it=item: self.delete_history_item(it)
            )
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

    def toggle_theme(self):
        mode = "Dark" if self.theme_switch.get() == 1 else "Light"
        ctk.set_appearance_mode(mode)
        self.settings["theme"] = mode
        save_settings(self.settings)

if __name__ == "__main__":
    app = DownloaderApp()
    app.mainloop()