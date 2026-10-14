# Universal Video Downloader Pro v4.1.1

A modern, high-performance desktop video & audio downloader application for Windows built with Python, CustomTkinter, and `yt-dlp`.

![Platform](https://img.shields.io/badge/Platform-Windows-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11%2B-brightgreen.svg)
![Release](https://img.shields.io/badge/Release-v4.1.1-red.svg)
![yt-dlp](https://img.shields.io/badge/yt--dlp-2026%2B%20Latest-orange.svg)

---

## 🌟 What's New in Version 4.1.1

### Fix: Dedicated TV Shows & Live Streams Tabs Now Visible
- **Rebuilt executable** with all 7 navigation tabs properly displayed: 📥 Downloader, 📑 Queue, 🤖 AI Discovery, 📺 TV Shows, 🔴 Live Streams, 📜 History, ⚙ Settings.
- Previous `.exe` (v4.0.0) was built before the new tabs were added to source code — this release corrects that.

---

## 🌟 Features (Full List from v4.1.0+)

### 1. 📺 TV Shows & Episode Explorer
- **Dedicated TV Shows Discovery**: Browse curated hit television series (e.g., *Breaking Bad*, *Stranger Things*, *The Boys*, *Game of Thrones*, *Fallout*, *Shogun*, *Arcane*) or search any global television or web series via TVMaze.
- **Rich Metadata & Network Badges**: Displays official networks/studios (HBO, Netflix, Prime Video, Apple TV+, AMC, Disney+), ratings, premiered year, series status (Running / Ended), and synopsis.
- **Interactive Season & Episode Explorer**: Click **"📋 Seasons & Episodes"** to launch an interactive episode guide modal.
- **1-Click Season Batch Queueing**: Select any season from the dropdown and click **"➕ Queue Entire Season"** to automatically add all episodes of that season to the Download Queue manager in one click!
- **Episode Quick Actions**: Send any individual episode directly to the Single Downloader or Download Queue.

### 2. 🔴 Live Streams Discovery & Real-Time DVR Recorder
- **Multi-Platform Live Discovery**: Discovers live broadcasts across **YouTube Live** and **Twitch** in real-time with category filters (Gaming, Breaking News, 24/7 Lofi & Music, Podcasts).
- **Direct Live Stream URL Recorder**: Paste any YouTube Live, Twitch, Kick, or direct `.m3u8` HLS stream URL into the dedicated Direct Recorder.
- **Live DVR Support (`--live-from-start`)**: Record live broadcasts from the very start of the stream or from the current live point.
- **Live Recording Stats**: Real-time recording stats showing recorded size (MB), streaming bitrate, and an active recording timer (`REC TIME: HH:MM:SS`).
- **Safe Container Remuxing**: Interrupted or user-stopped live recordings are automatically remuxed into a clean `.mp4` container (`ffmpeg -c copy -movflags +faststart`) to ensure 100% playable files without corrupted headers.

### 3. 📑 Full Download Queue with Pause, Resume & Retry
- **Multi-Item Queue Management**: Queue dozens or hundreds of videos with sequential or concurrent processing (1, 2, or 3 parallel downloads).
- **Pause & Resume**: Seamlessly pause active downloads. Temporary `.part` files are preserved and resumed via HTTP byte range streaming without restarting from 0%.
- **Intelligent Retry**: Instantly retry any failed or interrupted downloads with a single click.
- **Batch Import**: Paste multiple URLs (one per line) to batch-queue videos or playlists with preset audio/video format and quality.
- **Live Progress & Speeds**: Individual progress bars, dynamic download speed calculation, remaining size, and ETA per item.

### 4. 🤖 AI Multi-Platform Video Discovery & Browsing
- **Natural Language Search**: Ask the built-in AI search assistant in plain English (e.g., *"Dark fantasy anime by MAPPA studio"*, *"Stranger Things on Netflix"*, *"Python GUI tutorials"*).
- **Universal Multi-Platform Support**:
  - **YouTube**: Displays verified **Channel Names**, upload duration, view counts, and direct 1-click download links.
  - **Anime & Crunchyroll**: Displays exact **Animation Studio Names** (e.g., MAPPA, ufotable, Bones, Wit Studio, Madhouse, Toei Animation), ratings, episode counts, genres, and stream links.
  - **Netflix & Amazon Prime Video**: Discovers series/movies with **Production Studios / Networks**, release year, synopsis, and direct watch links.
  - **Live Streams**: Real-time Twitch streamer and YouTube live stream discovery.
  - **Other Platforms**: Vimeo, Twitch, Dailymotion, Bilibili, and 1000+ web sources.
- **1-Click Queueing**: Add any discovered video, show, or anime directly to your download queue.

### 5. 🔄 Core Engine & Path Stability
- Windows path normalization for FFmpeg ensuring error-free remuxing across all drives.
- Built-in one-click yt-dlp updater in the **Settings** tab.

---

## 🚀 Download & Installation

### Option 1: Pre-built Windows Executable (.exe)
1. Head over to the **[GitHub Releases](https://github.com/LazarusEffect-dotcom/All_Download/releases)** section.
2. Download `Youtube.exe` or `Youtube-Downloader-Windows-x64.zip` from release **v4.1.1**.
3. Run the executable directly. FFmpeg is embedded; no installation or Python required!

---

## 🛠 Local Development Setup

To run the application from source code:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/LazarusEffect-dotcom/All_Download.git
   cd All_Download
   ```

2. **Create a virtual environment (optional but recommended)**:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   python Youtube.py
   ```

---

## 📦 Building the Windows .exe Locally

To build a standalone `.exe` using PyInstaller:

```powershell
pyinstaller --clean Youtube.spec
```

The resulting binary will be located at `dist/Youtube.exe`.

---

## 🤖 GitHub Releases CI/CD Automated Deployment

This repository includes a GitHub Actions workflow (`.github/workflows/release.yml`) that automatically builds and deploys the Windows `.exe` to GitHub Releases:

### Deploying a New Release:
1. **Push a Git tag**:
   ```bash
   git tag v4.1.1
   git push origin v4.1.1
   ```
2. **Or trigger manually via GitHub Actions**:
   - Go to your repository on GitHub.
   - Click on the **Actions** tab.
   - Select **Build and Release Windows Executable**.
   - Click **Run workflow**, specify the release tag (`v4.1.1`), and run.
