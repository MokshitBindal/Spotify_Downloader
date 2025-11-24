#!/usr/bin/env python3
"""
Setup script for Spotify Downloader
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip() 
        for line in requirements_file.read_text().splitlines()
        if line.strip() and not line.startswith('#')
    ]

setup(
    name="spotify-downloader",
    version="1.0.0",
    author="Mokshit Bindal",
    author_email="your-email@example.com",
    description="Download Spotify playlists, albums, and tracks in FLAC/MP3 format from free sources",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MokshitBindal/spotify-downloader",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Sound/Audio",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "spotify-downloader=main:main",
            "spotdl=main:main",  # Short alias
        ],
    },
    include_package_data=True,
    project_urls={
        "Bug Reports": "https://github.com/MokshitBindal/spotify-downloader/issues",
        "Source": "https://github.com/MokshitBindal/spotify-downloader",
        "Documentation": "https://github.com/MokshitBindal/spotify-downloader#readme",
    },
)
