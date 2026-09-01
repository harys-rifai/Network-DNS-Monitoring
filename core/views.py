import json
import re
import time

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import transaction
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect, render

from . import nextdns_ai as ai
from . import nextdns_config as cfg
from . import nextdns_ctl as ctl
from .models import CacheStatsSnapshot, DaemonStatus, DiscoveredClient, Profile

PROFILE_RE = re.compile(r"^[0-9a-f]{6}$")


def authed(request):
    return request.user.is_authenticated


def home(request):
    if authed(request):
        return redirect("dashboard")
    return redirect("login")


def login_view(request):
    if authed(request):
        return redirect("dashboard")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("dashboard")
    return render(request, "registration/login.html", {"form": form})


def signup_view(request):
    if authed(request):
        return redirect("dashboard")
    form = UserCreationForm(data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("login")
    return render(request, "registration/signup.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")


def _flat(conf):
    out = {}
    for k, v in conf.items():
        out[k] = ", ".join(v)
    return out


def _profile_value(conf):
    v = conf.get("profile")
    if isinstance(v, list):
        return v[0] if v else ""
    return v or ""


@login_required
def dashboard(request):
    stats, stats_err = ctl.query("cache-stats")
    metrics, metrics_err = ctl.query("cache-metrics")
    discovered, disc_err = ctl.query("discovered")

    # Persist a snapshot of the current state.
    reachable = stats_err is None
    try:
        with transaction.atomic():
            DaemonStatus.objects.create(
                reachable=reachable, error=stats_err or "")
            if stats:
                CacheStatsSnapshot.objects.create(
                    hits=int(stats.get("hit", 0) or 0),
                    misses=int(stats.get("miss", 0) or 0),
                    metrics=metrics or {},
                    reachable=reachable,
                )
    except Exception:
        pass  # DB not available yet — UI still renders live daemon data.

    return render(request, "core/dashboard.html", {
        "cache_stats": stats,
        "cache_stats_error": stats_err,
        "cache_metrics": metrics,
        "cache_metrics_error": metrics_err,
        "discovered": discovered,
        "discovered_error": disc_err,
    })


@login_required
def discovery(request):
    data, err = ctl.query("discovered")
    clients = {}
    if isinstance(data, dict):
        for source, names in data.items():
            if isinstance(names, dict):
                for name, addrs in names.items():
                    clients.setdefault(name, [])
                    if isinstance(addrs, list):
                        clients[name].extend(addrs)

    # Persist discovered clients (upsert).
    if data:
        try:
            with transaction.atomic():
                for source, names in data.items():
                    if not isinstance(names, dict):
                        continue
                    for name, addrs in names.items():
                        DiscoveredClient.objects.update_or_create(
                            source=source, name=name,
                            defaults={"addresses": list(addrs)})
        except Exception:
            pass

    return render(request, "core/discovery.html", {
        "clients": clients,
        "source_map": data,
        "error": err,
    })


@login_required
def cache(request):
    stats, stats_err = ctl.query("cache-stats")
    metrics, metrics_err = ctl.query("cache-metrics")
    keys, keys_err = ctl.query("cache-keys")
    return render(request, "core/cache.html", {
        "stats": stats, "stats_error": stats_err,
        "metrics": metrics, "metrics_error": metrics_err,
        "keys": keys, "keys_error": keys_err,
    })


@login_required
def setup(request):
    conf, conf_err = cfg.read_config()
    message = None
    if request.method == "POST":
        profile = (request.POST.get("profile") or "").strip().lower()
        if not PROFILE_RE.match(profile):
            message = {"error": "Profile ID must be 6 lowercase hex characters."}
        else:
            ok, err = cfg.set_profile(profile)
            if not ok:
                message = {"error": err}
            else:
                ok2, err2 = cfg.restart()
                message = (
                    {"success": "Profile set and daemon restarted."}
                    if ok2 else {"error": err2 or "Daemon could not be restarted."}
                )
                try:
                    Profile.objects.filter(active=True).update(active=False)
                    Profile.objects.update_or_create(
                        profile_id=profile, defaults={"active": True})
                except Exception:
                    pass
        conf, conf_err = cfg.read_config()
    return render(request, "core/setup.html", {
        "profile": _profile_value(conf),
        "config": _flat(conf),
        "conf_error": conf_err,
        "message": message,
        "binary": cfg.binary_path(),
    })


@login_required
def settings_view(request):
    conf, err = cfg.read_config()
    return render(request, "core/settings.html", {
        "config": _flat(conf),
        "conf_error": err,
        "binary": cfg.binary_path(),
        "conf_path": cfg.config_path(),
    })


@login_required
def ai_assistant(request):
    """Render the AI assistant chat page."""
    return render(request, "core/ai.html", {
        "ai_available": ai.available(),
        "ai_model": ai.DEFAULT_MODEL,
    })


@login_required
def ai_chat(request):
    """Handle a chat message from the AI assistant (AJAX + streaming).

    Expects ``POST`` with a JSON body containing a ``messages`` array (the
    conversation history, including the new user message) and optionally a
    ``model`` string.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST only."}, status=405)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    messages = payload.get("messages", [])
    model = payload.get("model") or ai.DEFAULT_MODEL

    if not ai.available():
        return JsonResponse({"error": "OpenRouter API key is not configured."}, status=503)

    stream = payload.get("stream", True)
    if not stream:
        result = ai.chat(messages, model=model)
        if result.get("error"):
            return JsonResponse({"error": result["error"]}, status=502)
        return JsonResponse({
            "content": result["content"],
            "model": result["model"],
        })

    def _event_stream():
        for chunk in ai.chat(messages, model=model, stream=True):
            yield "data: %s\n\n" % json.dumps(chunk)

    return StreamingHttpResponse(_event_stream(), content_type="text/event-stream")


def _topology_data():
    """Gather live daemon data for the topology view.

    Returns a dict that can be JSON-serialised and sent as an SSE event.
    """
    stats, stats_err = ctl.query("cache-stats")
    metrics, metrics_err = ctl.query("cache-metrics")
    discovered, disc_err = ctl.query("discovered")

    clients = []
    if isinstance(discovered, dict):
        for source, names in discovered.items():
            if isinstance(names, dict):
                for name, addrs in names.items():
                    clients.append({"source": source, "name": name, "addresses": list(addrs) if isinstance(addrs, list) else []})

    return {
        "daemon_reachable": stats_err is None,
        "daemon_error": stats_err,
        "cache_stats": stats,
        "cache_metrics": metrics,
        "clients": clients,
        "client_count": len(clients),
        "timestamp": time.time(),
    }


@login_required
def topology(request):
    """Render the realtime DNS topology page."""
    return render(request, "core/topology.html", {
        "initial_data": _topology_data(),
    })


@login_required
def topology_stream(request):
    """SSE endpoint that pushes topology snapshots at a fixed interval."""
    def _stream():
        yield "retry: 3000\ndata: %s\n\n" % json.dumps({"type": "ping"})
        while True:
            data = _topology_data()
            yield "data: %s\n\n" % json.dumps(data)
            time.sleep(5)

    return StreamingHttpResponse(_stream(), content_type="text/event-stream")


@login_required
def analytics(request):
    """Render the analytics dashboard mirroring my.nextdns.io analytics.

    Shows query volume over time (live + historical snapshots), top domains,
    top clients, and DNSSEC/DoH summary from the local daemon and persisted
    CacheStatsSnapshot models.
    """
    stats, stats_err = ctl.query("cache-stats")
    metrics, metrics_err = ctl.query("cache-metrics")
    discovered, disc_err = ctl.query("discovered")

    clients = {}
    if isinstance(discovered, dict):
        for source, names in discovered.items():
            if isinstance(names, dict):
                for name, addrs in names.items():
                    clients.setdefault(name, [])
                    if isinstance(addrs, list):
                        clients[name].extend(addrs)

    snapshots = CacheStatsSnapshot.objects.order_by("-recorded_at")[:20]

    time_labels = []
    hits_series = []
    misses_series = []
    for snap in snapshots:
        time_labels.append(snap.recorded_at.strftime("%H:%M"))
        hits_series.append(snap.hits)
        misses_series.append(snap.misses)

    stats_dict = stats if isinstance(stats, dict) else {}
    total_queries = stats_dict.get("queries", stats_dict.get("total", 0)) or 0
    total_answers = stats_dict.get("answers", 0) or 0

    top_domains = []
    metrics_dict = metrics if isinstance(metrics, dict) else {}
    for key in sorted(metrics_dict):
        if key.startswith("domain_") or key.startswith("top_"):
            top_domains.append((key, metrics_dict[key]))
    top_domains = top_domains[:10] if top_domains else []

    return render(request, "core/analytics.html", {
        "stats": stats_dict,
        "stats_error": stats_err,
        "metrics": metrics_dict,
        "metrics_error": metrics_err,
        "clients": clients,
        "discovered_error": disc_err,
        "total_queries": total_queries,
        "total_answers": total_answers,
        "snapshot_labels": time_labels,
        "snapshot_hits": hits_series,
        "snapshot_misses": misses_series,
        "snapshots": snapshots,
        "top_domains": top_domains,
    })
