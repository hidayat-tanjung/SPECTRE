#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  SPECTRE v5.0 - CORE ENGINE
#  Config | Storage | Logging | Utils | Crypto
#  👻 AUTHOR: イズミー (IZUMI)
# ============================================================

import os
import re
import sys
import json
import time
import base64
import hashlib
import logging
import platform
import sqlite3
import threading
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict, List

# ============================================================
# OPTIONAL IMPORTS
# ============================================================
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class Fore:
        RED=GREEN=YELLOW=CYAN=MAGENTA=WHITE=BLUE=RESET=""
    class Style:
        RESET=""
        BRIGHT=""

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import StaticPool
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

# Suppress warnings
warnings.filterwarnings("ignore")
try:
    from urllib3.exceptions import InsecureRequestWarning
    if HAS_REQUESTS:
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except Exception:
    pass


# ============================================================
# PATHS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = BASE_DIR / "config.yaml"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

VERSION = "5.0.0"
AUTHOR = "イズミー (IZUMI)"
YEAR = "2050"


# ============================================================
# LOGGER
# ============================================================
class Log:
    _lock = threading.Lock()
    _loggers: Dict[str, logging.Logger] = {}

    @staticmethod
    def get(name: str = "spectre") -> logging.Logger:
        with Log._lock:
            if name in Log._loggers:
                return Log._loggers[name]

            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
            logger.propagate = False

            # avoid duplicate handlers
            if not logger.handlers:
                try:
                    fh = logging.FileHandler(LOG_DIR / f"{name}.log", encoding="utf-8")
                    fh.setLevel(logging.DEBUG)
                    fh.setFormatter(logging.Formatter(
                        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
                    ))
                    logger.addHandler(fh)
                except Exception:
                    pass

                ch = logging.StreamHandler()
                ch.setLevel(logging.WARNING)
                ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
                logger.addHandler(ch)

            Log._loggers[name] = logger
            return logger


log = Log.get("spectre")


# ============================================================
# COLOR HELPER
# ============================================================
class C:
    @staticmethod
    def s(t): return f"{Fore.GREEN}✅ {t}{Style.RESET_ALL}"
    @staticmethod
    def e(t): return f"{Fore.RED}❌ {t}{Style.RESET_ALL}"
    @staticmethod
    def w(t): return f"{Fore.YELLOW}⚠️  {t}{Style.RESET_ALL}"
    @staticmethod
    def i(t): return f"{Fore.CYAN}ℹ️  {t}{Style.RESET_ALL}"
    @staticmethod
    def h(t): return f"{Fore.RED}💀 {t}{Style.RESET_ALL}"
    @staticmethod
    def j(t): return f"{Fore.YELLOW}🇯🇵 {t}{Style.RESET_ALL}"
    @staticmethod
    def a(t): return f"{Fore.MAGENTA}⚡ {t}{Style.RESET_ALL}"
    @staticmethod
    def d(t): return f"{Fore.MAGENTA}🌑 {t}{Style.RESET_ALL}"


# ============================================================
# CONFIG LOADER
# ============================================================
class Config:
    _instance: Optional["Config"] = None
    _lock = threading.Lock()

    def __new__(cls, *a, **kw):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._loaded = False
            return cls._instance

    def __init__(self, path: Optional[str] = None):
        if self._loaded:
            return
        self.path = Path(path or os.getenv("CONFIG_PATH", DEFAULT_CONFIG))
        self.data: Dict[str, Any] = {}
        self._load()
        self._loaded = True

    def _load(self):
        if HAS_YAML and self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = yaml.safe_load(f) or {}
                log.info(f"Config loaded from {self.path}")
            except Exception as e:
                log.error(f"Config load failed: {e}")
                self.data = self._defaults()
        else:
            log.warning(f"Config not found: {self.path}, using defaults")
            self.data = self._defaults()

        self._apply_env_overrides()

    def _defaults(self) -> Dict[str, Any]:
        return {
            "general": {"version": VERSION, "threads": 100, "timeout": 8,
                        "user_agent": "random"},
            "ai": {"enabled": False, "provider": "none",
                   "features": {"report_generation": True, "vuln_reasoning": True,
                                "payload_mutation": False, "chat_interface": True}},
            "storage": {"driver": "sqlite", "sqlite": {"path": "spectre.db"},
                        "postgres": {"dsn": ""}},
            "redis": {"enabled": False},
            "c2": {},
            "recon": {},
            "exploit": {"msf": {"enabled": False}},
            "web": {"host": "0.0.0.0", "port": 5000,
                    "auth": {"enabled": True, "users": {"admin": "changeme"}}},
            "evasion": {},
        }

    def _apply_env_overrides(self):
        for env_key, val in os.environ.items():
            if not env_key.startswith("SPECTRE_"):
                continue
            parts = env_key[len("SPECTRE_"):].lower().split("_", 1)
            if len(parts) != 2:
                continue
            section, key = parts
            if section not in self.data:
                self.data[section] = {}
            if isinstance(self.data[section], dict):
                if val.lower() in ("true", "false"):
                    val = val.lower() == "true"
                elif val.isdigit():
                    val = int(val)
                self.data[section][key] = val

    def get(self, path: str, default: Any = None) -> Any:
        cur = self.data
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return default
        return cur

    def __getitem__(self, key): return self.data.get(key, {})
    def __contains__(self, key): return key in self.data
    def to_dict(self): return self.data


