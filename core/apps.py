"""Core app for the Network-DNS-Monitoring web clone."""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Network-DNS-Monitoring"
