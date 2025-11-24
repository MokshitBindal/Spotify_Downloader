#!/usr/bin/env python3
"""
Spotify Music Downloader
Main entry point for the application.
Downloads Spotify playlists/albums/tracks in various formats including FLAC from Deezer.
"""

import sys
import click
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.spotify_client import SpotifyClient
from src.multi_source_downloader import MultiSourceDownloader
from src.metadata import MetadataEmbedder
from src.progress_display import ProgressDisplay
from src.user_config import UserConfigManager
from src.utils import (
    load_config, setup_logging, validate_spotify_url,
    check_ffmpeg, print_banner, ProgressTracker
)

logger = logging.getLogger('spotify_downloader')


@click.command()
@click.option('--playlist', '-p', help='Spotify playlist URL')
@click.option('--track', '-t', help='Spotify track URL')
@click.option('--album', '-a', help='Spotify album URL')
@click.option('--song', '-s', help='Search and download by song name (e.g., "Eminem - Beautiful Pain")')
@click.option('--retry-failed', is_flag=True, help='Retry previously failed downloads')
@click.option('--format', '-f', default=None, help='Audio format (mp3, flac, wav, m4a)')
@click.option('--quality', '-q', default=None, help='Audio quality for MP3 (128, 192, 256, 320)')
@click.option('--output', '-o', default=None, help='Output directory')
@click.option('--concurrent', '-c', default=None, type=int, help='Number of concurrent downloads')
@click.option('--no-metadata', is_flag=True, help='Skip metadata embedding')
@click.option('--no-artwork', is_flag=True, help='Skip artwork embedding')
@click.option('--config', default='config/config.yaml', help='Path to config file')
@click.option('--set-download-folder', help='Set default download folder')
@click.option('--show-preferences', is_flag=True, help='Show current user preferences')
@click.option('--reset-preferences', is_flag=True, help='Reset all user preferences')
def main(playlist, track, album, song, retry_failed, format, quality, output, concurrent, no_metadata, no_artwork, config, set_download_folder, show_preferences, reset_preferences):
    """
    Spotify Music Downloader - Download playlists, albums, or tracks from Spotify.
    
    Supports high-quality FLAC downloads from multiple free sources.
    First run will prompt you to set preferences (format, quality, download folder).
    
    Examples:
    
        \b
        # Download playlist (uses your preferences)
        python main.py --playlist <url>
        
        \b
        # Download by song name
        python main.py --song "Eminem - Beautiful Pain"
        
        \b
        # Retry failed downloads
        python main.py --retry-failed
        
        \b
        # Override format for this session
        python main.py --album <url> --format mp3 --quality 320
        
        \b
        # View/manage preferences
        python main.py --show-preferences
        python main.py --reset-preferences
        python main.py --set-download-folder ~/Music
    """
    print_banner()
    
    # Check FFmpeg
    if not check_ffmpeg():
        click.echo("❌ FFmpeg not found! Please install FFmpeg to continue.")
        click.echo("   Ubuntu/Debian: sudo apt-get install ffmpeg")
        click.echo("   macOS: brew install ffmpeg")
        click.echo("   Arch: sudo pacman -S ffmpeg")
        click.echo("   Windows: Download from https://ffmpeg.org/download.html")
        sys.exit(1)
    
    # Initialize user config manager
    user_config = UserConfigManager()
    
    # Handle preference commands
    if show_preferences:
        show_user_preferences(user_config)
        return
    
    if reset_preferences:
        if click.confirm("⚠️  Are you sure you want to reset all preferences?", default=False):
            user_config.reset()
            click.echo("✅ All preferences have been reset. Run again to reconfigure.")
        return
    
    if set_download_folder:
        user_config.set_download_folder(set_download_folder)
        return
    
    # Load configuration
    try:
        cfg = load_config(config)
    except Exception as e:
        click.echo(f"❌ Failed to load configuration: {e}")
        click.echo("   Make sure config/config.yaml exists and is valid")
        sys.exit(1)
    
    # Setup logging
    setup_logging(cfg)
    
    # Get download folder from user config (prompts on first run)
    if not output:
        default_folder = cfg['download'].get('output_dir', './downloads')
        cfg['download']['output_dir'] = user_config.get_download_folder(default_folder)
    
    # Apply user preferences (if not overridden by command line)
    if not format:
        cfg['download']['audio_format'] = user_config.get_preferred_format(
            cfg['download'].get('audio_format', 'flac')
        )
    
    if not quality:
        cfg['download']['audio_quality'] = user_config.get_preferred_quality(
            cfg['download'].get('audio_quality', '320')
        )
    
    if not concurrent:
        cfg['download']['max_concurrent'] = user_config.get_max_concurrent(
            cfg['download'].get('max_concurrent', 2)
        )
    
    if not no_metadata:
        cfg['metadata']['embed_metadata'] = user_config.get_embed_metadata(
            cfg['metadata'].get('embed_metadata', True)
        )
    
    if not no_artwork:
        cfg['metadata']['embed_artwork'] = user_config.get_embed_artwork(
            cfg['metadata'].get('embed_artwork', True)
        )
    
    # Override config with command line arguments (these take priority)
    if format:
        cfg['download']['audio_format'] = format
    if quality:
        cfg['download']['audio_quality'] = quality
    if output:
        cfg['download']['output_dir'] = output
    if concurrent:
        cfg['download']['max_concurrent'] = concurrent
    if no_metadata:
        cfg['metadata']['embed_metadata'] = False
    if no_artwork:
        cfg['metadata']['embed_artwork'] = False
    
    # Handle retry failed
    if retry_failed:
        retry_failed_downloads(cfg)
        return
    
    # Handle song name search
    if song:
        download_by_song_name(song, cfg)
        return
    
    # Validate input
    if not (playlist or track or album):
        click.echo("❌ Please provide a Spotify URL (--playlist, --track, --album)")
        click.echo("   Or use --song to search by name, or --retry-failed to retry")
        click.echo("   Use --help for more information")
        sys.exit(1)
    
    # Determine URL type
    url = playlist or track or album
    url_type = validate_spotify_url(url)
    
    if not url_type:
        click.echo("❌ Invalid Spotify URL")
        click.echo("   Expected format: https://open.spotify.com/playlist/xxxxx")
        sys.exit(1)
    
    try:
        # Initialize components
        click.echo("🔧 Initializing components...")
        
        # Initialize Spotify client
        try:
            spotify_client = SpotifyClient(
                cfg['spotify']['client_id'],
                cfg['spotify']['client_secret']
            )
        except Exception as e:
            click.echo(f"❌ Failed to initialize Spotify client: {e}")
            click.echo("   Please check your Spotify API credentials in config/config.yaml")
            click.echo("   Get credentials from: https://developer.spotify.com/dashboard")
            sys.exit(1)
        
        # Initialize multi-source downloader
        multi_downloader = MultiSourceDownloader(cfg)
        metadata_embedder = MetadataEmbedder(cfg)
        
        # Show available sources
        available_sources = multi_downloader.get_available_sources()
        if available_sources:
            sources_str = ', '.join([s.upper() for s in available_sources])
            click.echo(f"📡 Available sources: {sources_str}")
            
            # Show quality info
            if 'deezer' in available_sources and cfg['download']['audio_format'] == 'flac':
                click.echo("✨ FLAC quality enabled via Deezer (lossless)")
            elif cfg['download']['audio_format'] == 'flac':
                click.echo("⚠️  FLAC format selected but Deezer not configured")
                click.echo("   Will download from YouTube and convert to FLAC")
                click.echo("   For true lossless FLAC, configure Deezer in config.yaml")
        else:
            click.echo("⚠️  No download sources available")
            sys.exit(1)
        
        # Fetch tracks
        click.echo(f"🎵 Fetching {url_type} information...")
        
        if url_type == 'playlist':
            tracks = spotify_client.get_playlist_tracks(url)
        elif url_type == 'album':
            tracks = spotify_client.get_album_tracks(url)
        else:  # track
            tracks = [spotify_client.get_track(url)]
        
        if not tracks:
            click.echo("❌ No tracks found")
            sys.exit(1)
        
        click.echo(f"✅ Found {len(tracks)} track(s)")
        click.echo(f"📁 Output directory: {cfg['download']['output_dir']}")
        click.echo(f"🎼 Format: {cfg['download']['audio_format'].upper()}")
        
        if cfg['download']['audio_format'] == 'mp3':
            click.echo(f"🎚️  Quality: {cfg['download']['audio_quality']} kbps")
        
        click.echo()
        
        # Download tracks
        max_workers = cfg['download']['max_concurrent']
        delay_between = cfg['download'].get('delay_between_downloads', 1.5)
        
        # Initialize beautiful progress display
        display = ProgressDisplay(len(tracks))
        display.print_header()
        
        # Show available sources with their status
        source_status = {}
        for source in available_sources:
            source_status[source] = "ready"
        display.print_source_info(source_status)
        
        import time
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit download tasks with staggered delays
            future_to_track = {}
            for i, track in enumerate(tracks):
                # Stagger the initial submissions
                delay = i * (delay_between / max_workers)
                future = executor.submit(
                    download_track, 
                    track, 
                    multi_downloader, 
                    metadata_embedder, 
                    delay, 
                    i + 1, 
                    len(tracks), 
                    display,
                    start_time
                )
                future_to_track[future] = (track, i + 1)
            
            # Process completed downloads with beautiful progress display
            for future in as_completed(future_to_track):
                track, track_num = future_to_track[future]
                try:
                    result = future.result()
                    # Result is tuple: (success, source, file_size, skipped)
                    # Results are displayed in download_track function
                    pass
                except Exception as e:
                    logger.error(f"Error processing {track['name']}: {e}")
                    display.print_error(f"{track['artist']} - {track['name']}", str(e), track)
        
        # Print final summary
        elapsed_time = time.time() - start_time
        display.print_summary(elapsed_time)
        
        # Save failed tracks to JSON for retry functionality (overwrites previous run)
        import json
        from datetime import datetime
        failed_log = Path(cfg['download']['output_dir']) / '.failed_downloads.json'
        
        if display.failed_tracks:
            try:
                # Add metadata about this run
                failed_data = {
                    'timestamp': datetime.now().isoformat(),
                    'total_failed': len(display.failed_tracks),
                    'tracks': display.failed_tracks
                }
                with open(failed_log, 'w') as f:
                    json.dump(failed_data, f, indent=2)
                click.echo(f"\n⚠️  Failed tracks saved to: {failed_log}")
                click.echo(f"   Use --retry-failed to try downloading them again")
            except Exception as e:
                logger.error(f"Could not save failed tracks: {e}")
        else:
            # Clear failed downloads file if all succeeded
            try:
                if failed_log.exists():
                    failed_log.unlink()
            except Exception:
                pass
        
        if display.completed > 0:
            click.echo(f"\n💾 Files saved to: {cfg['download']['output_dir']}")
        
        if display.failed == len(tracks):
            click.echo("\n❌ All downloads failed. Please check the logs.")
            click.echo(f"   Log file: {cfg.get('logging', {}).get('file', 'downloads/download.log')}")
            sys.exit(1)
        elif display.failed > 0:
            click.echo("\n⚠️  Some downloads failed. Check the logs for details.")
    
    except KeyboardInterrupt:
        click.echo("\n\n⚠️  Download interrupted by user")
        click.echo("   Run the same command again to resume (existing files will be skipped)")
        sys.exit(0)
    except Exception as e:
        click.echo(f"\n❌ An error occurred: {e}")
        logger.exception("Fatal error")
        sys.exit(1)