cfg = Config()


# ============================================================
# STORAGE
# ============================================================
class Storage:
    def __init__(self, driver: Optional[str] = None):
        self.driver = driver or cfg.get("storage.driver", "sqlite")
        self._engine = None
        self._sqlite_path = cfg.get("storage.sqlite.path", "spectre.db")
        self._pg_dsn = cfg.get("storage.postgres.dsn", "")
        self._lock = threading.Lock()
        self._init_engine()
        self._init_schema()

    def _init_engine(self):
        if self.driver == "postgres" and HAS_SQLALCHEMY and self._pg_dsn:
            try:
                self._engine = create_engine(self._pg_dsn, pool_pre_ping=True)
                log.info("Using PostgreSQL")
                return
            except Exception as e:
                log.error(f"Postgres failed: {e}, fallback SQLite")
                self.driver = "sqlite"

        if HAS_SQLALCHEMY:
            try:
                dsn = f"sqlite:///{self._sqlite_path}"
                self._engine = create_engine(
                    dsn,
                    connect_args={"check_same_thread": False},
                    poolclass=StaticPool,
                )
                log.info(f"SQLite: {self._sqlite_path}")
            except Exception as e:
                log.error(f"SQLAlchemy init failed: {e}")
                self._engine = None

    def _init_schema(self):
        ddl_scans = """
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target TEXT NOT NULL,
            module TEXT NOT NULL,
            data TEXT,
            severity TEXT DEFAULT 'info',
            ts TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
        ddl_targets = """
        CREATE TABLE IF NOT EXISTS targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target TEXT UNIQUE NOT NULL,
            tags TEXT,
            first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
            last_seen TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
        ddl_findings = """
        CREATE TABLE IF NOT EXISTS findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target TEXT,
            kind TEXT,
            detail TEXT,
            severity TEXT,
            ts TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
        try:
            if self._engine is not None and HAS_SQLALCHEMY:
                with self._engine.begin() as con:
                    con.execute(text(ddl_scans))
                    con.execute(text(ddl_targets))
                    con.execute(text(ddl_findings))
            else:
                con = sqlite3.connect(self._sqlite_path)
                con.execute(ddl_scans)
                con.execute(ddl_targets)
                con.execute(ddl_findings)
                con.commit()
                con.close()
        except Exception as e:
            log.error(f"Schema init failed: {e}")

    def save(self, target: str, module: str, data: Any, severity: str = "info"):
        payload = json.dumps(data, default=str, ensure_ascii=False)
        ts = datetime.now().isoformat()
        with self._lock:
            try:
                if self._engine is not None and HAS_SQLALCHEMY:
                    with self._engine.begin() as con:
                        con.execute(
                            text("INSERT INTO scans (target,module,data,severity,ts) "
                                 "VALUES (:t,:m,:d,:s,:ts)"),
                            {"t": str(target), "m": module, "d": payload,
                             "s": severity, "ts": ts},
                        )
                        con.execute(
                            text("INSERT INTO targets (target, last_seen) "
                                 "VALUES (:t, :ts) "
                                 "ON CONFLICT(target) DO UPDATE SET last_seen=:ts"),
                            {"t": str(target), "ts": ts},
                        )
                else:
                    con = sqlite3.connect(self._sqlite_path)
                    con.execute(
                        "INSERT INTO scans (target,module,data,severity,ts) "
                        "VALUES (?,?,?,?,?)",
                        (str(target), module, payload, severity, ts),
                    )
                    con.execute(
                        "INSERT OR IGNORE INTO targets (target, last_seen) "
                        "VALUES (?,?)",
                        (str(target), ts),
                    )
                    con.commit()
                    con.close()
            except Exception as e:
                log.error(f"save failed: {e}")

    def save_finding(self, target: str, kind: str, detail: Any, severity: str = "info"):
        payload = json.dumps(detail, default=str, ensure_ascii=False)
        ts = datetime.now().isoformat()
        with self._lock:
            try:
                if self._engine is not None and HAS_SQLALCHEMY:
                    with self._engine.begin() as con:
                        con.execute(
                            text("INSERT INTO findings (target,kind,detail,severity,ts) "
                                 "VALUES (:t,:k,:d,:s,:ts)"),
                            {"t": target, "k": kind, "d": payload,
                             "s": severity, "ts": ts},
                        )
                else:
                    con = sqlite3.connect(self._sqlite_path)
                    con.execute(
                        "INSERT INTO findings (target,kind,detail,severity,ts) "
                        "VALUES (?,?,?,?,?)",
                        (target, kind, payload, severity, ts),
                    )
                    con.commit()
                    con.close()
            except Exception as e:
                log.error(f"save_finding failed: {e}")

    def dump(self, limit: int = 200) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        try:
            if self._engine is not None and HAS_SQLALCHEMY:
                with self._engine.begin() as con:
                    rs = con.execute(text(
                        "SELECT target, module, data, severity, ts FROM scans "
                        "ORDER BY id DESC LIMIT :l"
                    ), {"l": limit}).fetchall()
                    for r in rs:
                        rows.append({"target": r[0], "module": r[1],
                                     "data": r[2], "severity": r[3], "ts": r[4]})
            else:
                con = sqlite3.connect(self._sqlite_path)
                rs = con.execute(
                    "SELECT target, module, data, severity, ts FROM scans "
                    "ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
                con.close()
                for r in rs:
                    rows.append({"target": r[0], "module": r[1],
                                 "data": r[2], "severity": r[3], "ts": r[4]})
        except Exception as e:
            log.error(f"dump failed: {e}")
        return rows

    def targets(self) -> List[str]:
        try:
            if self._engine is not None and HAS_SQLALCHEMY:
                with self._engine.begin() as con:
                    rs = con.execute(text("SELECT target FROM targets ORDER BY id DESC")).fetchall()
                    return [r[0] for r in rs]
            else:
                con = sqlite3.connect(self._sqlite_path)
                rs = con.execute("SELECT target FROM targets ORDER BY id DESC").fetchall()
                con.close()
                return [r[0] for r in rs]
        except Exception as e:
            log.error(f"targets failed: {e}")
            return []

    def history(self, target: str, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            if self._engine is not None and HAS_SQLALCHEMY:
                with self._engine.begin() as con:
                    rs = con.execute(text(
                        "SELECT module, data, severity, ts FROM scans "
                        "WHERE target=:t ORDER BY id DESC LIMIT :l"
                    ), {"t": target, "l": limit}).fetchall()
                    return [{"module": r[0], "data": r[1],
                             "severity": r[2], "ts": r[3]} for r in rs]
            else:
                con = sqlite3.connect(self._sqlite_path)
                rs = con.execute(
                    "SELECT module, data, severity, ts FROM scans "
                    "WHERE target=? ORDER BY id DESC LIMIT ?", (target, limit)
                ).fetchall()
                con.close()
                return [{"module": r[0], "data": r[1],
                         "severity": r[2], "ts": r[3]} for r in rs]
        except Exception as e:
            log.error(f"history failed: {e}")
            return []

    def stats(self) -> Dict[str, Any]:
        try:
            if self._engine is not None and HAS_SQLALCHEMY:
                with self._engine.begin() as con:
                    s = con.execute(text("SELECT COUNT(*) FROM scans")).scalar()
                    a = con.execute(text("SELECT COUNT(*) FROM targets")).scalar()
                    f = con.execute(text("SELECT COUNT(*) FROM findings")).scalar()
                    return {"scans": s, "assets": a, "findings": f,
                            "driver": self.driver}
            else:
                con = sqlite3.connect(self._sqlite_path)
                s = con.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
                a = con.execute("SELECT COUNT(*) FROM targets").fetchone()[0]
                f = con.execute("SELECT COUNT(*) FROM findings").fetchone()[0]
                con.close()
                return {"scans": s, "assets": a, "findings": f,
                        "driver": self.driver}
        except Exception as e:
            log.error(f"stats failed: {e}")
            return {"scans": 0, "assets": 0, "findings": 0,
                    "driver": self.driver}


_store: Optional[Storage] = None
_store_lock = threading.Lock()


def store() -> Storage:
    global _store
    with _store_lock:
        if _store is None:
            _store = Storage()
        return _store


# ============================================================
# CRYPTO
# ============================================================
class Crypto:
    @staticmethod
    def gen_key() -> bytes:
        if not HAS_CRYPTO:
            raise RuntimeError("cryptography not installed")
        return Fernet.generate_key()

    @staticmethod
    def enc(key: bytes, data: bytes) -> bytes:
        return Fernet(key).encrypt(data)

    @staticmethod
    def dec(key: bytes, token: bytes) -> bytes:
        return Fernet(key).decrypt(token)

    @staticmethod
    def xor(data: bytes, key: bytes) -> bytes:
        if not key:
            return data
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

    @staticmethod
    def b64e(data: bytes) -> str:
        return base64.b64encode(data).decode()

    @staticmethod
    def b64d(s: str) -> bytes:
        return base64.b64decode(s)

    @staticmethod
    def obfuscate(data: bytes, key: bytes) -> str:
        step1 = Crypto.xor(data, key)
        step2 = Crypto.b64e(step1)
        step3 = step2[::-1]
        return Crypto.b64e(step3.encode())

    @staticmethod
    def deobfuscate(s: str, key: bytes) -> bytes:
        step1 = Crypto.b64d(s).decode()
        step2 = step1[::-1]
        step3 = Crypto.b64d(step2)
        return Crypto.xor(step3, key)

    @staticmethod
    def md5(data: bytes) -> str: return hashlib.md5(data).hexdigest()
    @staticmethod
    def sha1(data: bytes) -> str: return hashlib.sha1(data).hexdigest()
    @staticmethod
    def sha256(data: bytes) -> str: return hashlib.sha256(data).hexdigest()


# ============================================================
# UTILS
# ============================================================
class Utils:
    @staticmethod
    def now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def timestamp() -> int:
        return int(time.time())

    @staticmethod
    def is_ip(s: str) -> bool:
        try:
            import ipaddress
            ipaddress.ip_address(str(s))
            return True
        except Exception:
            return False

    @staticmethod
    def is_domain(s: str) -> bool:
        return bool(re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", str(s)))

    @staticmethod
    def is_email(s: str) -> bool:
        return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(s)))

    @staticmethod
    def normalize_url(target: str) -> str:
        if str(target).startswith(("http://", "https://")):
            return str(target)
        return f"https://{target}"

    @staticmethod
    def clear_screen():
        os.system("cls" if platform.system().lower() == "windows" else "clear")

    @staticmethod
    def user_agent() -> str:
        mode = cfg.get("general.user_agent", "random")
        if mode == "random":
            try:
                import fake_useragent
                return fake_useragent.UserAgent().random
            except Exception:
                pass
        return ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36")

    @staticmethod
    def http_headers() -> Dict[str, str]:
        return {
            "User-Agent": Utils.user_agent(),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "close",
        }

    @staticmethod
    def safe_json(data: Any, indent: int = 2) -> str:
        return json.dumps(data, indent=indent, default=str, ensure_ascii=False)

    @staticmethod
    def truncate(s: str, n: int = 100) -> str:
        s = str(s)
        return s if len(s) <= n else s[:n-3] + "..."

    @staticmethod
    def random_string(n: int = 8) -> str:
        import random, string
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))

    @staticmethod
    def chunk(lst, size):
        for i in range(0, len(lst), size):
            yield lst[i:i + size]

    @staticmethod
    def safe_filename(name: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_\-\.]", "_", str(name))

    @staticmethod
    def which(binary: str):
        from shutil import which as _which
        return _which(binary)


# ============================================================
# SESSION FACTORY
# ============================================================
class SessionFactory:
    _proxies: List[str] = []
    _lock = threading.Lock()

    @classmethod
    def set_proxies(cls, proxies: List[str]):
        with cls._lock:
            cls._proxies = list(set(proxies))

    @classmethod
    def get_proxy(cls) -> Optional[Dict[str, str]]:
        with cls._lock:
            if not cls._proxies:
                return None
            import random
            p = random.choice(cls._proxies)
            return {"http": p, "https": p}

    @classmethod
    def create(cls, use_proxy: bool = False):
        if not HAS_REQUESTS:
            raise RuntimeError("requests not installed")
        s = requests.Session()
        s.headers.update(Utils.http_headers())
        s.verify = False
        if use_proxy:
            p = cls.get_proxy()
            if p:
                s.proxies.update(p)
        return s


# ============================================================
# WRITER
# ============================================================
class Writer:
    @staticmethod
    def json(path, data):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)
            return True
        except Exception as e:
            log.error(f"write json: {e}")
            return False

    @staticmethod
    def text(path, text):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            return True
        except Exception as e:
            log.error(f"write text: {e}")
            return False

    @staticmethod
    def script(path, code, executable: bool = True):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(code)
            if executable and platform.system().lower() != "windows":
                try:
                    os.chmod(path, 0o755)
                except Exception:
                    pass
            return True
        except Exception as e:
            log.error(f"write script: {e}")
            return False


# ============================================================
# RETRY DECORATOR
# ============================================================
def retry(times: int = 3, delay: float = 1.0, backoff: float = 2.0,
          exceptions: tuple = (Exception,)):
    def deco(func):
        def wrapper(*args, **kwargs):
            d = delay
            last = None
            for i in range(times):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last = e
                    if i < times - 1:
                        time.sleep(d)
                        d *= backoff
            raise last
        return wrapper
    return deco


# ============================================================
# PROGRESS
# ============================================================
def progress(iterable, desc: str = "Processing"):
    try:
        from tqdm import tqdm
        return tqdm(iterable, desc=desc, unit="item", ncols=80)
    except Exception:
        return iterable


# ============================================================
# BANNER
# ============================================================
BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║   ███████╗██████╗ ███████╗ ██████╗████████╗██████╗ ███████╗ ║
║   ██╔════╝██╔══██╗██╔════╝██╔════╝╚══██╔══╝██╔══██╗██╔════╝ ║
║   ███████╗██████╔╝█████╗  ██║        ██║   ██████╔╝█████╗   ║
║   ╚════██║██╔═══╝ ██╔══╝  ██║        ██║   ██╔══██╗██╔══╝   ║
║   ███████║██║     ███████╗╚██████╗   ██║   ██║  ██║███████╗ ║
║   ╚══════╝╚═╝     ╚══════╝ ╚═════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝ ║
╚══════════════════════════════════════════════════════════════╝
"""


