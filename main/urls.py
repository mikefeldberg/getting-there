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
    path('trips/new/<str:mta_uid>/<int:line_id>', views.trips_new, name='trips_new'),
    path('trips/edit/', views.trips_edit, name='trips_edit'),
    path('alerts/new/<str:mta_uid>/<int:line_id>/', views.alerts_new, name='alerts_new'),
    path('alerts/<str:mta_uid>/<int:line_id>/', views.alerts_index, name='alerts_index'),
    path('alerts/<str:mta_uid>/', views.alerts_detail, name='alerts_detail'),
    path('alerts/<int:alert_id>/add_comment', views.comments_new, name='comments_new'),
    path('alerts/<int:alert_id>/mark_resolved', views.mark_resolved, name='mark_resolved'),
    path('alerts/<int:alert_id>/mark_ongoing', views.mark_ongoing, name='mark_ongoing'),
]