def show_user_preferences(user_config: UserConfigManager):
    """Display current user preferences."""
    click.echo("\n" + "="*70)
    click.echo("  ⚙️   USER PREFERENCES")
    click.echo("="*70)
    
    if not user_config.config:
        click.echo("\n  No preferences set yet. Run a download to configure.")
    else:
        click.echo(f"\n  📁 Download Folder:    {user_config.config.get('download_folder', 'Not set')}")
        click.echo(f"  🎵 Preferred Format:   {user_config.config.get('preferred_format', 'Not set').upper()}")
        
        if user_config.config.get('preferred_quality'):
            click.echo(f"  🎚️  Preferred Quality:  {user_config.config.get('preferred_quality')} kbps")
        
        click.echo(f"  ⚡ Max Concurrent:     {user_config.config.get('max_concurrent', 'Not set')}")
        click.echo(f"  📝 Embed Metadata:     {'Yes' if user_config.config.get('embed_metadata', True) else 'No'}")
        click.echo(f"  🎨 Embed Artwork:      {'Yes' if user_config.config.get('embed_artwork', True) else 'No'}")
        
        click.echo("\n  To change preferences:")
        click.echo("    --reset-preferences    (reset all and reconfigure)")
        click.echo("    --set-download-folder  (change download location)")
        click.echo("    --format <format>      (override for this session)")
        click.echo("    --quality <quality>    (override for this session)")
    
    click.echo("="*70 + "\n")


