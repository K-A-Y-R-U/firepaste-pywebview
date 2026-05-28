#!/bin/bash
echo ""
echo "🔥 Instalando Firepaste Bot (PyWebView)..."
echo ""

# Dependencias del sistema para PyWebView en Fedora
sudo dnf install -y python3-pip python3-devel \
  webkit2gtk4.1 webkit2gtk4.1-devel \
  gobject-introspection gobject-introspection-devel \
  gtk3 gtk3-devel cairo-devel 2>/dev/null

# Python packages
pip3 install --user pywebview requests beautifulsoup4 playwright

# Chromium para Playwright
python3 -m playwright install chromium

# Dependencias sistema para Playwright
sudo dnf install -y nss atk at-spi2-atk cups-libs libdrm libxkbcommon \
  libXcomposite libXdamage libXrandr mesa-libgbm pango cairo alsa-lib gtk3 2>/dev/null

echo ""
echo "✅ Instalación completa!"
echo ""
echo "🚀 Abriendo Firepaste Bot..."
python3 main.py
