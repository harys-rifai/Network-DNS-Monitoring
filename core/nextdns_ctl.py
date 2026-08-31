"""Client for the local Network-DNS-Monitoring daemon control commands.

Instead of reimplementing the daemon's named-pipe / unix-socket protocol
(which is platform-specific, see pkg/ctl), this module delegates to the
already-installed ``nextdns`` CLI binary. That binary already owns the
control-socket logic, privilege handling and output formatting, so we just
run ``nextdns <command>`` and parse its JSON output. No extra deps, no
platform-specific socket code.
"""

import json
import shutil
import subprocess

from . import nextdns_config as _cfg

DEFAULT_TIMEOUT = 5


def binary_path():
    """Resolve the nextdns binary to invoke for control commands."""
    return _cfg.binary_path()


def query(command, timeout=DEFAULT_TIMEOUT):
    """Run ``nextdns <command>`` and return (data, error).

    The daemon CLI prints JSON for structured commands (cache-stats,
    discovered, cache-metrics) and plain text for trace/arp/ndp.
    """
    exe = binary_path()
    if not exe:
        return None, "Network-DNS-Monitoring binary not found. Install it or add it to PATH."
    try:
        proc = subprocess.run(
            [exe, command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None, "Request to Network-DNS-Monitoring daemon timed out."
    except OSError as e:
        return None, "Failed to run the nextdns CLI: %s" % e

    if proc.returncode != 0:
        msg = (proc.stderr or "").strip()
        if not msg:
            msg = "nextdns %s failed (exit code %d)." % (command, proc.returncode)
        return None, msg

    text = proc.stdout.strip()
    if not text:
        return None, None
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        # Raw-text commands (trace / arp / ndp) land here.
        return text, None
