import re

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db import transaction
from django.shortcuts import redirect, render

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
