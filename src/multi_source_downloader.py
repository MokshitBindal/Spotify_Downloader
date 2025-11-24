"""
Multi-Source Download Manager
Manages downloading from multiple sources (Deezer, YouTube) with fallback.
"""

import logging
from typing import Dict, Optional, List
from pathlib import Path
import time
import random

logger = logging.getLogger(__name__)


class MultiSourceDownloader:
    """Manages downloading from multiple sources with priority and fallback."""
    
    def __init__(self, config: Dict):
        """
        Initialize multi-source downloader.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.sources = {}
        self.source_priority = config.get('download', {}).get('source_priority', ['deezer', 'youtube'])
        self.last_source = None  # Track which source was used
        
        # Initialize available sources
        self._initialize_sources()
    
    def _initialize_sources(self):
        """Initialize all available download sources."""
        # Try to initialize Internet Archive (FREE FLAC - legal!)
        ia_config = self.config.get('internetarchive', {})
        if ia_config.get('enabled', True):  # Enabled by default
            try:
                from .internetarchive_client import InternetArchiveClient
                
                self.sources['internetarchive'] = InternetArchiveClient(self.config)
                logger.info("✓ Internet Archive source initialized (Free legal FLAC)")
            except Exception as e:
                logger.warning(f"Failed to initialize Internet Archive source: {e}")
        
        # Try to initialize Jamendo (FREE - Creative Commons)
        jamendo_config = self.config.get('jamendo', {})
        if jamendo_config.get('enabled', True):  # Enabled by default
            try:
                from .jamendo_client import JamendoClient
                
                self.sources['jamendo'] = JamendoClient(self.config)
                logger.info("✓ Jamendo source initialized (Free Creative Commons)")
            except Exception as e:
                logger.warning(f"Failed to initialize Jamendo source: {e}")
        
        # Try to initialize Deezer/Deemix
        deezer_config = self.config.get('deezer', {})
        if deezer_config.get('enabled') and deezer_config.get('arl_token'):
            try:
                from .deemix_client import DeemixClient, DEEMIX_AVAILABLE
                
                if DEEMIX_AVAILABLE:
                    self.sources['deezer'] = DeemixClient(
                        deezer_config['arl_token'],
                        self.config
                    )
                    logger.info("✓ Deezer/Deemix source initialized (FLAC quality available)")
                else:
                    logger.warning("Deemix library not available. Install with: pip install deemix deezer-py")
            except Exception as e:
                logger.warning(f"Failed to initialize Deezer source: {e}")
        
        # Initialize YouTube downloader
        try:
            from .downloader import Downloader
            from .youtube_search import YouTubeSearcher
            
            self.sources['youtube'] = {
                'downloader': Downloader(self.config),
                'searcher': YouTubeSearcher(self.config)
            }
            logger.info("✓ YouTube source initialized")
        except Exception as e:
            logger.error(f"Failed to initialize YouTube source: {e}")
    
    def download(self, track: Dict, progress_callback=None) -> Optional[str]:
        """
        Download track from best available source.
        
        Args:
            track: Track metadata from Spotify
            progress_callback: Optional progress callback
            
        Returns:
            Path to downloaded file or None
        """
        # Try each source in priority order
        for source in self.source_priority:
            if source not in self.sources:
                continue
            
            try:
                logger.info(f"Attempting download from {source.upper()}")
                
                if source == 'internetarchive':
                    result = self._download_from_internetarchive(track)
                elif source == 'jamendo':
                    result = self._download_from_jamendo(track)
                elif source == 'deezer':
                    result = self._download_from_deezer(track)
                elif source == 'youtube':
                    result = self._download_from_youtube(track, progress_callback)
                else:
                    continue
                
                if result:
                    self.last_source = source  # Track which source was used
                    logger.info(f"✓ Successfully downloaded from {source.upper()}")
                    return result
                else:
                    logger.warning(f"✗ Download from {source.upper()} failed, trying next source...")
            
            except Exception as e:
                logger.error(f"Error downloading from {source}: {e}")
                continue
        
        logger.error(f"Failed to download from all sources: {track['artist']} - {track['name']}")
        return None
    
    def _download_from_internetarchive(self, track: Dict) -> Optional[str]:
        """
        Download from Internet Archive (free legal FLAC).
        
        Args:
            track: Track metadata
            
        Returns:
            Path to downloaded file or None
        """
        try:
            ia_client = self.sources.get('internetarchive')
            if not ia_client:
                return None
            
            # Search for track on Internet Archive
            ia_item = ia_client.search_track(track)
            if not ia_item:
                logger.warning("Track not found on Internet Archive")
                return None
            
            # Download
            output_dir = self.config.get('download', {}).get('output_dir', './downloads')
            output_path = ia_client.download_track(ia_item, output_dir, track)
            
            return output_path
        
        except Exception as e:
            logger.error(f"Internet Archive download error: {e}")
            return None
    
    def _download_from_jamendo(self, track: Dict) -> Optional[str]:
        """
        Download from Jamendo (free Creative Commons).
        
        Args:
            track: Track metadata
            
        Returns:
            Path to downloaded file or None
        """
        try:
            jamendo_client = self.sources.get('jamendo')
            if not jamendo_client:
                return None
            
            # Search for track on Jamendo
            jamendo_track = jamendo_client.search_track(track)
            if not jamendo_track:
                logger.warning("Track not found on Jamendo")
                return None
            
            # Download
            output_dir = self.config.get('download', {}).get('output_dir', './downloads')
            output_path = jamendo_client.download_track(jamendo_track, output_dir, track)
            
            return output_path
        
        except Exception as e:
            logger.error(f"Jamendo download error: {e}")
            return None
    
    def _download_from_deezer(self, track: Dict) -> Optional[str]:
        """
        Download from Deezer.
        
        Args:
            track: Track metadata
            
        Returns:
            Path to downloaded file or None
        """
        try:
            deemix_client = self.sources.get('deezer')
            if not deemix_client:
                return None
            
            # Search for track on Deezer
            deezer_track = deemix_client.search_track(track)
            if not deezer_track:
                logger.warning("Track not found on Deezer")
                return None
            
            # Download
            output_dir = self.config.get('download', {}).get('output_dir', './downloads')
            output_path = deemix_client.download_track(deezer_track, output_dir)
            
            return output_path
        
        except Exception as e:
            logger.error(f"Deezer download error: {e}")
            return None
    
    def _download_from_youtube(self, track: Dict, progress_callback=None) -> Optional[str]:
        """
        Download from YouTube with retry logic.
        
        Args:
            track: Track metadata
            progress_callback: Optional progress callback
            
        Returns:
            Path to downloaded file or None
        """
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                youtube = self.sources.get('youtube')
                if not youtube:
                    return None
                
                searcher = youtube['searcher']
                downloader = youtube['downloader']
                
                # Add small delay between attempts to avoid rate limiting
                if attempt > 0:
                    delay = random.uniform(1, 3)
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries} after {delay:.1f}s...")
                    time.sleep(delay)
                
                # Search for track on YouTube
                youtube_url = searcher.search(track, retry_count=attempt)
                if not youtube_url:
                    if attempt < max_retries - 1:
                        continue
                    logger.warning("Track not found on YouTube after retries")
                    return None
                
                # Download
                output_path = downloader.download(youtube_url, track, progress_callback)
                
                if output_path:
                    return output_path
                elif attempt < max_retries - 1:
                    continue
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"YouTube download attempt {attempt + 1} failed: {e}, retrying...")
                    continue
                else:
                    logger.error(f"YouTube download error after {max_retries} attempts: {e}")
        
        return None
    
    def get_available_sources(self) -> List[str]:
        """
        Get list of available sources.
        
        Returns:
            List of available source names
        """
        return list(self.sources.keys())
    
    def is_source_available(self, source: str) -> bool:
        """
        Check if a source is available.
        
        Args:
            source: Source name
            
        Returns:
            True if available, False otherwise
        """
        return source in self.sources