def download_track(track, multi_downloader, metadata_embedder, delay, track_num, total_tracks, display, start_time):
    """
    Download a single track with progress display.
    
    Args:
        track: Track dictionary from Spotify
        multi_downloader: MultiSourceDownloader instance
        metadata_embedder: MetadataEmbedder instance
        delay: Delay before starting download (to avoid rate limiting)
        track_num: Current track number
        total_tracks: Total number of tracks
        display: ProgressDisplay instance
        start_time: Download start time
        
    Returns:
        Tuple (success, source, file_size, skipped)
    """
    import time
    import random
    from pathlib import Path
    
    try:
        # Add random delay to avoid rate limiting
        if delay > 0:
            actual_delay = delay + random.uniform(0, 1)
            time.sleep(actual_delay)
        
        # Show track info with progress (clean output)
        display.print_track_info(track_num, total_tracks, track)
        
        # Download from best available source
        # Suppress all logging during download for clean output
        original_level = logging.getLogger().level
        logging.getLogger().setLevel(logging.ERROR)
        
        audio_path = multi_downloader.download(track)
        
        # Restore logging
        logging.getLogger().setLevel(original_level)
        
        if not audio_path:
            logger.error(f"Download failed for: {track['name']}")
            display.print_error(f"{track['artist']} - {track['name']}", "Download failed", track)
            return (False, None, 0, False)
        
        # Convert string path to Path object
        audio_path_obj = Path(audio_path)
        
        # Check if it was already downloaded (skipped)
        from src.download_tracker import DownloadTracker
        from src.utils import load_config
        
        config = load_config('config/config.yaml')
        output_dir = config.get('download', {}).get('output_dir', './downloads')
        tracker = DownloadTracker(output_dir)
        skipped = tracker.is_downloaded(track, audio_path_obj)
        
        if skipped:
            file_size = audio_path_obj.stat().st_size / (1024 * 1024)  # MB
            display.print_skip(f"{track['artist']} - {track['name']}", file_size)
            return (True, "cached", file_size, True)
        
        # Embed metadata (if not already embedded by source)
        if metadata_embedder.embed_metadata:
            metadata_embedder.embed(str(audio_path_obj), track)
        
        # Get file size and source
        file_size = audio_path_obj.stat().st_size / (1024 * 1024)  # MB
        source = getattr(multi_downloader, 'last_source', 'unknown')
        
        display.print_success(f"{track['artist']} - {track['name']}", file_size, source)
        
        # Mark as downloaded
        tracker.mark_downloaded(track, audio_path_obj)
        
        return (True, source, file_size, False)
    
    except Exception as e:
        logger.error(f"Error downloading {track['name']}: {e}")
        display.print_error(f"{track['artist']} - {track['name']}", str(e), track)
        return (False, None, 0, False)


