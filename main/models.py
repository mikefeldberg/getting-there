from django.db import models
from django.urls import reverse
from datetime import date
from django.contrib.auth.models import User


class Line(models.Model):
    name = models.CharField(max_length=50)
    group_id = models.IntegerField()
    color = models.CharField(max_length=7)
    text_color = models.CharField(max_length=7)
    express = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True)

    def __str__(self):
        return self.name


class Station(models.Model):
    uid = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    line = models.ForeignKey(Line, on_delete=models.CASCADE, default=None)
    uptown_stop_number = models.IntegerField()
    downtown_stop_number = models.IntegerField()
    deleted_at = models.DateTimeField(null=True)

    def __str__(self):
        return self.name + ' ' + str(self.line_id)


class Alert(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None)
    station = models.ForeignKey(Station, on_delete=models.CASCADE, default=None)
    line = models.ForeignKey(Line, on_delete=models.CASCADE, default=None)
    direction = models.CharField(max_length=100)
    wait_time = models.IntegerField()
    ongoing = models.BooleanField(default=True)
    message = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)

    def __str__(self):
        return str(self.user) + ' ' + str(self.station) + ' ' + str(self.line) + ' ' + str(self.direction) + ' ' + str(self.ongoing)

    #TO DO: Decide whether or not to delete this or put it to use. May be useless for what we're doing.
    # def get_absolute_url(self):
    #     return reverse('detail', kwargs={'alert_id': self.id})


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None)
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, default=None)
    message = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True)

    def __str__(self):
        return str(self.user_id) + ' - ' + str(self.alert_id) + ' - ' + self.message


class Trip(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None)
    trip_type = models.CharField(max_length=10)
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, default=None)
    line = models.ForeignKey(Line, on_delete=models.CASCADE, default=None)
    direction = models.CharField(max_length=20)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.user_id) + ' - ' + str(self.trip_type) + ' - ' + str(self.station_id) + ' - ' + str(self.direction)

class Vote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None)
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, default=None)
    resolved = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.resolved
