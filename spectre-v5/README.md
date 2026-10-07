# 💀 SPECTRE v5.0 — Singularity Edition

```
 ███████╗██████╗ ███████╗ ██████╗████████╗██████╗ ███████╗
 ██╔════╝██╔══██╗██╔════╝██╔════╝╚══██╔══╝██╔══██╗██╔════╝
 ███████╗██████╔╝█████╗  ██║        ██║   ██████╔╝█████╗  
 ╚════██║██╔═══╝ ██╔══╝  ██║        ██║   ██╔══██╗██╔══╝  
 ███████║██║     ███████╗╚██████╗   ██║   ██║  ██║███████╗
 ╚══════╝╚═╝     ╚══════╝ ╚═════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝
```

**Offensive Security Framework — AI-Powered**

- 🔥 **26 Modul** — Recon, Attack, Exploit
- 🤖 **AI Layer** — Ollama / OpenAI / Anthropic
- 📡 **Multi-Channel C2** — Telegram, Discord, TCP, Dead-Drop
- 🌐 **Web UI** — Real-time dashboard (FastAPI + WebSocket)
- 🐳 **Docker Ready**
- 🔌 **Plugin System**
- 💾 **Multi-DB** — SQLite / PostgreSQL
- ⚡ **Async Recon**

👻 **Author:** イズミー (IZUMI)  
📅 **Year:** 2050  
📜 **License:** For authorized security testing only

---

## 📑 DAFTAR ISI

1. [Fitur](#1-fitur)
2. [Instalasi Cepat](#2-instalasi-cepat)
3. [Struktur Project](#3-struktur-project)
4. [Cara Pakai](#4-cara-pakai)
5. [Modul Lengkap](#5-modul-lengkap)
6. [Konfigurasi](#6-konfigurasi)
7. [Docker](#7-docker)
8. [Legal](#8-legal)

---

## 1. FITUR

### 🔍 Recon (15 modul)
`geoip` `breach` `darkweb` `phone` `port` `whois` `dns` `subdomain`
`email` `ssl` `social` `tech` `dir` `async` `shodan`

### 💀 Attack (7 modul)
`sqli` `backdoor` `ransomware` `phishing` `crypto` `wifi` `dns-spoof`

### 💥 Exploit (4 modul)
`yara` `msf` `evasion` `autopwn`

---

## 2. INSTALASI CEPAT

```bash
# Clone / extract
cd spectre-v5

# Setup otomatis
chmod +x setup.sh
./setup.sh

# Test
python spectre.py --help
```

### Manual

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python spectre.py --init
```

---

## 3. STRUKTUR PROJECT

```
spectre-v5/
├── spectre.py           # CLI entry
├── core.py              # Config, storage, crypto, utils
├── ai_layer.py          # LLM integration
├── c2.py                # Multi-channel C2
├── persistence.py       # Persistence modules
├── plugin_loader.py     # Plugin + Evasion
├── modules.py           # 26 modul
├── web.py               # Web UI
├── config.yaml
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── setup.sh
├── README.md
├── plugins/
│   └── example_plugin.py
├── docs/
│   └── SETUP.md
├── logs/
└── spectre.db
```

---

## 4. CARA PAKAI

### Recon

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
python spectre.py --async example.com
python spectre.py --shodan 8.8.8.8
```

### Attack

```bash
python spectre.py --sqli "http://target.com/page?id=1"
python spectre.py --backdoor 10.0.0.5:4444
python spectre.py --ransomware
python spectre.py --phishing https://example.com
python spectre.py --crypto 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
python spectre.py --wifi
python spectre.py --dns-spoof example.com
```

### Exploit

```bash
python spectre.py --yara /path/to/file
python spectre.py --msf apache
python spectre.py --evasion 10.0.0.5
python spectre.py --autopwn target.com
```

### System

```bash
python spectre.py --all example.com     # SEMUA modul
python spectre.py --web                 # Web UI
python spectre.py --c2                  # C2 listener
python spectre.py --ai                  # AI chat
python spectre.py --db                  # DB stats
python spectre.py --report
python spectre.py --plugins
python spectre.py --init
python spectre.py --help
```

---

## 5. MODUL LENGKAP

### Recon

| Modul | Fungsi |
|---|---|
| `geoip` | Geolocation, ISP, ASN |
| `breach` | HaveIBeenPwned check |
| `darkweb` | Paste leak (psbdmp) |
| `phone` | Carrier, geocoder |
| `port` | Threaded port scan + banner grab |
| `whois` | Registrar, dates, NS |
| `dns` | A/AAAA/MX/NS/TXT/CNAME/SOA/CAA |
| `subdomain` | 70+ wordlist + takeover detect |
| `email` | Pattern + Hunter.io |
| `ssl` | Cert, SAN, TLS version |
| `social` | 12 platform |
| `tech` | Server, CDN, WAF, CMS |
| `dir` | 80+ path bruteforce |
| `async` | Full recon paralel |
| `shodan` | Host lookup + CVE |

### Attack

| Modul | Fungsi |
|---|---|
| `sqli` | SQLi + XSS scanner |
| `backdoor` | 6 bahasa reverse shell |
| `ransomware` | AES-256 gen (EDU) |
| `phishing` | Clone + harvester |
| `crypto` | BTC + ETH tracker |
| `wifi` | WiFi scan |
| `dns-spoof` | Spoofing helper |

### Exploit

| Modul | Fungsi |
|---|---|
| `yara` | Malware scan |
| `msf` | Metasploit RPC |
| `evasion` | Obfuscator + AMSI bypass |
| `autopwn` | Auto-pwn chain |

---

## 6. KONFIGURASI

Edit `config.yaml`. Minimal:

```yaml
general:
  threads: 100
ai:
  enabled: false
storage:
  driver: "sqlite"
```

### Aktifkan AI (Ollama)

```bash
ollama serve &
ollama pull llama3.2
```

```yaml
ai:
  enabled: true
  provider: "ollama"
  ollama:
    model: "llama3.2"
```

### Aktifkan Telegram C2

```yaml
c2:
  telegram:
    enabled: true
    bot_token: "123:ABC"
    chat_id: "987654"
```

---

## 7. DOCKER

```bash
docker-compose up -d
```

Services: master (5000), worker x3, redis, postgres, ollama.

---

## 8. LEGAL

```
╔══════════════════════════════════════════════════════════════╗
║                    ⚠️ LEGAL WARNING ⚠️                       ║
╚══════════════════════════════════════════════════════════════╝
```

**DIIZINKAN:**
- ✅ Scan sistem sendiri
- ✅ Pentest dengan kontrak
- ✅ CTF
- ✅ Bug bounty scope
- ✅ Lab edukasi

**DILARANG:**
- ❌ Scan tanpa izin
- ❌ Phishing tanpa kontrak
- ❌ Deploy ransomware
- ❌ DoS/DDoS
- ❌ Mencuri data

Author tidak bertanggung jawab atas penyalahgunaan.

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

**End of README**