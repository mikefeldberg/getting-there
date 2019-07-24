import collections
import uuid
import boto3
import pytz
import calendar
import time

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
from django.db.models import Q

from copy import copy
from datetime import datetime, timedelta, timezone

from .models import Line, Station, Trip, Alert, Comment, Vote, Arrival


def convert_datetime_to_timestamp(dt):
    target_tz = pytz.timezone("America/New_York")
    dt = dt.astimezone(target_tz)

    return dt.strftime("%-I:%M%p")


def home(request):
    trips = Trip.objects.filter(
        user_id=request.user.id,
        deleted_at=None
    ).values(
        'id',
        'line__id',
        'line__route',
        'station__id',
        'station__name',
        'station__mta_downtown_id',
        'station__mta_uptown_id',
        'direction',
        'trip_type',
    ).all()


    for trip in trips:
        trip['resolved'] = True
        trip['status_updated_at'] = None
        trip['mta_uid'] = ''

        mta_uptown_id = Station.objects.filter(
            id=trip['station__id'],
        ).values(
            'mta_uptown_id'
        ).first()

        mta_uid = mta_uptown_id['mta_uptown_id'][0:3]

        trip['mta_uid'] = mta_uid

        trip['alert_count'] = Alert.objects.filter(
            station_id=trip['station__id'],
            line_id=trip['line__id'],
            updated_at__gt=datetime.now() - timedelta(minutes=20),
            deleted_at=None,
        ).count()

        last_alert = Alert.objects.filter(
            station_id=trip['station__id'],
            line_id=trip['line__id'],
            updated_at__gt=datetime.now() - timedelta(minutes=20),
            deleted_at=None,
        ).order_by(
            '-updated_at',
        ).values(
            'id',
            'updated_at',
        ).last()

        if last_alert:
            trip['resolved'] = False
            trip['status_updated_at'] = last_alert['updated_at']

            last_vote = Vote.objects.filter(
                alert_id=last_alert['id']
            ).order_by(
                '-updated_at'
            ).values(
                'resolved',
                'updated_at'
            ).last()

            if last_vote:
                trip['resolved'] = last_vote['resolved']
                # trip['status_updated_at'] = last_vote['updated_at']

    for trip in trips:
        if trip['direction'] == 'Uptown':
            stop_id = trip['station__mta_uptown_id']
        else:
            stop_id = trip['station__mta_downtown_id']

        arrivals = Arrival.objects.filter(
            stop_id=stop_id,
            route=trip['line__route'],
            arrivaltime__gt=datetime.now(),
        ).order_by(
            'arrivaltime',
        ).values(
            'arrivaltime',
        ).all()[:3]

        arrival_times = []

        # For testing
        # arrival_times.append(convert_datetime_to_timestamp(datetime.now()))
        # arrival_times.append(convert_datetime_to_timestamp(datetime.now()))
        # arrival_times.append(convert_datetime_to_timestamp(datetime.now()))

        for arrival in arrivals:
            arrival_times.append(convert_datetime_to_timestamp(arrival['arrivaltime']))

        trip['next_three'] = arrival_times

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

    for station in stations:
        station.mta_uid = station.mta_uptown_id[0:3]

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
# def trips_new(request, line_id, station_id):
def trips_new(request, mta_uid, line_id):
    if request.method == 'POST':
        data = request.POST.copy()
        del data['csrfmiddlewaretoken']
        trip_type = data.pop('trip_type')[0]

        for item in data.keys():
            route_name, direction = item.split('_')
            if trip_type == 'Both':
                line = Line.objects.filter(id=route_name).first()
                station = Station.objects.filter(mta_uptown_id=mta_uid + 'N', line_id=line.id).first()
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
                station = Station.objects.filter(mta_uptown_id=mta_uid + 'N', line_id=line.id).first()
                trip = Trip(
                    user=request.user,
                    trip_type=trip_type,
                    station_id=station.id,
                    line_id=line.id,
                    direction=direction,
                )

                trip.save()

        return redirect('lines_detail', line_id=line_id)

    # line = Line.objects.filter(id=line_id, deleted_at=None).first()
    current_line = Line.objects.filter(id=line_id).first()
    station_id_obj = Station.objects.filter(
        line=current_line,
        mta_uptown_id=mta_uid + 'N'
    ).values('id').first()
    station_id = station_id_obj['id']
    
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

    return render(request, 'trips/new.html', {'station': station, 'train_lines': train_lines, 'line_id': line_id, })


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


