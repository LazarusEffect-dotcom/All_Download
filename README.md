# Universal Video Downloader Pro v4.0.0

A modern, high-performance desktop video & audio downloader application for Windows built with Python, CustomTkinter, and `yt-dlp`.

![Platform](https://img.shields.io/badge/Platform-Windows-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11%2B-brightgreen.svg)
![Release](https://img.shields.io/badge/Release-v4.0.0-red.svg)
![yt-dlp](https://img.shields.io/badge/yt--dlp-2026%2B%20Latest-orange.svg)

---

## 🌟 What's New in Version 4.0.0

### 1. 📑 Full Download Queue with Pause, Resume & Retry
- **Multi-Item Queue Management**: Queue dozens or hundreds of videos with sequential or concurrent processing (1, 2, or 3 parallel downloads).
- **Pause & Resume**: Seamlessly pause active downloads. Temporary `.part` files are preserved and resumed via HTTP byte range streaming without restarting from 0%.
- **Intelligent Retry**: Instantly retry any failed or interrupted downloads with a single click.
- **Batch Import**: Paste multiple URLs (one per line) to batch-queue videos or playlists with preset audio/video format and quality.
- **Live Progress & Speeds**: Individual progress bars, dynamic download speed calculation, remaining size, and ETA per item.

### 2. 🤖 AI Multi-Platform Video Discovery & Browsing
- **Natural Language Search**: Ask the built-in AI search assistant in plain English (e.g., *"Dark fantasy anime by MAPPA studio"*, *"Stranger Things on Netflix"*, *"Python GUI tutorials"*).
- **Universal Multi-Platform Support**:
  - **YouTube**: Displays verified **Channel Names**, upload duration, view counts, and direct 1-click download links.
  - **Anime & Crunchyroll**: Displays exact **Animation Studio Names** (e.g., MAPPA, ufotable, Bones, Wit Studio, Madhouse, Toei Animation, Kyoto Animation, CloverWorks, A-1 Pictures), user ratings, episode counts, genres, and stream links.
  - **Netflix & Amazon Prime Video**: Discovers series/movies with **Production Studios / Networks**, release year, synopsis, and direct watch links.
  - **Other Platforms**: Vimeo, Twitch, Dailymotion, Bilibili, and 1000+ web sources.
- **1-Click Queueing**: Add any discovered video or anime directly to your download queue.

### 3. 🔄 yt-dlp Core Engine Updates
- Built-in one-click yt-dlp updater in the **Settings** tab to keep the extraction engine ahead of platform signature changes and anti-bot measures.

---

## 🚀 Download & Installation

### Option 1: Pre-built Windows Executable (.exe)
1. Head over to the **[GitHub Releases](https://github.com/LazarusEffect-dotcom/All_Download/releases)** section.
2. Download `Youtube.exe` or `Youtube-Downloader-Windows-x64.zip` from release **v4.0.0**.
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
   git tag v4.0.0
   git push origin v4.0.0
   ```
2. **Or trigger manually via GitHub Actions**:
   - Go to your repository on GitHub.
   - Click on the **Actions** tab.
   - Select **Build and Release Windows Executable**.
   - Click **Run workflow**, specify the release tag (`v4.0.0`), and run.
