from django.urls import path

from . import views

urlpatterns = [
    path("teams/", views.AllTeamsView.as_view(), name='teams'),
    path("teams/<int:pk>", views.TeamDetailView.as_view(), name='team'),
    path('matches/', views.AllMatchesViewSlim.as_view(), name='matches'),
    path('matches/detailed/', views.AllMatchesView.as_view(), name='matches-detail'),
    path('matches/archived/', views.AllMatchesView.as_view(), name='matches-detail'),
    path('matches/<int:pk>/', views.MatchView.as_view(), name='match-detail'),
    path('matches/<int:pk>/results/', views.MatchResultsView.as_view(), name='match-results'),
]