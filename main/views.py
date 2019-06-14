from django.shortcuts import render, redirect
from django.http import HttpResponse

def home(request):
    return HttpResponse('Welcome to the home page, homey')

def about(request):
    return HttpResponse('Welcome to the about page')