def download_by_song_name(song_query: str, config: dict):
    """
    Download a song by searching its name.
    
    Args:
        song_query: Song name query (e.g., "Eminem - Beautiful Pain")
        config: Configuration dictionary
    """
    click.echo(f"🔍 Searching for: {song_query}")
    
    try:
        # Initialize Spotify client
        spotify_client = SpotifyClient(
            config['spotify']['client_id'],
            config['spotify']['client_secret']
        )
        
        # Parse artist and song if format is "Artist - Song"
        if ' - ' in song_query:
            parts = song_query.split(' - ', 1)
            search_query = f'track:{parts[1]} artist:{parts[0]}'
        else:
            search_query = f'track:{song_query}'
        
        # Search for the track with better filtering
        results = spotify_client.sp.search(q=search_query, type='track', limit=10)
        
        if not results['tracks']['items']:
            click.echo(f"❌ No results found for: {song_query}")
            return
        
        # Show results with more details
        click.echo("\n🎵 Found tracks:")
        for i, item in enumerate(results['tracks']['items'], 1):
            artist = item['artists'][0]['name']
            name = item['name']
            album = item['album']['name']
            year = item['album']['release_date'][:4] if item['album'].get('release_date') else '????'
            duration_ms = item['duration_ms']
            duration_str = f"{duration_ms // 60000}:{(duration_ms % 60000) // 1000:02d}"
            
            # Truncate long names
            artist_display = artist[:25] + '...' if len(artist) > 25 else artist
            name_display = name[:30] + '...' if len(name) > 30 else name
            album_display = album[:30] + '...' if len(album) > 30 else album
            
            click.echo(f"  {i:2d}. {artist_display:<28} - {name_display:<33} [{year}] ({duration_str}) [from: {album_display}]")
        
        # Ask user to select
        choice = click.prompt("\nSelect track number (or 0 to cancel)", type=int, default=1)
        
        if choice == 0 or choice > len(results['tracks']['items']):
            click.echo("Cancelled.")
            return
        
        selected_track = results['tracks']['items'][choice - 1]
        track_url = selected_track['external_urls']['spotify']
        
        # Download the selected track
        click.echo(f"\n✅ Downloading: {selected_track['artists'][0]['name']} - {selected_track['name']}")
        
        # Initialize downloaders
        multi_downloader = MultiSourceDownloader(config)
        metadata_embedder = MetadataEmbedder(config)
        display = ProgressDisplay(1)
        
        display.print_header()
        available_sources = multi_downloader.get_available_sources()
        display.print_source_info(available_sources)
        
        # Format track data
        track = spotify_client.get_track(track_url)
        
        # Download
        import time
        start_time = time.time()
        result = download_track(track, multi_downloader, metadata_embedder, 0, 1, 1, display, start_time)
        
        elapsed = time.time() - start_time
        display.print_summary(elapsed)
        
        if result[0]:
            click.echo(f"💾 File saved to: {config['download']['output_dir']}")
        else:
            click.echo("❌ Download failed")
    
    except Exception as e:
        click.echo(f"❌ Error: {e}")
        logger.exception("Song search error")


