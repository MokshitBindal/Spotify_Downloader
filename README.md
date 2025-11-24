# Spotify Music Downloader

Download music from Spotify playlists with beautiful terminal UI and smart retry features.

## ✨ Features

- 🎵 **Multi-source downloads** from free legal sources (Internet Archive, Jamendo, YouTube)
- 📥 Download playlists, albums, tracks, or search by song name
- 🎧 Multiple formats (FLAC, MP3, WAV, M4A, OPUS) with quality selection
- 🎼 Automatic metadata & artwork embedding
- ⚡ Concurrent downloads (configurable)
- 🔄 Smart failed download tracking & retry system
- 🔍 Advanced song search (works with just song name or "Artist - Song")
- 💾 Organized downloads by artist/album

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- FFmpeg (`sudo apt install ffmpeg` on Ubuntu/Debian)

### Installation

```bash
git clone https://github.com/MokshitBindal/Spotify_Downloader.git
cd Spotify_Downloader
pip install -r requirements.txt
```

### First Run Setup

On first run, you'll be guided through an interactive setup to configure:

- Download folder location
- Preferred audio format (FLAC, MP3, etc.)
- Audio quality
- Number of concurrent downloads
- Metadata preferences

Just run any command and the wizard will start automatically!

## 📖 Usage

### Basic Commands

```bash
# Download playlist
python main.py --playlist https://open.spotify.com/playlist/xxxxx

# Download album
python main.py --album https://open.spotify.com/album/xxxxx

# Download single track
python main.py --track https://open.spotify.com/track/xxxxx

# Search and download by song name
python main.py --song "Metallica - Enter Sandman"
python main.py --song "Bohemian Rhapsody"  # Works even without artist

# Retry failed downloads
python main.py --retry-failed
```

### Advanced Options

```bash
# Custom format and quality
python main.py --playlist <url> --format flac --quality high

# Custom output folder
python main.py --playlist <url> --output ~/Music

# More concurrent downloads
python main.py --playlist <url> --concurrent 5
```

### Manage Preferences

```bash
# Show current preferences
python main.py --show-preferences

# Change download folder
python main.py --set-download-folder ~/Music/Spotify

# Reset all preferences (restart wizard)
python main.py --reset-preferences
```

## 🎯 How It Works

1. **Fetch Metadata**: Gets track info from Spotify API
2. **Multi-Source Search**: Searches across multiple free sources in priority order:
   - Internet Archive (archive.org) - Best quality FLAC
   - Jamendo - Creative Commons music
   - YouTube - Fallback (up to 256kbps)
3. **Smart Download**: Downloads from first available source
4. **Processing**: Converts to desired format using FFmpeg
5. **Metadata**: Embeds artist, title, album, artwork automatically
6. **Organization**: Saves in organized folder structure
7. **Tracking**: Remembers completed downloads and failed attempts

## 🎨 Features in Detail

### Beautiful Terminal UI

- Fixed-position progress bar with pacman animation
- Real-time download statistics
- Clean, non-scrolling updates
- Shows current track, source, format, and progress

### Smart Retry System

- Automatically tracks failed downloads with timestamps
- Retry any time with `--retry-failed`
- Failed list overwrites each run (only keeps most recent failures)
- Auto-removes from failed list when successfully downloaded

### Flexible Search

- Download by Spotify URL (playlist, album, track)
- Search by just song name: `"Enter Sandman"`
- Search with artist: `"Metallica - Enter Sandman"`
- Advanced Spotify query syntax for accurate matching

## 🛠️ Configuration

All preferences are stored in `.user_config.json` and can be:

- Set during first-run wizard
- Changed with `--set-download-folder`
- Reset with `--reset-preferences`
- Viewed with `--show-preferences`

Available settings:

- Download folder path
- Audio format (FLAC, MP3, WAV, M4A, OPUS)
- Quality (high, medium, low)
- Max concurrent downloads (1-10)
- Metadata embedding preferences

## 📝 Additional Files

- `.user_config.json` - Your preferences
- `.failed_downloads.json` - Failed tracks (with retry info)
- `.download_tracker.json` - Prevents re-downloading
- `config.yaml` - Spotify API credentials (create from config.yaml)


## 🐛 Troubleshooting

**FFmpeg not found**: Install with `sudo apt install ffmpeg`  
**No songs found**: Try different search terms or use Spotify URLs  
**Failed downloads**: Use `--retry-failed` to retry, or check `.failed_downloads.json`  
**Quality issues**: Internet Archive and Jamendo provide best quality (FLAC), YouTube is fallback

## 🤝 Contributing

Contributions welcome! This project uses:

- `spotipy` for Spotify API
- `yt-dlp` for YouTube downloads
- `mutagen` for metadata embedding
- `click` for CLI interface
