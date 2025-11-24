"""
Enhanced Progress Display
Beautiful terminal output similar to pacman downloader.
"""

import sys
from typing import Optional
from datetime import datetime
import time


class ProgressDisplay:
    """Enhanced progress display for terminal."""
    
    def __init__(self, total_tracks: int = 0):
        self.start_time = time.time()
        self.current_track = ""
        self.total_tracks = total_tracks
        self.completed = 0
        self.failed = 0
        self.skipped = 0
        self.failed_tracks = []  # Track failed song names
        
    def print_header(self):
        """Print a beautiful header."""
        print("\n" + "=" * 70)
        print("  🎵  SPOTIFY MUSIC DOWNLOADER")
        print("=" * 70 + "\n")
    
    def print_source_info(self, sources: list):
        """Print available download sources."""
        source_icons = {
            'internetarchive': '📚',
            'jamendo': '🎹',
            'deezer': '🎼',
            'youtube': '📺',
            'soundcloud': '☁️',
            'bandcamp': '🎸'
        }
        
        source_labels = {
            'internetarchive': 'INTERNET ARCHIVE (FREE FLAC)',
            'jamendo': 'JAMENDO (FREE CC)',
            'deezer': 'DEEZER',
            'youtube': 'YOUTUBE',
            'soundcloud': 'SOUNDCLOUD',
            'bandcamp': 'BANDCAMP'
        }
        
        print("📡 Available Sources:")
        for i, source in enumerate(sources):
            icon = source_icons.get(source, '🔊')
            label = source_labels.get(source, source.upper())
            status = "✓ PRIMARY" if i == 0 else "✓ FALLBACK"
            print(f"   {icon}  {label:<30} {status}")
        print()
    
    def print_track_info(self, track_num: int, total: int, track: dict):
        """Print current track being processed - updates in place."""
        elapsed = time.time() - self.start_time
        rate = self.completed / elapsed if elapsed > 0 and self.completed > 0 else 0
        eta = (total - self.completed) / rate if rate > 0 else 0
        
        # Save cursor position, clear from cursor to end of screen
        sys.stdout.write('\033[s\033[J')
        
        # Track info - shown above progress bar
        artist = track['artist'][:40]
        title = track['name'][:50]
        print(f"🎵 Downloading: {artist} - {title}")
        
        # Progress bar - fixed position
        print(f"[{track_num:3d}/{total}] ", end='')
        print(f"{'█' * int((track_num/total) * 20)}", end='')
        print(f"{'░' * (20 - int((track_num/total) * 20))} ", end='')
        print(f"{(track_num/total)*100:5.1f}%", end='')
        
        print(f" │ ✓ {self.completed} │ ✗ {self.failed} │ ⊙ {self.skipped} ", end='')
        print(f"│ ⏱ {self._format_time(int(eta))}")
        
        # Restore cursor position
        sys.stdout.write('\033[u')
        sys.stdout.flush()
    
    def print_download_progress(self, source: str, percent: float, speed: str, eta: str):
        """Print download progress bar."""
        bar_length = 40
        filled = int(bar_length * percent / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        source_icons = {
            'internetarchive': '📚',
            'jamendo': '🎹',
            'deezer': '🎼',
            'youtube': '📺',
            'soundcloud': '☁️',
            'bandcamp': '🎸'
        }
        source_icon = source_icons.get(source, '🔊')
        
        print(f"   {source_icon} [{bar}] {percent:5.1f}% │ {speed:>10} │ ETA: {eta}", end='\r')
    
    def print_success(self, track_name: str, file_size: float, source: str):
        """Print success message - appears above progress bar."""
        self.completed += 1
        # Move to saved position, go up 2 lines, print result
        sys.stdout.write('\033[u\033[2A')
        source_icons = {'internetarchive': '📚', 'jamendo': '🎹', 'deezer': '🎼', 'youtube': '📺'}
        icon = source_icons.get(source, '🔊')
        print(f"{icon} ✓ {track_name[:55]:<55} [{file_size:.1f}MB]")
        # Move back to progress position
        sys.stdout.write('\033[2B')
        sys.stdout.flush()
    
    def print_skip(self, track_name: str, file_size: float):
        """Print skip message - appears above progress bar."""
        self.skipped += 1
        sys.stdout.write('\033[u\033[2A')
        print(f"⊙ {track_name[:60]} (exists)")
        sys.stdout.write('\033[2B')
        sys.stdout.flush()
    
    def print_error(self, track_name: str, error: str, track_info: dict = None):
        """Print error message - appears above progress bar."""
        self.failed += 1
        
        # Store detailed info for retry functionality
        if track_info:
            self.failed_tracks.append({
                'name': track_info.get('name'),
                'artist': track_info.get('artist'),
                'url': track_info.get('spotify_url')
            })
        else:
            # Fallback if no track info provided
            self.failed_tracks.append({'name': track_name})
        
        sys.stdout.write('\033[u\033[2A')
        print(f"✗ {track_name[:60]} (failed)")
        sys.stdout.write('\033[2B')
        sys.stdout.flush()
    
    def print_retry(self, attempt: int, max_attempts: int, source: str):
        """Print retry message."""
        print(f"   ⟳ Retry {attempt}/{max_attempts} via {source.upper()}...", end='')
        sys.stdout.flush()
    
    def print_summary(self, elapsed: float):
        """Print final summary."""
        print("\n" + "=" * 70)
        print("  📊 DOWNLOAD SUMMARY")
        print("=" * 70)
        
        total = self.completed + self.failed + self.skipped
        success_rate = (self.completed / total * 100) if total > 0 else 0
        
        print(f"\n  ✓ Completed:  {self.completed:3d}")
        print(f"  ✗ Failed:     {self.failed:3d}")
        print(f"  ⊙ Skipped:    {self.skipped:3d}")
        print(f"  ━━━━━━━━━━━━━━━━━")
        print(f"  ∑ Total:      {total:3d}")
        print(f"\n  Success Rate: {success_rate:.1f}%")
        print(f"  Time Elapsed: {self._format_time(elapsed)}")
        
        if self.completed > 0:
            avg_time = elapsed / self.completed
            print(f"  Avg per song: {avg_time:.1f}s")
        
        print("\n" + "=" * 70)
        
        # Show failed tracks if any
        if self.failed > 0 and self.failed_tracks:
            print(f"\n❌ Failed Downloads ({self.failed}):")
            print("─" * 70)
            for i, track in enumerate(self.failed_tracks, 1):
                print(f"  {i:2d}. {track}")
            print()
        
        print()
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds to human-readable time."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            mins = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds / 3600)
            mins = int((seconds % 3600) / 60)
            return f"{hours}h {mins}m"
