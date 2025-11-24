"""
User Configuration Manager
Handles persistent user settings like download folder preferences.
"""

import json
from pathlib import Path
from typing import Optional
import click


class UserConfigManager:
    """Manages user-specific configuration."""
    
    def __init__(self, config_file: str = ".user_config.json"):
        """
        Initialize user config manager.
        
        Args:
            config_file: Path to user config file (relative to project root)
        """
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load user configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_config(self):
        """Save user configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            click.echo(f"⚠️  Warning: Could not save user preferences: {e}")
    
    def get_download_folder(self, default: str = "./downloads") -> str:
        """
        Get the user's preferred download folder.
        Prompts user on first run or if not set.
        
        Args:
            default: Default download folder
            
        Returns:
            Download folder path
        """
        if 'download_folder' in self.config:
            return self.config['download_folder']
        
        # First time setup
        self._first_time_setup(default)
        
        return self.config.get('download_folder', default)
    
    def _first_time_setup(self, default_folder: str = "./downloads"):
        """Run first time setup wizard to configure user preferences."""
        click.echo("\n" + "="*70)
        click.echo("  🎵  FIRST TIME SETUP")
        click.echo("="*70)
        
        # Download folder
        click.echo(f"\n📁 Where would you like to save downloaded music?")
        click.echo(f"   Default: {default_folder}")
        
        folder = click.prompt(
            "\nEnter download folder path (or press Enter for default)",
            default=default_folder,
            type=str
        )
        
        # Expand user home directory
        folder = str(Path(folder).expanduser())
        Path(folder).mkdir(parents=True, exist_ok=True)
        self.config['download_folder'] = folder
        
        # Audio format preference
        click.echo(f"\n🎵 What audio format do you prefer?")
        click.echo("   Options: flac (lossless), mp3, m4a, wav")
        
        audio_format = click.prompt(
            "\nEnter preferred format",
            default="flac",
            type=click.Choice(['flac', 'mp3', 'm4a', 'wav'], case_sensitive=False)
        )
        self.config['preferred_format'] = audio_format.lower()
        
        # Quality preference for lossy formats
        if audio_format.lower() == 'mp3':
            click.echo(f"\n🎚️  What MP3 quality do you prefer?")
            click.echo("   Options: 128, 192, 256, 320 (kbps)")
            
            quality = click.prompt(
                "\nEnter preferred quality",
                default="320",
                type=click.Choice(['128', '192', '256', '320'])
            )
            self.config['preferred_quality'] = quality
        
        # Concurrent downloads
        click.echo(f"\n⚡ How many songs to download simultaneously?")
        click.echo("   Recommended: 2-4 (higher values may cause rate limiting)")
        
        concurrent = click.prompt(
            "\nEnter number of concurrent downloads",
            default=2,
            type=click.IntRange(1, 10)
        )
        self.config['max_concurrent'] = concurrent
        
        # Metadata preferences
        click.echo(f"\n📝 Do you want to embed metadata (artist, album, artwork)?")
        embed_metadata = click.confirm(
            "Embed metadata",
            default=True
        )
        self.config['embed_metadata'] = embed_metadata
        
        if embed_metadata:
            embed_artwork = click.confirm(
                "Embed album artwork",
                default=True
            )
            self.config['embed_artwork'] = embed_artwork
        else:
            self.config['embed_artwork'] = False
        
        # Save all preferences
        self._save_config()
        
        # Summary
        click.echo("\n" + "="*70)
        click.echo("  ✅  SETUP COMPLETE")
        click.echo("="*70)
        click.echo(f"\n  📁 Download Folder:    {folder}")
        click.echo(f"  🎵 Audio Format:       {audio_format.upper()}")
        if audio_format.lower() == 'mp3':
            click.echo(f"  🎚️  Quality:            {quality} kbps")
        click.echo(f"  ⚡ Concurrent:         {concurrent} downloads")
        click.echo(f"  📝 Metadata:           {'Yes' if embed_metadata else 'No'}")
        if embed_metadata:
            click.echo(f"  🎨 Artwork:            {'Yes' if self.config['embed_artwork'] else 'No'}")
        click.echo("\n  You can change these anytime with:")
        click.echo("    --set-download-folder <path>")
        click.echo("    --format <format>")
        click.echo("    --quality <quality>")
        click.echo("    --concurrent <num>")
        click.echo("="*70 + "\n")
    
    def get_preferred_format(self, default: str = "flac") -> str:
        """Get user's preferred audio format."""
        return self.config.get('preferred_format', default)
    
    def get_preferred_quality(self, default: str = "320") -> str:
        """Get user's preferred audio quality for lossy formats."""
        return self.config.get('preferred_quality', default)
    
    def get_max_concurrent(self, default: int = 2) -> int:
        """Get user's preferred number of concurrent downloads."""
        return self.config.get('max_concurrent', default)
    
    def get_embed_metadata(self, default: bool = True) -> bool:
        """Get user's preference for metadata embedding."""
        return self.config.get('embed_metadata', default)
    
    def get_embed_artwork(self, default: bool = True) -> bool:
        """Get user's preference for artwork embedding."""
        return self.config.get('embed_artwork', default)
    
    def set_download_folder(self, folder: str):
        """
        Set a new download folder.
        
        Args:
            folder: New download folder path
        """
        folder = str(Path(folder).expanduser())
        Path(folder).mkdir(parents=True, exist_ok=True)
        
        self.config['download_folder'] = folder
        self._save_config()
        
        click.echo(f"✅ Download folder updated to: {folder}")
    
    def get(self, key: str, default=None):
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value):
        """Set a configuration value."""
        self.config[key] = value
        self._save_config()
    
    def reset(self):
        """Reset all user configuration."""
        self.config = {}
        if self.config_file.exists():
            self.config_file.unlink()
        click.echo("✅ User configuration reset")
