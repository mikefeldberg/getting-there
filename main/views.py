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
from datetime import datetime, timedelta

import collections
import uuid
import boto3

from .models import Line, Station, Trip, Alert, Comment, Vote, Arrival


def home(request):
    trips = Trip.objects.filter(
        user_id=request.user.id,
        deleted_at=None
    ).values(
        'id',
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

    for trip in trips:
        trip['alert_count'] = []
        trip['resolved'] = False
        trip['updated_at'] = None
        alerts = []

        all_alerts = Alert.objects.filter(
            station_id=trip['station__id'],
            line_id=trip['line__id'],
            deleted_at=None,
        ).values(
            'id',
            'updated_at',
        ).all()

        for alert in all_alerts:
            trip['updated_at'] = alert['updated_at']
            
            vote = Vote.objects.filter(
                alert_id=alert['id']
            ).values(
                'resolved'
            ).last()

            alerts.append(alert['id'])
            if vote:
                trip['resolved'] = vote['resolved']

        trip['alert_count'].append(len(alerts))

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
    stations = Station.objects.filter(
        line_id=line_id,
        deleted_at=None
        ).all().order_by('downtown_stop_number')
        
    alerts = Alert.objects.filter(
        line_id=line_id,
        deleted_at=None
    ).values('station_id').all()

    trips = Trip.objects.filter(
        user_id=request.user.id,
        line_id=line_id,
        deleted_at=None
    ).values('station_id').all()

    trip_station_ids = [i['station_id'] for i in trips]
    alert_station_ids = [i['station_id'] for i in alerts]

    user = User.objects.filter(id=request.user.id).first()

    return render(request, 'lines/detail.html', {
        'user': user,
        'line': line,
        'stations': stations,
        'trip_station_ids': trip_station_ids,
        'alert_station_ids': alert_station_ids,
    })


@login_required
def trips_new(request, line_id, station_id):
    if request.method == 'POST':
        data = request.POST.copy()
        del data['csrfmiddlewaretoken']
        trip_type = data.pop('trip_type')[0]

        station_uid = Station.objects.filter(id=station_id).first().mta_downtown_id

        for item in data.keys():
            route_name, direction = item.split('_')
            if trip_type == 'Both':
                line = Line.objects.filter(id=route_name).first()
                station = Station.objects.filter(mta_downtown_id=station_uid, line_id=line.id).first()
                trip = Trip(
                    user=request.user,
                    trip_type="AM",
                    station_id=station.id,
                    line_id=line.id,
                    direction=direction,
                )
                
                trip.save()
                
                trip = Trip(
                    user=request.user,
                    trip_type="PM",
                    station_id=station.id,
                    line_id=line.id,
                    direction=direction,
                )

                trip.save()

            else:
                line = Line.objects.filter(id=route_name).first()
                station = Station.objects.filter(mta_downtown_id=station_uid, line_id=line.id).first()
                trip = Trip(
                    user=request.user,
                    trip_type=trip_type,
                    station_id=station.id,
                    line_id=line.id,
                    direction=direction,
                )

                trip.save()

        return redirect('lines_detail', line_id=line_id)

    line = Line.objects.filter(id=line_id, deleted_at=None).first()
    station = Station.objects.filter(id=station_id, deleted_at=None).first()

    lines = Station.objects.filter(
        mta_downtown_id=station.mta_downtown_id,
        deleted_at=None
    ).values(
        'line__id',
        'line__name',
        'line__color',
        'line__text_color',
        'line__express',
        'uptown_stop_number',
        'downtown_stop_number'
    ).all()

    train_lines = []

    for line in lines:
        train = {
            'id': line['line__id'],
            'name': line['line__name'],
            'color': line['line__color'],
            'text_color': line['line__text_color'],
            'express': line['line__express'],
        }

        if line.get('uptown_stop_number'):
            train['direction'] = 'Uptown'
            train_lines.append(copy(train))

        if line.get('downtown_stop_number'):
            train['direction'] = 'Downtown'
            train_lines.append(copy(train))

    return render(request, 'trips/new.html', {'line': line, 'station': station, 'train_lines': train_lines, 'line_id': line_id, })


@login_required
def trips_edit(request):
    if request.method == 'POST':
        data = request.POST.copy()
        del data['csrfmiddlewaretoken']

        for item in data:
            trip = Trip.objects.filter(id=item).first()
            trip.deleted_at = datetime.now()
            trip.save()


    trips = Trip.objects.filter(user_id=request.user.id, deleted_at=None).all()

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

    lines = Line.objects.filter(deleted_at=None).values(
        'id',
        'group_id',
        'name',
        'express',
        'color',
        'text_color',
    ).all().order_by('group_id')

    return render(request, 'alerts/index.html', {'alerts': alerts, 'station_id': station_id, 'line_id': line_id, 'lines': lines })


@login_required
def alerts_new(request, station_id, line_id):
    if request.method == 'POST':
        data = request.POST.copy()

        del data['csrfmiddlewaretoken']
        wait_time = data.pop('wait_time')[0]
        station_uid = Station.objects.filter(id=station_id).first().mta_downtown_id

        for item in data.keys():
            route_name, direction = item.split('_')
            line = Line.objects.filter(id=route_name).first()
            station = Station.objects.filter(mta_downtown_id=station_uid, line_id=line.id).first()

            alert = Alert(
                user=request.user,
                station_id=station.id,
                line_id=line.id,
                direction=direction,
                wait_time=wait_time,
            )

            alert.save()

        return redirect('alerts_index', station_id=station_id, line_id=line_id)

    line = Line.objects.filter(id=line_id, deleted_at=None).first()
    station = Station.objects.filter(id=station_id, deleted_at=None).first()

    lines = Station.objects.filter(
        mta_downtown_id=station.mta_downtown_id,
        deleted_at=None
    ).values(
        'line__id',
        'line__name',
        'line__color',
        'line__text_color',
        'line__express',
        'uptown_stop_number',
        'downtown_stop_number',
    ).all()

    train_lines = []

    for line in lines:
        train = {
            'id': line['line__id'],
            'name': line['line__name'],
            'color': line['line__color'],
            'text_color': line['line__text_color'],
            'express': line['line__express'],
        }

        if line.get('uptown_stop_number'):
            train['direction'] = 'Uptown'
            train_lines.append(copy(train))

        if line.get('downtown_stop_number'):
            train['direction'] = 'Downtown'
            train_lines.append(copy(train))

    minute_range = list(range(1,60))

    return render(request, 'alerts/new.html', {'line': line, 'station': station, 'train_lines': train_lines, 'minute_range': minute_range})


def alerts_detail(request, alert_id):
    if request.method == 'POST':
        data = request.POST.copy()
        del data['csrfmiddlewaretoken']

        for item in data.keys():
            comment = Comment.objects.filter(id=item).first()
            comment.deleted_at = datetime.now()
            comment.save()

    alert = Alert.objects.filter(id=alert_id, deleted_at=None).first()
    user_id = request.user.id

    all_votes = Vote.objects.filter(alert_id=alert_id).values('resolved', 'created_at', 'updated_at')
    votes = []
    resolved_last = None
    ongoing_last = None
    resolved_as_of = None
    ongoing_as_of = None

    for vote in all_votes:
        votes.append(vote['resolved'])

        if vote['resolved'] == True:
            resolved_last = vote['updated_at']
        if vote['resolved'] == False:
            ongoing_last = vote['updated_at']

    resolved_tally = votes.count(True)
    ongoing_tally = votes.count(False)

### --------------- ongoing updated_at is updating properly when marked ongoing, resolved updated_at is NOT updating properly when marked resolved --------- ###

    # if (resolved_last):
    #     resolved_as_of = datetime.today() - timedelta(resolved_last)
    # if (ongoing_last):
    #     ongoing_as_of = datetime.today() - timedelta(ongoing_last)

    # d = datetime.today() - timedelta(hours=0, minutes=50)

    # d.strftime('%H:%M %p')

    comments = Comment.objects.filter(
        alert_id=alert.id,
        deleted_at=None
    ).values(
        'id',
        'user__id',
        'user__username',
        'message',
        'created_at',
    ).all()

    return render(
        request,
        'alerts/detail.html',
        {
            'alert': alert,
            'resolved_tally': resolved_tally,
            'ongoing_tally': ongoing_tally,
            'resolved_last': resolved_last,
            'ongoing_last': ongoing_last,
            'comments': comments,
            'user_id': user_id
        }
    )


def mark_resolved(request, alert_id):
    vote = Vote.objects.filter(
        alert_id=alert_id,
        user_id=request.user.id
    ).first()

    alert = Alert.objects.filter(id=alert_id).first()

    if (vote):
        vote.resolved=True
        vote.save()
        alert.save()
        return redirect('alerts_detail', alert_id=alert_id)
    
    vote = Vote(
        alert_id=alert_id,
        user_id=request.user.id,
        resolved=True
    )

    vote.save()
    alert.save()

    return redirect('alerts_detail', alert_id=alert_id)

def mark_ongoing(request, alert_id):
    vote = Vote.objects.filter(
        alert_id=alert_id,
        user_id=request.user.id
    ).first()

    alert = Alert.objects.filter(id=alert_id).first()

    if (vote):
        vote.resolved=False
        vote.save()
        alert.save()
        return redirect('alerts_detail', alert_id=alert_id)

    
    vote = Vote(
        alert_id=alert_id,
        user_id=request.user.id,
        resolved=False
    )

    vote.save()
    alert.save()

    return redirect('alerts_detail', alert_id=alert_id)


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
        return redirect('alerts_detail', alert_id=alert_id)


    alert = Alert.objects.filter(id=alert_id, deleted_at=None).first()
    user_id = request.user.id

    all_votes = Vote.objects.filter(alert_id=alert_id).values('resolved', 'created_at', 'updated_at')
    votes = []
    resolved_last = None
    ongoing_last = None
    resolved_as_of = None
    ongoing_as_of = None

    for vote in all_votes:
        votes.append(vote['resolved'])

        if vote['resolved'] == True:
            resolved_last = vote['updated_at']
        if vote['resolved'] == False:
            ongoing_last = vote['updated_at']

    resolved_tally = votes.count(True)
    ongoing_tally = votes.count(False)


    current_user = Alert.objects.filter(
        id=alert_id
    ).values(
        'user__id',
        'user__username',
        'user__first_name',
    )

    alert = Alert.objects.filter(id=alert_id).first()

    return render(
        request, 'comments/new.html',
        {
            'alert': alert,
            'current_user': current_user,
            'resolved_tally': resolved_tally,
            'ongoing_tally': ongoing_tally,
            'resolved_last': resolved_last,
            'ongoing_last': ongoing_last,
        }
    )