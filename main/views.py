from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import ListView, DetailView
from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User

from copy import copy
import collections
import uuid
import boto3

from .models import Line, Station, Trip, Alert, Comment, Vote


def home(request):
    trips = Trip.objects.filter(
        user_id=request.user.id,
        deleted_at=None
    ).values(
        'line__id',
        'line__name',
        'line__color',
        'line__text_color',
        'line__express',
        'station__id',
        'station__name',
        'direction',
        'trip_type',
    ).all()

    return render(request, 'home.html', {'trips': trips})


def about(request):
    return render(request, 'about.html')


def signup(request):
    error_message = ''
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
        else:
            error_message = 'Invalid sign up - try again!'

    form = UserCreationForm()
    context = {
        'form': form,
        'error_message': error_message,
    }

    return render(request, 'registration/signup.html', context)


def lines_index(request):
    lines = Line.objects.filter(deleted_at=None).all()

    grouped_lines = collections.defaultdict(list)
    for line in lines:
        grouped_lines[line.group_id].append(line)
    
    return render(request, 'lines/index.html', {'grouped_lines': dict(grouped_lines)})


def lines_detail(request, line_id):
    line = Line.objects.filter(id=line_id, deleted_at=None).first()
    stations = Station.objects.filter(line_id=line_id, deleted_at=None).all()

    trips = Trip.objects.filter(
        user_id=request.user.id,
        line_id=line_id,
        deleted_at=None
    ).values('station_id').all()

    trip_station_ids = [i['station_id'] for i in trips]

    user = User.objects.filter(id=request.user.id).first()

    return render(request, 'lines/detail.html', {
        'line': line,
        'stations': stations,
        'trip_station_ids': trip_station_ids,
        'user': user
    })


@login_required
def trips_new(request, line_id, station_id):
    if request.method == 'POST':
        data = request.POST.copy()
        del data['csrfmiddlewaretoken']
        trip_type = data.pop('trip_type')[0]

        station_uid = Station.objects.filter(id=station_id).first().uid

        for item in data.keys():
            line_name, direction = item.split('_')
            line = Line.objects.filter(name=line_name).first()
            station = Station.objects.filter(uid=station_uid, line_id=line.id).first()
            trip = Trip(
                user=request.user,
                trip_type=trip_type,
                station_id=station.id,
                line_id=line.id,
                direction=direction,
            )

            trip.save()

        return redirect('/')

    line = Line.objects.filter(id=line_id, deleted_at=None).first()
    station = Station.objects.filter(id=station_id, deleted_at=None).first()

    lines = Station.objects.filter(
        uid=station.uid,
        deleted_at=None
    ).values(
        'line__name',
        'line__color',
        'line__text_color',
        'line__express',
        'uptown_stop_number',
        'downtown_stop_number'
    ).all()

    train_list = []

    for line in lines:
        train = {
            'name': line['line__name'],
            'color': line['line__color'],
            'text_color': line['line__text_color'],
            'express': line['line__express'],
        }

        if line.get('uptown_stop_number'):
            train['direction'] = 'Uptown'
            train_list.append(copy(train))

        if line.get('downtown_stop_number'):
            train['direction'] = 'Downtown'
            train_list.append(copy(train))

    return render(request, 'trips/new.html', {'line': line, 'station': station, 'train_list': train_list})


@login_required
def trips_edit(request):
    trips = Trip.objects.filter(deleted_at=None).all()
    # lines = Line.objects.filter()
    return render(request, 'trips/edit.html', {'trips': trips})

def alerts_index(request, station_id, line_id):
    alerts = Alert.objects.filter(
        station_id=station_id,
        line_id=line_id,
        deleted_at=None
    ).values(
        'id',
        'line__id',
        'line__name',
        'line__color',
        'line__text_color',
        'line__express',
        'station__name',
        'direction',
    ).all()

    return render(request, 'stations/alert_index.html', {'alerts': alerts, 'station_id': station_id, 'line_id': line_id})


@login_required
def alerts_new(request, station_id, line_id):
    if request.method == 'POST':
        data = request.POST.copy()
        del data['csrfmiddlewaretoken']
        wait_time = data.pop('wait_time')[0]

        station_uid = Station.objects.filter(id=station_id).first().uid

        for item in data.keys():
            line_name, direction = item.split('_')
            line = Line.objects.filter(name=line_name).first()
            station = Station.objects.filter(uid=station_uid, line_id=line.id).first()
            alert = Alert(
                user=request.user,
                station_id=station.id,
                line_id=line.id,
                direction=direction,
                wait_time=wait_time,
            )

            alert.save()

        # TO DO: redirect to origin station
        return redirect('/')

    line = Line.objects.filter(id=line_id, deleted_at=None).first()
    station = Station.objects.filter(id=station_id, deleted_at=None).first()

    lines = Station.objects.filter(
        uid=station.uid,
        deleted_at=None
    ).values(
        'line__name',
        'line__color',
        'line__text_color',
        'line__express',
        'uptown_stop_number',
        'downtown_stop_number'
    ).all()

    train_list = []

    for line in lines:
        train = {
            'name': line['line__name'],
            'color': line['line__color'],
            'text_color': line['line__text_color'],
            'express': line['line__express'],
        }

        if line.get('uptown_stop_number'):
            train['direction'] = 'Uptown'
            train_list.append(copy(train))

        if line.get('downtown_stop_number'):
            train['direction'] = 'Downtown'
            train_list.append(copy(train))

    minute_range = list(range(1,60))

    return render(request, 'alerts/new.html', {'line': line, 'station': station, 'train_list': train_list, 'minute_range': minute_range})


def alerts_detail(request, alert_id):
    alert = Alert.objects.filter(id=alert_id, deleted_at=None).first()
    user_id = request.user.id

    comments = Comment.objects.filter(
        alert_id=alert.id,
        deleted_at=None
    ).values(
        'user__id',
        'user__username',
        'message',
        'created_at'
    ).all()

    return render(request, 'alerts/detail.html', {'alert': alert, 'comments': comments, 'user_id': user_id})


def comments_new(request, alert_id):
    if request.method == 'POST':
        data = request.POST.copy()
        del data['csrfmiddlewaretoken']

        alert = Alert.objects.filter(id=alert_id).first()

        comment = Comment(
            user=request.user,
            alert_id=alert.id,
            message=data['message'],
        )

        comment.save()
        return redirect('/')

    current_user = Alert.objects.filter(
        id=alert_id
    ).values(
        'user__id',
        'user__username',
        'user__first_name',
    )

    alert = Alert.objects.filter(id=alert_id).first()

    return render(request, 'comments/new.html', {'alert': alert, 'current_user': current_user})

def mark_resolved(request, alert_id):
    vote = Vote.objects.filter(
        alert_id=alert_id,
        user_id=request.user.id
    ).first()

    if (vote):
        vote.resolved=True
        return render(request, 'alerts/')
    
    vote = Vote(
        alert_id=alert_id,
        user_id=request.user.id,
        resolved=True
    )

    vote.save()

    return render(request, 'about.html')

def mark_ongoing(request, alert_id):
    vote = Vote(
        alert_id=alert_id,
        user_id=request.user.id,
        resolved=False
    )


    print(vote)

    return False