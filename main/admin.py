from django.contrib import admin

from .models import Alert, Comment, Trip, Vote, Line, Station

admin.site.register(Alert)
admin.site.register(Comment)
admin.site.register(Trip)
admin.site.register(Vote)
admin.site.register(Line)
admin.site.register(Station)