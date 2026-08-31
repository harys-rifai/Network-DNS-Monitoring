from django.db import models


class Profile(models.Model):
    """A Network-DNS-Monitoring profile id configured on the daemon."""

    profile_id = models.CharField(max_length=64, unique=True)
    active = models.BooleanField(default=False)
    set_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.profile_id


class DiscoveredClient(models.Model):
    """A client discovered on the LAN querying the resolver."""

    source = models.CharField(max_length=128, default="")
    name = models.CharField(max_length=255)
    addresses = models.JSONField(default=list)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("source", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name


class CacheStatsSnapshot(models.Model):
    """A point-in-time capture of resolver cache statistics."""

    hits = models.PositiveBigIntegerField(default=0)
    misses = models.PositiveBigIntegerField(default=0)
    metrics = models.JSONField(default=dict, blank=True)
    reachable = models.BooleanField(default=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return "hits=%d miss=%d @ %s" % (self.hits, self.misses, self.recorded_at)


class DaemonStatus(models.Model):
    """Recorded availability of the local Network-DNS-Monitoring daemon."""

    reachable = models.BooleanField(default=False)
    error = models.TextField(blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]

    def __str__(self):
        return "reachable=%s @ %s" % (self.reachable, self.recorded_at)
