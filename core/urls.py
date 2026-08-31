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
]
