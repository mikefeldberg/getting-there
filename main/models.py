from django.db import models
from django.urls import reverse
from datetime import date
from django.contrib.auth.models import User

class Alert(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    station_id = models.CharField(max_length=100)
    line_id = models.CharField(max_length=100)
    direction = models.CharField(max_length=100)
    wait_time = models.IntegerField()
    ongoing = models.BooleanField(default=True)
    message = models.TextField(max_length=500)
    source_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField()

    def __str__(self):
        return self.id

    def get_absolute_url(self):
        return reverse('detail', kwargs={'alert_id': self.id})

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    alert_id = models.ForeignKey(Alert, on_delete=models.CASCADE)
    message = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField()

class Trip(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    trip_type = models.CharField(max_length=10)
    station_id = models.CharField(max_length=50)
    line_id = models.CharField(max_length=50)
    direction = models.CharField(max_length=50)

class Votes(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resolved = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
