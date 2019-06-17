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

import collections
import uuid
import boto3

from .models import Line, Station, Trip
# from .forms import OccasionForm


def home(request):
    return render(request, 'home.html')


def about(request):
    return render(request, 'about.html')


def signup(request):
    error_message = ''
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
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

def trips_new(request, line_id, station_id):
    line = Line.objects.filter(id=line_id, deleted_at=None).first()
    station = Station.objects.filter(id=station_id, deleted_at=None).first()

    return render(request, 'trips/new.html', {'line': line, 'station': station})

def trips_edit(request):
    trips = Trip.objects.filter(deleted_at=None).all()
    # lines = Line.objects.filter()
    return render(request, 'trips/edit.html', {'trips': trips})

