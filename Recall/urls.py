from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Auth
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', views.MeView.as_view(), name='me'),

    # Photos
    path('photos/', views.PhotoListView.as_view(), name='photo-list'),
    path('photos/upload/', views.PhotoUploadView.as_view(), name='photo-upload'),
    path('photos/<int:pk>/', views.PhotoDeleteView.as_view(), name='photo-delete'),

    # Search
    path('search/', views.SearchView.as_view(), name='search'),

    # Stats
    path('stats/', views.StatsView.as_view(), name='stats'),
]