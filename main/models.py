from django.db import models
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import datetime, timedelta
from pytz import timezone


TIME_ZONE = 'UTC'
class Provider(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    active = models.BooleanField(default=False)
    ready = models.BooleanField(default=False)
    last_ready_signal = models.DateTimeField(default=datetime(2018, 7, 1, tzinfo=timezone(TIME_ZONE)))
    location = models.CharField(max_length=30, blank=True)
    fabric_org = models.CharField(max_length=30, blank=True)
    ram = models.IntegerField(default=0)
    cpu = models.IntegerField(default=0)

    def __str__(self):
        return self.user.username

    def is_contributing(self):
        if self.active and self.ready:
            if self.last_ready_signal > datetime.now(timezone(TIME_ZONE)) - timedelta(minutes=1):
                return True
            else:
                return False
        else:
            return False


class Developer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    active = models.BooleanField(default=False)
    location = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Provider.objects.create(user=instance)
        Developer.objects.create(user=instance)
    instance.provider.save()
    instance.developer.save()


# Create your models here

# Create your models here.
class Services(models.Model):
    developer = models.ForeignKey(Developer, on_delete=models.CASCADE)
    provider = models.ForeignKey(Provider, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=30)
    docker_container = models.URLField()
    active = models.BooleanField(default=False)

    class Meta:
        # Each developer can only have one service with a specific name
        unique_together = ['name', 'developer']

class Job(models.Model):
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE,null=True,blank=True)
    service = models.ForeignKey(Services, on_delete=models.CASCADE)
    start_time = models.DateTimeField(default=datetime(2018, 7, 1, tzinfo=timezone(TIME_ZONE)))
    ack_time = models.DateTimeField(default=datetime(2018, 7, 1, tzinfo=timezone(TIME_ZONE)))
    pull_time = models.IntegerField(default=0)
    run_time = models.IntegerField(default=0)
    total_time = models.IntegerField(default=0)
    cost = models.FloatField(default=0.0)
    finished = models.BooleanField(default=False)
    corr_id = models.UUIDField(default=0, db_index=True)
    response = models.TextField(default='')