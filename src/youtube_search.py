"""
YouTube Search Module
Searches YouTube for tracks matching Spotify metadata.
"""

import yt_dlp
from typing import Optional, Dict, List
import logging
import time
import random

logger = logging.getLogger(__name__)


class YouTubeSearcher:
    """Searches YouTube for matching audio tracks."""
    
    def __init__(self, config: Dict):
        """
        Initialize YouTube searcher.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.search_format = config.get('youtube', {}).get('search_query_format', '{artist} {title} audio')
        self.max_results = config.get('youtube', {}).get('max_results', 5)
        self.prefer_official = config.get('youtube', {}).get('prefer_official', True)
        self.min_duration_match = config.get('youtube', {}).get('min_duration_match', 0.9)
        self.max_duration_match = config.get('youtube', {}).get('max_duration_match', 1.1)
    
    def search(self, track: Dict, retry_count: int = 0) -> Optional[str]:
        """
        Search YouTube for a track with retry logic.
        
        Args:
            track: Track dictionary from Spotify
            retry_count: Current retry attempt
            
        Returns:
            YouTube video URL or None
        """
        query = self._build_search_query(track)
        logger.info(f"Searching YouTube for: {query}")
        
        # Add random delay to avoid rate limiting
        if retry_count > 0:
            delay = random.uniform(2, 5) * retry_count
            logger.info(f"Retry attempt {retry_count}, waiting {delay:.1f}s...")
            time.sleep(delay)
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'format': 'bestaudio/best',
            'socket_timeout': 30,
            'retries': 3,
            'nocheckcertificate': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_results = ydl.extract_info(f"ytsearch{self.max_results}:{query}", download=False)
                
                if not search_results or 'entries' not in search_results:
                    logger.warning(f"No YouTube results found for: {query}")
                    return None
                
                # Find best match
                best_match = self._find_best_match(track, search_results['entries'])
                
                if best_match:
                    video_url = f"https://www.youtube.com/watch?v={best_match['id']}"
                    logger.info(f"Found match: {best_match['title']}")
                    return video_url
                
                logger.warning(f"No suitable match found for: {query}")
                return None
        
        except Exception as e:
            logger.error(f"YouTube search failed: {e}")
            return None
    
    def _build_search_query(self, track: Dict) -> str:
        """
        Build search query from track metadata.
        
        Args:
            track: Track dictionary
            
        Returns:
            Search query string
        """
        query = self.search_format.format(
            artist=track['artist'],
            title=track['name'],
            album=track['album']
        )
        return query
    
    def _find_best_match(self, track: Dict, results: List[Dict]) -> Optional[Dict]:
        """
        Find the best matching video from search results.
        
        Args:
            track: Track dictionary from Spotify
            results: List of YouTube search results
            
        Returns:
            Best matching result or None
        """
        track_duration = track['duration_ms'] / 1000  # Convert to seconds
        scored_results = []
        
        for result in results:
            if not result:
                continue
            
            score = 0
            
            # Check duration match
            video_duration = result.get('duration', 0)
            if video_duration:
                duration_ratio = video_duration / track_duration
                if self.min_duration_match <= duration_ratio <= self.max_duration_match:
                    score += 50
                    # Closer match = higher score
                    score += max(0, 20 - abs(video_duration - track_duration))
            
            # Prefer official uploads
            if self.prefer_official:
                title_lower = result.get('title', '').lower()
                uploader_lower = result.get('uploader', '').lower()
                artist_lower = track['artist'].lower()
                
                if 'official' in title_lower or 'official' in uploader_lower:
                    score += 30
                if artist_lower in uploader_lower:
                    score += 20
                if 'vevo' in uploader_lower:
                    score += 15
            
            # Check title relevance
            title = result.get('title', '').lower()
            track_name = track['name'].lower()
            artist_name = track['artist'].lower()
            
            if track_name in title:
                score += 25
            if artist_name in title:
                score += 25
            
            # Avoid live versions, remixes, covers (unless original is)
            if 'original' not in track_name.lower():
                if any(word in title for word in ['live', 'remix', 'cover', 'karaoke', 'instrumental']):
                    score -= 30
            
            scored_results.append((score, result))
        
        # Sort by score and return best match
        if scored_results:
            scored_results.sort(key=lambda x: x[0], reverse=True)
            best_score, best_result = scored_results[0]
            
            # Only return if score is reasonable
            if best_score > 30:
                return best_result
        
        return None
    
    def get_video_info(self, url: str) -> Optional[Dict]:
        """
        Get detailed information about a YouTube video.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Video information dictionary or None
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return None
