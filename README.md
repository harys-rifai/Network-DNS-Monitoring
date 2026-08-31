# Network-DNS-Monitoring

A Django 5 web management interface for **Network-DNS-Monitoring**, mirroring the management surface of the
[`nextdns`](https://github.com/nextdns/nextdns) CLI daemon: view discovered clients, cache
statistics, and manage the active profile — all behind a username/password login.

It is **not** a DNS server. Instead it talks to an already-installed local `nextdns` daemon
(the Windows service / Linux systemd service / macOS launchd agent) by invoking the
`nextdns` CLI binary, which already owns the control-socket and privilege logic. This keeps
the clone small and cross-platform without reimplementing the daemon's named-pipe / unix-socket
protocol.

The UI is styled macOS-inspired, including a blurred **bottom dock menu** à la Big Sur/Monterey.

---

## Features

- **Login** with username & password (Django auth) + signup / logout.
- **macOS-style bottom dock** navigation (Dashboard · Discovery · Cache · Setup · Settings),
  active-item highlight, hover magnify, vibrancy blur.
- **Live daemon status** via the control commands `cache-stats`, `cache-metrics`, `discovered`.
- **Setup page** to read the active profile and (when running elevated) set a new profile id
  (`nextdns install -profile=...`) plus daemon restart.
- **Settings page** dumping the live `nextdns.conf`.
- **PostgreSQL persistence** of probes (required dependencies, discovered clients, cache
  snapshots, daemon status).

---

## Requirements

- Python 3.12+
- A local Network-DNS-Monitoring installation (`nextdns` / `nextdns.exe` on `PATH` or in `Program Files\NextDNS`)
- PostgreSQL 12+ listening on `localhost:5008`, database `ddns_network`, user `postgres`

---

## Quick start

```bash
# 1. (optional) create and activate a virtual environment
python -m venv .venv
# .venv\Scripts\activate      # Windows
# source .venv/bin/activate   # macOS / Linux

# 2. install dependencies
python -m pip install -r requirements.txt

# 3. set the database password (never committed to source)
set NEXTDNS_DB_PASSWORD=Password09!      # Windows PowerShell / cmd
# export NEXTDNS_DB_PASSWORD=Password09!  # macOS / Linux bash

# 4. apply migrations
python manage.py migrate

# 5. create an admin account
python manage.py createsuperuser

# 6. run
python manage.py runserver
```

Open http://127.0.0.1:8000/ and sign in.

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `NEXTDNS_DB_NAME`  | `ddns_network` | PostgreSQL database |
| `NEXTDNS_DB_HOST`  | `localhost`    | Database host |
| `NEXTDNS_DB_PORT`  | `5008`         | Database port |
| `NEXTDNS_DB_USER`  | `postgres`     | Database user |
| `NEXTDNS_DB_PASSWORD` | *(unset)* | Database password (**required**) |

Secrets are read from the environment — the literal password is never stored in the source tree.

---

## Architecture

```
nextdns-web/
├── manage.py
├── requirements.txt
├── nextdns_web/          # project: settings, urls, wsgi/asgi
    └── core/                 # "Network-DNS-Monitoring" app
    ├── static/css/style.css   # macOS-themed UI + dock
    ├── static/js/main.js
    ├── templates/
    │   ├── base.html            # top bar + bottom dock menu
    │   ├── core/                # dashboard, discovery, cache, setup, settings
    │   └── registration/        # login, signup
    ├── nextdns_ctl.py           # shell out to `nextdns <cmd>` (JSON/CLI protocol)
    ├── nextdns_config.py        # read/write nextdns.conf, locate the binary
    ├── models.py                # Profile, DiscoveredClient, CacheStatsSnapshot, DaemonStatus
    ├── views.py                 # auth + pages (login_required), persistence
    └── admin.py                 # Django admin for the models
```

### Data flow

1. A browser request hits a `@login_required` view in `core/views.py`.
2. The view calls `core/nextdns_ctl.query("cache-stats")` etc., which run the
   real `nextdns` CLI binary (found via `core/nextdns_config.binary_path()`) and
   parse its JSON output. This delegates to the daemon's own control-socket logic.
3. Results are rendered through templates that extend `base.html` (the dock lives
   there). Live probes are also persisted to PostgreSQL.

| CLI command (Go)  | Django page | What it shows |
|---|---|---|
| `cache-stats`     | Dashboard, Cache | cache hits/misses + metrics |
| `cache-keys`      | Cache             | cached entries (if registered) |
| `discovered`      | Dashboard, Discovery | LAN clients that queried the resolver |
| `install`/`restart` | Setup           | set profile id, restart daemon |
| `-config-file`    | Settings          | the on-disk `nextdns.conf` |

### On Windows

The daemon listens on the named pipe `\\.\pipe\nextdns-cli`. The clone shells out to
`nextdns.exe`, which speaks that pipe natively — so **no** Python `AF_UNIX`/named-pipe
client is required. Writing the config (`C:\Program Files\NextDNS\nextdns.conf`) and
restarting the service require the web process to run **as Administrator**.

### On Linux / macOS

The daemon listens on `/var/run/nextdns.sock`. The CLI uses `sudo` automatically when
needed, so the web process may need elevated privileges for `setup`/`restart` actions;
read-only pages (dashboard, discovery, cache, settings) work as a normal user.

---

## Running as a service

For production, run Django behind gunicorn/uwsgi + a reverse proxy, with the same env vars
available to the process and a persistent PostgreSQL instance.

---

## License

This is an independent, community web management UI. The underlying daemon and its name remain
the property of their respective owners. See the parent repository for the upstream CLI.
