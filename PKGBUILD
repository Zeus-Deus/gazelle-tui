# Maintainer: Your Name <your.email@domain.com>
pkgname=gazelle-tui
pkgver=0.1.0
pkgrel=1
pkgdesc="Minimal NetworkManager TUI with complete 802.1X enterprise WiFi support"
arch=('any')
url="https://github.com/Zeus-Deus/gazelle-tui"
license=('MIT')
depends=('python' 'python-textual' 'networkmanager')
makedepends=('git')
source=("git+https://github.com/Zeus-Deus/gazelle-tui.git#tag=v${pkgver}")
sha256sums=('SKIP')

package() {
    cd "$srcdir/$pkgname"
    
    # Install the main script
    install -Dm755 gazelle "$pkgdir/usr/bin/gazelle"
    
    # Install Python modules
    install -Dm644 network.py "$pkgdir/usr/lib/python3.11/site-packages/gazelle_network.py"
    install -Dm644 app.py "$pkgdir/usr/lib/python3.11/site-packages/gazelle_app.py"
    
    # Install README
    install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
    
    # Install license
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
