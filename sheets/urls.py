from django.urls import path

from . import views

urlpatterns = [
    path("teams/", views.AllTeamsView.as_view(), name='teams'),
    path("teams/<int:pk>", views.TeamDetailView.as_view(), name='team'),
]