def retry_failed_downloads(config: dict):
    """
    Retry previously failed downloads.
    
    Args:
        config: Configuration dictionary
    """
    # Check for failed downloads log
    failed_log = Path(config['download']['output_dir']) / '.failed_downloads.json'
    
    if not failed_log.exists():
        click.echo("❌ No failed downloads found to retry")
        click.echo("   (Failed downloads are tracked after you run a playlist download)")
        return
    
    import json
    
    try:
        with open(failed_log, 'r') as f:
            failed_data = json.load(f)
        
        # Handle both old format (list) and new format (dict with metadata)
        if isinstance(failed_data, dict) and 'tracks' in failed_data:
            failed_tracks = failed_data['tracks']
            timestamp = failed_data.get('timestamp', 'Unknown')
            click.echo(f"\n📅 Failed downloads from: {timestamp}")
        else:
            # Old format compatibility
            failed_tracks = failed_data if isinstance(failed_data, list) else []
        
        if not failed_tracks:
            click.echo("✅ No failed downloads to retry!")
            return
        
        click.echo(f"\n🔄 Found {len(failed_tracks)} failed download(s):\n")
        for i, track in enumerate(failed_tracks, 1):
            click.echo(f"  {i}. {track.get('artist')} - {track.get('name')}")
        
        if not click.confirm(f"\nRetry all {len(failed_tracks)} tracks?", default=True):
            return
        
        # Initialize components
        spotify_client = SpotifyClient(
            config['spotify']['client_id'],
            config['spotify']['client_secret']
        )
        multi_downloader = MultiSourceDownloader(config)
        metadata_embedder = MetadataEmbedder(config)
        display = ProgressDisplay(len(failed_tracks))
        
        display.print_header()
        available_sources = multi_downloader.get_available_sources()
        display.print_source_info(available_sources)
        
        import time
        start_time = time.time()
        
        successfully_retried = []
        
        # Try downloading each failed track
        for i, track_info in enumerate(failed_tracks, 1):
            track_url = track_info.get('url')
            if not track_url:
                continue
            
            try:
                track = spotify_client.get_track(track_url)
                result = download_track(track, multi_downloader, metadata_embedder, 0, i, len(failed_tracks), display, start_time)
                
                if result[0]:
                    successfully_retried.append(track_info)
            except Exception as e:
                logger.error(f"Retry failed for {track_info.get('name')}: {e}")
        
        elapsed = time.time() - start_time
        display.print_summary(elapsed)
        
        # Update failed log with new format
        remaining_failed = [t for t in failed_tracks if t not in successfully_retried]
        if remaining_failed:
            from datetime import datetime
            failed_data = {
                'timestamp': datetime.now().isoformat(),
                'total_failed': len(remaining_failed),
                'tracks': remaining_failed
            }
            with open(failed_log, 'w') as f:
                json.dump(failed_data, f, indent=2)
        else:
            # Delete file if no more failed tracks
            if failed_log.exists():
                failed_log.unlink()
        
        click.echo(f"\n✅ Successfully retried: {len(successfully_retried)} / {len(failed_tracks)}")
        click.echo(f"💾 Files saved to: {config['download']['output_dir']}")
        
        if remaining_failed:
            click.echo(f"⚠️  Still failed: {len(remaining_failed)} tracks")
    
    except Exception as e:
        click.echo(f"❌ Error reading failed downloads: {e}")
        logger.exception("Retry failed downloads error")


if __name__ == '__main__':
    main()
