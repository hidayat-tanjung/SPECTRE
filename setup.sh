#!/bin/bash
# SPECTRE v5.0 - Setup script
set -e

echo "════════════════════════════════════════════════════════════"
echo "  💀 SPECTRE v5.0 - Setup 💀"
echo "════════════════════════════════════════════════════════════"

# Check python
if ! command -v python3 &> /dev/null; then
    echo "❌ python3 not found"
    exit 1
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✅ Python $PY_VER"

# Folders
mkdir -p plugins logs reports docs

# Venv
if [ ! -d "venv" ]; then
    echo "[*] Creating virtualenv..."
    python3 -m venv venv
fi
source venv/bin/activate

# Pip
pip install --upgrade pip --quiet

# Deps
echo "[*] Installing dependencies..."
pip install -r requirements.txt

# Init
if [ ! -f "config.yaml" ]; then
    echo "[*] Creating default config..."
    python3 -c "
import yaml
cfg = {
  'general': {'version': '5.0.0', 'threads': 100, 'timeout': 8},
  'ai': {'enabled': False, 'provider': 'none'},
  'storage': {'driver': 'sqlite', 'sqlite': {'path': 'spectre.db'}},
  'c2': {},
  'web': {'host': '0.0.0.0', 'port': 5000, 'auth': {'enabled': True, 'users': {'admin': 'changeme'}}},
}
with open('config.yaml', 'w') as f:
    yaml.safe_dump(cfg, f)
"
fi

# Test
echo "[*] Testing import..."
python3 spectre.py --help >/dev/null 2>&1 && echo "✅ CLI OK" || echo "⚠️  CLI ada error, cek manual"

echo
echo "════════════════════════════════════════════════════════════"
echo "  ✅ Setup selesai!"
echo "════════════════════════════════════════════════════════════"
echo
echo "  Next:"
echo "    1. source venv/bin/activate"
echo "    2. python spectre.py --help"
echo "    3. python spectre.py --geoip 8.8.8.8"
echo