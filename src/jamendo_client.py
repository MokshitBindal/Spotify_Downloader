#!/usr/bin/env python3
"""
Jamendo Music Downloader
Downloads music from Jamendo (Creative Commons, legal and free)
"""

import requests
import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class JamendoClient:
    """Client for downloading music from Jamendo (Creative Commons)."""
    
    API_BASE = "https://api.jamendo.com/v3.0"
    CLIENT_ID = "56d30c95"  # Public API key (can be used by anyone)
    
    def __init__(self, config: Dict):
        """
        Initialize Jamendo client.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; SpotifyMusicDownloader/1.0)'
        })
    
    def search_track(self, track: Dict) -> Optional[Dict]:
        """
        Search for a track on Jamendo.
        
        Args:
            track: Track metadata from Spotify
            
        Returns:
            Jamendo track dict or None
        """
        try:
            artist = track['artist']
            title = track['name']
            
            # Search Jamendo
            search_url = f"{self.API_BASE}/tracks"
            params = {
                'client_id': self.CLIENT_ID,
                'format': 'json',
                'limit': 5,
                'search': f"{artist} {title}",
                'include': 'musicinfo',
                'audioformat': 'flac'
            }
            
            logger.info(f"Searching Jamendo for: {artist} - {title}")
            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = data.get('results', [])
            
            if not results:
                logger.warning(f"No results found on Jamendo for: {artist} - {title}")
                return None
            
            # Find best match
            best_match = self._find_best_match(track, results)
            
            if best_match:
                logger.info(f"Found on Jamendo: {best_match.get('name')}")
                return best_match
            
            return None
        
        except Exception as e:
            logger.error(f"Jamendo search error: {e}")
            return None
    
    def _find_best_match(self, spotify_track: Dict, jamendo_results: List[Dict]) -> Optional[Dict]:
        """
        Find the best matching track from Jamendo results.
        
        Args:
            spotify_track: Spotify track metadata
            jamendo_results: List of Jamendo search results
            
        Returns:
            Best matching track or None
        """
        artist = spotify_track['artist'].lower()
        title = spotify_track['name'].lower()
        
        best_score = 0
        best_match = None
        
        for result in jamendo_results:
            score = 0
            
            result_artist = result.get('artist_name', '').lower()
            result_title = result.get('name', '').lower()
            
            # Exact artist match
            if artist == result_artist:
                score += 50
            elif artist in result_artist or result_artist in artist:
                score += 30
            
            # Exact title match
            if title == result_title:
                score += 50
            elif title in result_title or result_title in title:
                score += 30
            
            # Check duration match (within 10 seconds)
            if 'duration_ms' in spotify_track:
                spotify_duration = spotify_track['duration_ms'] / 1000
                jamendo_duration = result.get('duration', 0)
                
                duration_diff = abs(spotify_duration - jamendo_duration)
                if duration_diff <= 10:
                    score += 20
            
            if score > best_score:
                best_score = score
                best_match = result
        
        # Only return if score is reasonable
        if best_score >= 60:
            return best_match
        
        return None
    
    def download_track(self, jamendo_track: Dict, output_dir: str, track: Dict) -> Optional[str]:
        """
        Download track from Jamendo.
        
        Args:
            jamendo_track: Jamendo track metadata
            output_dir: Output directory path
            track: Original Spotify track metadata
            
        Returns:
            Path to downloaded file or None
        """
        try:
            track_id = jamendo_track.get('id')
            if not track_id:
                logger.error("No track ID in Jamendo result")
                return None
            
            # Get download URL
            download_url = f"{self.API_BASE}/tracks/file"
            params = {
                'client_id': self.CLIENT_ID,
                'id': track_id,
                'audioformat': 'flac'
            }
            
            # Create output path
            artist = track['artist']
            title = track['name']
            output_path = Path(output_dir) / artist
            output_path.mkdir(parents=True, exist_ok=True)
            
            output_file = output_path / f"{artist} - {title}.flac"
            
            # Download file
            logger.info(f"Downloading from Jamendo: {jamendo_track.get('name')}")
            
            response = self.session.get(download_url, params=params, stream=True, timeout=30)
            response.raise_for_status()
            
            # Check if we got actual audio or redirect
            content_type = response.headers.get('content-type', '')
            if 'audio' not in content_type:
                logger.warning("Jamendo did not return audio file (might not be available in FLAC)")
                return None
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(output_file, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
            
            # Verify file size
            if output_file.stat().st_size < 100000:  # Less than 100KB
                logger.warning("Downloaded file too small, probably not valid")
                output_file.unlink()
                return None
            
            logger.info(f"Downloaded from Jamendo: {output_file}")
            return str(output_file)
        
        except Exception as e:
            logger.error(f"Jamendo download error: {e}")
            return None
    
    def is_available(self) -> bool:
        """
        Check if Jamendo is accessible.
        
        Returns:
            True if accessible, False otherwise
        """
        try:
            response = self.session.get(f"{self.API_BASE}/tracks", params={'client_id': self.CLIENT_ID, 'limit': 1}, timeout=5)
            return response.status_code == 200
        except:
            return False