def alerts_index(request, mta_uid, line_id):
    if request.method == 'POST':
        data = dict(request.POST.copy())
        del data['csrfmiddlewaretoken']

        current_line = Line.objects.filter(id=line_id).first()

        station_id_obj = Station.objects.filter(
            line=current_line,
            mta_uptown_id=mta_uid + 'N'
        ).values('id').first()

        station_id = station_id_obj['id']

        if 'line_ids' in data and data['line_ids'][0]:
            filtered_lines = data['line_ids']
        else:
            filtered_lines = [line_id]

        if data['stations_away'][0]:
            station_radius = int(data['stations_away'][0])
        else:
            station_radius = 0

        if data['age_of_alert'][0]:
            age_of_alert = int(data['age_of_alert'][0])
        else:
            age_of_alert = 15

        current_station = Station.objects.filter(id=station_id).values(
            'mta_uptown_id',
            'mta_downtown_id'
        ).last()

        line_filters = {}

        for line_id in filtered_lines:
            line_data = {}
            uptown_stations = Station.objects.filter(
                line_id=line_id,
                mta_uptown_id=current_station['mta_uptown_id'],
                deleted_at=None
            ).values(
                'uptown_stop_number',
            ).last()

            if uptown_stations:
                uptown_stop_number = uptown_stations['uptown_stop_number']
                uptown_min = uptown_stop_number - station_radius
                uptown_max = uptown_stop_number + station_radius
                line_data['uptown_range'] = list(range(uptown_min, uptown_max + 1))

            downtown_stations = Station.objects.filter(
                line_id=line_id,
                mta_downtown_id=current_station['mta_downtown_id'],
                deleted_at=None
            ).values(
                'downtown_stop_number',
            ).last()

            if downtown_stations:
                downtown_stop_number = downtown_stations['downtown_stop_number']
                downtown_min = downtown_stop_number - station_radius
                downtown_max = downtown_stop_number + station_radius
                line_data['downtown_range'] = list(range(downtown_min, downtown_max + 1))

            if line_data:
                line_filters[line_id] = line_data

        alerts = []

        for line_id, line_filter in line_filters.items():
            uptown_alerts = Alert.objects.filter(
                station__uptown_stop_number__in=line_filter['uptown_range'],
                line_id=line_id,
                direction='Uptown',
                updated_at__gt=datetime.now() - timedelta(minutes=age_of_alert),
                deleted_at=None,
            ).values(
                'id',
                'line__id',
                'line__name',
                'line__color',
                'line__text_color',
                'line__express',
                'station__name',
                'direction',
                'message',
            ).all()

            alerts.append(list(uptown_alerts))

            downtown_alerts = Alert.objects.filter(
                station__downtown_stop_number__in=line_filter['downtown_range'],
                line_id=line_id,
                direction='Downtown',
                updated_at__gt=datetime.now() - timedelta(minutes=age_of_alert),
                deleted_at=None,
            ).values(
                'id',
                'line__id',
                'line__name',
                'line__color',
                'line__text_color',
                'line__express',
                'station__name',
                'direction',
                'message',
            ).all()

            alerts.append(list(downtown_alerts))

        station_display = Station.objects.filter(id=station_id).values('name').first()

        stations = Station.objects.filter(
            Q(mta_uptown_id=mta_uid+'N') | Q(mta_downtown_id=mta_uid+'S')
        ).values(
            'id',
            'name',
            'line_id',
        ).all()

        line_ids = [i['line_id'] for i in stations]

        lines = Line.objects.filter(
            id__in=line_ids,
            deleted_at=None
        ).values(
            'id',
            'route',
            'group_id',
            'name',
            'express',
            'color',
            'text_color',
        ).all()

        distance = list(range(1,11))

        alerts = sum(alerts, [])

        # return redirect('alerts_index', mta_uid=mta_uid, line_id=line_id, {'alerts':alerts})
        return render(request, 'alerts/index.html', {
            'alerts': alerts,
            'line_id': line_id,
            'lines': lines,
            'filtered_lines': filtered_lines,
            'distance': distance,
            'station_display': station_display['name'],
            'mta_uid': mta_uid,
        })

    stations = Station.objects.filter(
        Q(mta_uptown_id=mta_uid+'N') | Q(mta_downtown_id=mta_uid+'S')
    ).values(
        'id',
        'name',
        'line_id',
    ).all()

    station_ids = []

    for item in stations:
        station_ids.append(item['id'])

    alerts = Alert.objects.filter(
        station__id__in=station_ids,
        deleted_at=None
    ).values(
        'id',
        'line__id',
        'line__name',
        'line__color',
        'line__text_color',
        'line__express',
        'station__name',
        'ongoing',
        'direction',
        'created_at',
        'updated_at',
        'message',
    ).all()

    station_display = Station.objects.filter(id=station_ids[0]).values('name').first()

    line_ids = [i['line_id'] for i in stations]

    lines = Line.objects.filter(
        id__in=line_ids,
        deleted_at=None
    ).values(
        'id',
        'route',
        'group_id',
        'name',
        'express',
        'color',
        'text_color',
    ).all()

    distance = list(range(1,11))

    return render(request, 'alerts/index.html', {
        'alerts': alerts,
        'line_id': line_id,
        'lines': lines,
        'distance': distance,
        'station_display': station_display['name'],
        'mta_uid': mta_uid,
    })


@login_required
def alerts_new(request, mta_uid, line_id):
    if request.method == 'POST':
        current_line = Line.objects.filter(id=line_id).first()
        station_id_obj = Station.objects.filter(
            line=current_line,
            mta_uptown_id=mta_uid + 'N'
        ).values('id').first()
        station_id = station_id_obj['id']
        
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

        return redirect('alerts_index', mta_uid=mta_uid, line_id=line_id)

    current_line = Line.objects.filter(id=line_id).first()
    station_id_obj = Station.objects.filter(
        line=current_line,
        mta_uptown_id=mta_uid + 'N'
    ).values('id').first()
    station_id = station_id_obj['id']

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

    origin_station = Alert.objects.filter(id=alert_id, deleted_at=None).values(
        'station__id',
        'station__name',
        'line__id',
    ).first()

    print(origin_station)
    mta_uptown_id = Station.objects.filter(id=origin_station['station__id']).values('mta_uptown_id').first()
    print(mta_uptown_id)
    origin_station['mta_uid'] = mta_uptown_id['mta_uptown_id'][0:3]
    print(origin_station)

    user_id = request.user.id

    all_votes = Vote.objects.filter(alert_id=alert_id).values('resolved', 'created_at', 'updated_at')
    votes = []
    resolved_last = None
    ongoing_last = None
    resolved_as_of = None
    ongoing_as_of = None

    for vote in all_votes:
        votes.append(vote['resolved'])

    resolved_tally = votes.count(True)
    ongoing_tally = votes.count(False)

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
            'user_id': user_id,
            'origin_station': origin_station,
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
        alert.ongoing=False
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
        alert.ongoing=True
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