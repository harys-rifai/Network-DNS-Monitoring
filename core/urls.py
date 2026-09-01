from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("discovery/", views.discovery, name="discovery"),
    path("cache/", views.cache, name="cache"),
    path("setup/", views.setup, name="setup"),
    path("settings/", views.settings_view, name="settings_view"),
    path("topology/", views.topology, name="topology"),
    path("topology/stream/", views.topology_stream, name="topology_stream"),
    path("ai/", views.ai_assistant, name="ai_assistant"),
    path("ai/chat/", views.ai_chat, name="ai_chat"),
]