def print_banner():
    print(Fore.RED + BANNER + Style.RESET_ALL)
    print(Fore.YELLOW + f"  🔥 SPECTRE v{VERSION} - SINGULARITY EDITION 🔥")
    print(Fore.RED +    "  💀 NO FILTER | NO RULES | NO MERCY 💀")
    print(Fore.MAGENTA +f"  👻 AUTHOR: {AUTHOR}")
    print(Fore.CYAN +   "  ⚡ AI | Async | C2 | Persistence | Evasion | Web UI ⚡")
    print()


# ============================================================
# SELF-TEST
# ============================================================
if __name__ == "__main__":
    print_banner()
    print(C.i("Self-test core.py"))
    print(C.s(f"Version: {cfg.get('general.version', VERSION)}"))
    print(C.s(f"Storage driver: {cfg.get('storage.driver', 'sqlite')}"))

    st = store()
    st.save("test.local", "self_test", {"hello": "world"}, severity="info")
    rows = st.dump(5)
    print(C.s(f"DB rows: {len(rows)}"))

    key = Crypto.gen_key()
    secret = b"spectre-v5-secret"
    enc = Crypto.enc(key, secret)
    dec = Crypto.dec(key, enc)
    assert dec == secret
    print(C.s("Crypto OK"))

    obf = Crypto.obfuscate(secret, b"key123")
    deobf = Crypto.deobfuscate(obf, b"key123")
    assert deobf == secret
    print(C.s("Obfuscate OK"))

    print(C.h("core.py READY 💀"))