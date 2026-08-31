"""Read/write the on-disk Network-DNS-Monitoring configuration file.

On Windows the daemon config lives at
``C:\\Program Files\\NextDNS\\nextdns.conf``, mirroring the
``ConfigFileStorer`` format used by the Go source (one ``key value``
per line).
"""

import os
import re
import shutil
import subprocess

PROFILE_RE = re.compile(r"^\s*profile\s+(\S+)\s*$")


def config_path():
    """Path to nextdns.conf."""
    if os.name == "nt":
        base = os.environ.get("ProgramFiles", r"C:\Program Files")
        return os.path.join(base, "NextDNS", "nextdns.conf")
    return "/etc/nextdns.conf"


def binary_path():
    """Locate the installed nextdns executable."""
    exe = "nextdns.exe" if os.name == "nt" else "nextdns"
    if os.name == "nt":
        base = os.environ.get("ProgramFiles", r"C:\Program Files")
        candidate = os.path.join(base, "NextDNS", exe)
        if os.path.exists(candidate):
            return candidate
    return shutil.which(exe)


def read_config():
    """Return (config, error). config maps key -> list[str]."""
    path = config_path()
    cfg = {}
    if not os.path.exists(path):
        return cfg, None
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(None, 1)
                key = parts[0]
                value = parts[1] if len(parts) > 1 else ""
                cfg.setdefault(key, []).append(value)
    except PermissionError:
        return cfg, "Permission denied reading %s (run as Administrator)" % path
    except OSError as e:
        return cfg, "Error reading config: %s" % e
    return cfg, None


def set_profile(profile):
    """Set the default profile in the config file. Returns (ok, error)."""
    path = config_path()
    try:
        lines = []
        found = False
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.rstrip("\n")
                    if PROFILE_RE.match(line):
                        lines.append("profile %s" % profile)
                        found = True
                    else:
                        lines.append(line)
        if not found:
            lines.append("profile %s" % profile)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except PermissionError:
        return False, "Permission denied writing %s; run as Administrator" % path
    except OSError as e:
        return False, "Failed to write config: %s" % e
    return True, None


def restart():
    """Restart the installed nextdns daemon. Returns (ok, error)."""
    binp = binary_path()
    if not binp:
        return False, "nextdns binary not found on PATH or in Program Files"
    try:
        subprocess.run([binp, "restart"], check=False,
                       capture_output=True, text=True, timeout=30)
    except OSError as e:
        return False, "Failed to restart Network-DNS-Monitoring: %s" % e
    return True, None
