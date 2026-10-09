# Universal Video Downloader Pro

A modern, high-performance desktop video & audio downloader application for Windows built with Python, CustomTkinter, and `yt-dlp`.

![Platform](https://img.shields.io/badge/Platform-Windows-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11%2B-brightgreen.svg)
![Release](https://img.shields.io/badge/Release-Executable%20(.exe)-red.svg)

---

## Features

- **Modern Dark Theme UI**: Built with CustomTkinter for sleek, native-feeling Windows design.
- **Universal Downloader**: Powered by `yt-dlp`, supporting YouTube, playlists, channels, and 1000+ streaming sites.
- **Standalone Portable `.exe`**: Single-file executable with embedded FFmpeg for automatic audio extraction and video muxing. No external tools or Python installation needed by end users!
- **Format Flexibility**:
  - Video: 4K, 2K, 1080p, 720p, 480p, 360p (MP4, MKV, WebM)
  - Audio: MP3 (320kbps, 256kbps, 192kbps, 128kbps), M4A, WAV, FLAC
- **Subtitles & Metadata**: Optional subtitle download, chapter extraction, and thumbnail embedding.
- **Browser Cookies & Auth**: Support for auto-detecting browser cookies (Chrome, Edge, Firefox, Brave, Opera, Vivaldi) or custom `cookies.txt` for age-restricted/member-only content.
- **Download History & Analytics**: Built-in history viewer and management.

---

## 🚀 Download & Installation

### Option 1: Pre-built Windows Executable (.exe)
1. Head over to the **[GitHub Releases](https://github.com/LazarusEffect-dotcom/All_Download/releases)** section.
2. Download the latest `Youtube.exe` or `Youtube-Downloader-Windows-x64.zip`.
3. Run the executable directly. No installer or dependencies required.

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
   git tag v3.0.0
   git push origin v3.0.0
   ```
2. **Or trigger manually via GitHub Actions**:
   - Go to your repository on GitHub.
   - Click on the **Actions** tab.
   - Select **Build and Release Windows Executable**.
   - Click **Run workflow**, specify the release tag (e.g., `v3.0.0`), and run.
3. The workflow will:
   - Install dependencies and prepare FFmpeg binaries.
   - Build the standalone `.exe` via PyInstaller.
   - Generate SHA-256 checksums and zip packages.
   - Publish the release to GitHub Releases with downloadable assets attached.
