# Network-DNS-Monitoring

A Django 5 web management interface for **Network-DNS-Monitoring**, mirroring the management surface of the
[`nextdns`](https://github.com/nextdns/nextdns) CLI daemon: view discovered clients, cache
statistics, analytics dashboards, and manage the active profile — all behind a username/password login.

It is **not** a DNS server. Instead it talks to an already-installed local `nextdns` daemon
(the Windows service / Linux systemd service / macOS launchd agent) by invoking the
`nextdns` CLI binary, which already owns the control-socket and privilege logic. This keeps
the clone small and cross-platform without reimplementing the daemon's named-pipe / unix-socket
protocol.

The UI features a **professional sidebar navigation** with clean SVG icons, data-rich cards,
an interactive **network topology graph**, and a **Chart.js analytics dashboard**.

---

## Features

- **Login** with username & password (Django auth) + signup / logout.
- **Professional sidebar navigation** (Dashboard · Discovery · Cache · Analytics · Topology · Setup · Settings · AI Assistant).
- **Stats cards** with key metrics on every page.
- **Analytics dashboard** with Chart.js bar charts showing query volume, cache hits/misses
  over time, and historical snapshots.
- **Interactive topology graph** — a force-directed visualization showing clients, the resolver,
  and upstream connections, with real-time SSE updates.
- **Live daemon status** via the control commands `cache-stats`, `cache-metrics`, `discovered`.
- **Setup page** to read the active profile and (when running elevated) set a new profile id
  (`nextdns install -profile=...`) plus daemon restart.
- **Settings page** dumping the live `nextdns.conf`.
- **PostgreSQL persistence** of probes (required dependencies, discovered clients, cache
  snapshots, daemon status). Falls back to **SQLite** for local development when
  `NEXTDNS_DB_PASSWORD` is not set.

---

## Requirements

- Python 3.12+
- A local Network-DNS-Monitoring installation (`nextdns` / `nextdns.exe` on `PATH` or in `Program Files\NextDNS`)
- PostgreSQL 12+ listening on `localhost:5008`, database `ddns_network`, user `postgres`
  (optional — SQLite is used automatically when the password is not provided)

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

#    Or skip step 3 entirely — SQLite fallback is automatic.

# 4. apply migrations
python manage.py migrate

# 5. start the dev server
python manage.py runserver

#    Or use the bundled script (Windows):
#    .\run.bat
```

Open http://127.0.0.1:8090/ and sign in (default admin: `admin` / `admin123` if created
automatically).

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `NEXTDNS_DB_NAME`  | `ddns_network` | PostgreSQL database |
| `NEXTDNS_DB_HOST`  | `localhost`    | Database host |
| `NEXTDNS_DB_PORT`  | `5008`         | Database port |
| `NEXTDNS_DB_USER`  | `postgres`     | Database user |
| `NEXTDNS_DB_PASSWORD` | *(unset)* | Database password (if unset, SQLite is used) |
| `NEXTDNS_PORT`     | `8090`         | Dev server port (run.bat only) |

Secrets are read from the environment — the literal password is never stored in the source tree.

---

## Architecture

```
nextdns-web/
├── manage.py
├── requirements.txt
├── run.bat              # Windows dev server script
├── push.bat             # GitHub push script
├── nextdns_web/         # project: settings, urls, wsgi/asgi
│   ├── settings.py
│   └── urls.py
└── core/                # "Network-DNS-Monitoring" app
    ├── static/
    │   ├── css/style.css    # Professional sidebar + card styling
    │   └── js/
    │       ├── main.js
    │       └── topology.js  # Force-directed graph + SSE client
    ├── templates/
    │   ├── base.html          # Sidebar nav + topbar
    │   ├── icons/             # SVG icons for dock nav
    │   ├── core/
    │   │   ├── dashboard.html
    │   │   ├── discovery.html
    │   │   ├── cache.html
    │   │   ├── analytics.html   # Chart.js analytics dashboard
    │   │   ├── topology.html    # Network topology graph
    │   │   ├── setup.html
    │   │   ├── settings.html
    │   │   └── ai.html
    │   └── registration/
    │       ├── login.html
    │       └── signup.html
    ├── nextdns_ctl.py       # Shell out to `nextdns <cmd>` (JSON/CLI protocol)
    ├── nextdns_config.py    # Read/write nextdns.conf, locate the binary
    ├── nextdns_ai.py        # OpenRouter AI assistant integration
    ├── models.py            # Profile, DiscoveredClient, CacheStatsSnapshot, DaemonStatus
    ├── views.py             # Auth + pages (login_required), persistence
    └── admin.py             # Django admin for the models
```

### Data flow

1. A browser request hits a `@login_required` view in `core/views.py`.
2. The view calls `core/nextdns_ctl.query("cache-stats")` etc., which run the
   real `nextdns` CLI binary (found via `core/nextdns_config.binary_path()`) and
   parse its JSON output. This delegates to the daemon's own control-socket logic.
3. Results are rendered through templates that extend `base.html` (the sidebar nav lives there).
   Live probes are also persisted to the database.

| CLI command (Go)  | Django page | What it shows |
|---|---|---|
| `cache-stats`     | Dashboard, Analytics, Cache | cache hits/misses + metrics |
| `cache-metrics`   | Dashboard, Analytics, Cache | detailed metrics (queries, blocks, etc.) |
| `cache-keys`      | Cache | cached entries (if registered) |
| `discovered`      | Dashboard, Discovery, Topology, Analytics | LAN clients that queried the resolver |
| `install`/`restart` | Setup | set profile id, restart daemon |
| `-config-file`    | Settings | the on-disk `nextdns.conf` |

### Topology graph

The topology page renders a **force-directed network graph** using vanilla JavaScript
(no external dependencies). It shows:

- **Resolver node** (green) — the local Network-DNS-Monitoring daemon
- **Client nodes** (orange) — discovered LAN clients
- **Upstream node** (blue, dashed link) — the upstream DNS provider

The graph receives **real-time updates** via Server-Sent Events (SSE) at `/topology/stream/`,
updating the client count, cache hit rate, and node positions every 5 seconds.

### Analytics

The analytics page uses **Chart.js** (loaded from CDN) to render a bar chart of
cache hits and misses over the last 20 historical snapshots. Snapshots are persisted
to the database on each dashboard visit.

---

## License

This is an independent, community web management UI. The underlying daemon and its name remain
the property of their respective owners. See the parent repository for the upstream CLI.
