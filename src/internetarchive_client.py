#!/usr/bin/env python3
"""
Internet Archive Music Downloader
Downloads FLAC music from Internet Archive (100% legal and free)
"""

import requests
import logging
from typing import Dict, List, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class InternetArchiveClient:
    """Client for downloading music from Internet Archive."""
    
    SEARCH_URL = "https://archive.org/advancedsearch.php"
    METADATA_URL = "https://archive.org/metadata"
    DOWNLOAD_URL = "https://archive.org/download"
    
    def __init__(self, config: Dict):
        """
        Initialize Internet Archive client.
        
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
        Search for a track on Internet Archive.
        
        Args:
            track: Track metadata from Spotify
            
        Returns:
            Internet Archive item dict or None
        """
        try:
            artist = track['artist']
            title = track['name']
            
            # Search Internet Archive for music matching the track
            query = f'({artist} AND {title}) AND collection:(etree OR audio) AND format:FLAC'
            
            params = {
                'q': query,
                'fl[]': ['identifier', 'title', 'creator', 'date', 'format'],
                'rows': 5,
                'page': 1,
                'output': 'json'
            }
            
            logger.info(f"Searching Internet Archive for: {artist} - {title}")
            response = self.session.get(self.SEARCH_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            docs = data.get('response', {}).get('docs', [])
            
            if not docs:
                logger.warning(f"No results found on Internet Archive for: {artist} - {title}")
                return None
            
            # Find best match
            best_match = self._find_best_match(track, docs)
            
            if best_match:
                logger.info(f"Found on Internet Archive: {best_match.get('title')}")
                return best_match
            
            return None
        
        except Exception as e:
            logger.error(f"Internet Archive search error: {e}")
            return None
    
    def _find_best_match(self, spotify_track: Dict, ia_results: List[Dict]) -> Optional[Dict]:
        """
        Find the best matching track from Internet Archive results.
        
        Args:
            spotify_track: Spotify track metadata
            ia_results: List of Internet Archive search results
            
        Returns:
            Best matching item or None
        """
        artist = spotify_track['artist'].lower()
        title = spotify_track['name'].lower()
        
        best_score = 0
        best_match = None
        
        for item in ia_results:
            score = 0
            
            item_title = item.get('title', '').lower()
            item_creator = item.get('creator', '').lower()
            
            # Check if artist name appears
            if artist in item_creator or artist in item_title:
                score += 50
            
            # Check if track title appears
            if title in item_title:
                score += 50
            
            # Prefer items with FLAC format
            formats = item.get('format', [])
            if isinstance(formats, list) and 'Flac' in formats:
                score += 20
            
            if score > best_score:
                best_score = score
                best_match = item
        
        # Only return if score is reasonable
        if best_score >= 60:
            return best_match
        
        return None
    
    def download_track(self, ia_item: Dict, output_dir: str, track: Dict) -> Optional[str]:
        """
        Download FLAC file from Internet Archive.
        
        Args:
            ia_item: Internet Archive item metadata
            output_dir: Output directory path
            track: Original Spotify track metadata
            
        Returns:
            Path to downloaded file or None
        """
        try:
            identifier = ia_item.get('identifier')
            if not identifier:
                logger.error("No identifier in Internet Archive item")
                return None
            
            # Get item metadata to find FLAC files
            metadata_url = f"{self.METADATA_URL}/{identifier}"
            response = self.session.get(metadata_url, timeout=10)
            response.raise_for_status()
            
            metadata = response.json()
            files = metadata.get('files', [])
            
            # Find FLAC file
            flac_file = None
            for file in files:
                if file.get('format') == 'Flac' or file.get('name', '').endswith('.flac'):
                    flac_file = file
                    break
            
            if not flac_file:
                logger.warning(f"No FLAC file found in {identifier}")
                return None
            
            filename = flac_file.get('name')
            download_url = f"{self.DOWNLOAD_URL}/{identifier}/{filename}"
            
            # Create output path
            artist = track['artist']
            title = track['name']
            output_path = Path(output_dir) / artist
            output_path.mkdir(parents=True, exist_ok=True)
            
            output_file = output_path / f"{artist} - {title}.flac"
            
            # Download file
            logger.info(f"Downloading from Internet Archive: {download_url}")
            
            response = self.session.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(output_file, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Log progress every 10%
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            if int(progress) % 10 == 0:
                                logger.debug(f"Download progress: {progress:.1f}%")
            
            logger.info(f"Downloaded from Internet Archive: {output_file}")
            return str(output_file)
        
        except Exception as e:
            logger.error(f"Internet Archive download error: {e}")
            return None
    
    def is_available(self) -> bool:
        """
        Check if Internet Archive is accessible.
        
        Returns:
            True if accessible, False otherwise
        """
        try:
            response = self.session.get("https://archive.org", timeout=5)
            return response.status_code == 200
        except:
            return False
