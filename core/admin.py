from django.contrib import admin

from .models import (
    CacheStatsSnapshot,
    DaemonStatus,
    DiscoveredClient,
    Profile,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("profile_id", "active", "set_at")


@admin.register(DiscoveredClient)
class DiscoveredClientAdmin(admin.ModelAdmin):
    list_display = ("name", "source", "first_seen", "last_seen")
    readonly_fields = ("source", "name", "addresses", "first_seen", "last_seen")


@admin.register(CacheStatsSnapshot)
class CacheStatsSnapshotAdmin(admin.ModelAdmin):
    list_display = ("hits", "misses", "reachable", "recorded_at")
    readonly_fields = ("hits", "misses", "metrics", "reachable", "recorded_at")


@admin.register(DaemonStatus)
class DaemonStatusAdmin(admin.ModelAdmin):
    list_display = ("reachable", "recorded_at")
    readonly_fields = ("reachable", "error", "recorded_at")
