from django.urls import path, include
from . import views
from django.contrib.auth.views import LoginView

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('accounts/login/', LoginView.as_view(), name='login'),
    path('accounts/signup/', views.signup, name='signup'),
    path('lines/', views.lines_index, name='lines_index'),
    path('lines/<int:line_id>/', views.lines_detail, name='lines_detail'),
    path('trips/new/<int:line_id>/<int:station_id>/', views.trips_new, name='trips_new'),
    path('trips/edit/', views.trips_edit, name='trips_edit'),
    path('stations/alerts/<int:station_id>/<int:line_id>/', views.alerts_index, name='alerts_index'),
    path('alerts/new/<int:station_id>/<int:line_id>/', views.alerts_new, name='alerts_new'),
    path('alerts/<int:alert_id>/', views.alerts_detail, name='alerts_detail'),
    path('alerts/<int:alert_id>/add_comment', views.comments_new, name='comments_new'),
]
