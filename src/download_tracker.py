"""
Download Progress Tracker
Tracks successfully downloaded files to avoid re-downloading.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Set
import logging

logger = logging.getLogger(__name__)


class DownloadTracker:
    """Tracks completed downloads to avoid re-downloading."""
    
    def __init__(self, output_dir: str):
        """
        Initialize download tracker.
        
        Args:
            output_dir: Base output directory
        """
        self.output_dir = Path(output_dir)
        self.tracker_file = self.output_dir / '.download_tracker.json'
        self.completed_tracks = self._load_tracker()
    
    def _load_tracker(self) -> Dict[str, Dict]:
        """Load tracking data from file."""
        if self.tracker_file.exists():
            try:
                with open(self.tracker_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load tracker file: {e}")
                return {}
        return {}
    
    def _save_tracker(self):
        """Save tracking data to file."""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            with open(self.tracker_file, 'w') as f:
                json.dump(self.completed_tracks, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save tracker file: {e}")
    
    def _get_track_id(self, track: Dict) -> str:
        """Generate unique ID for a track."""
        track_str = f"{track['artist']}|{track['name']}|{track['album']}"
        return hashlib.md5(track_str.encode()).hexdigest()
    
    def is_downloaded(self, track: Dict, file_path: Path) -> bool:
        """
        Check if track is already downloaded and complete.
        
        Args:
            track: Track metadata
            file_path: Expected file path
            
        Returns:
            True if already downloaded and complete
        """
        track_id = self._get_track_id(track)
        
        # Check if file exists
        if not file_path.exists():
            return False
        
        # Check tracker
        if track_id in self.completed_tracks:
            tracked_info = self.completed_tracks[track_id]
            file_size = file_path.stat().st_size
            
            # Verify file size matches
            if tracked_info.get('size') == file_size:
                logger.debug(f"Track found in tracker: {track['name']}")
                return True
            else:
                logger.warning(f"File size mismatch for {track['name']}, will re-download")
                return False
        
        return False
    
    def mark_downloaded(self, track: Dict, file_path: Path):
        """
        Mark track as successfully downloaded.
        
        Args:
            track: Track metadata
            file_path: Downloaded file path
        """
        track_id = self._get_track_id(track)
        
        self.completed_tracks[track_id] = {
            'artist': track['artist'],
            'name': track['name'],
            'album': track['album'],
            'file': str(file_path),
            'size': file_path.stat().st_size,
            'format': file_path.suffix[1:]
        }
        
        self._save_tracker()
        logger.debug(f"Marked as downloaded: {track['name']}")
    
    def remove_track(self, track: Dict):
        """
        Remove track from completed list.
        
        Args:
            track: Track metadata
        """
        track_id = self._get_track_id(track)
        if track_id in self.completed_tracks:
            del self.completed_tracks[track_id]
            self._save_tracker()
    
    def get_stats(self) -> Dict:
        """Get download statistics."""
        return {
            'total_downloaded': len(self.completed_tracks),
            'formats': self._count_formats()
        }
    
    def _count_formats(self) -> Dict[str, int]:
        """Count downloads by format."""
        formats = {}
        for track_info in self.completed_tracks.values():
            fmt = track_info.get('format', 'unknown')
            formats[fmt] = formats.get(fmt, 0) + 1
        return formats
