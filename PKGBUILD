# Maintainer: Mokshit Bindal <your-email@example.com>

pkgname=spotify-downloader
pkgver=1.0.0
pkgrel=1
pkgdesc="Download Spotify playlists, albums, and tracks in FLAC/MP3 format from free sources"
arch=('x86_64')
url="https://github.com/MokshitBindal/spotify-downloader"
license=('MIT')
depends=('python' 'python-pip' 'ffmpeg')
makedepends=('python-setuptools' 'python-build' 'python-installer' 'python-wheel')
optdepends=(
    'yt-dlp: YouTube download support'
    'python-spotipy: Spotify API access'
)
source=("${pkgname}-${pkgver}.tar.gz::https://github.com/MokshitBindal/${pkgname}/archive/v${pkgver}.tar.gz")
sha256sums=('SKIP')  # Update this after first release

build() {
    cd "${srcdir}/${pkgname}-${pkgver}"
    python -m build --wheel --no-isolation
}

package() {
    cd "${srcdir}/${pkgname}-${pkgver}"
    python -m installer --destdir="$pkgdir" dist/*.whl
    
    # Install documentation
    install -Dm644 README.md "${pkgdir}/usr/share/doc/${pkgname}/README.md"
    
    # Install license
    install -Dm644 LICENSE "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE"
}
