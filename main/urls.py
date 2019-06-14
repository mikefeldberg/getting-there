from django.urls import path, include
from . import views
from django.contrib.auth.views import LoginView

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('accounts/login/', LoginView.as_view(), name='login'),
    path('accounts/signup/', views.signup, name='signup'),
]
