from django.urls import path
from . import views

app_name = 'core'
urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('manage/', views.owner_lookup, name='owner_lookup'),
    path('reports/', views.browse, name='browse'),
    path('reports/new/<str:kind>/', views.submit, name='submit'),
    path('reports/confirmation/', views.confirmation, name='confirmation'),
    path('reports/<uuid:pk>/', views.detail, name='detail'),
    path('reports/<uuid:pk>/matches/', views.matches, name='matches'),
    path('reports/<uuid:pk>/image/', views.image, name='image'),
    path('reports/<uuid:pk>/message/', views.claim, name='claim'),
    path('reports/<uuid:pk>/abuse/', views.abuse, name='abuse'),
    path('reports/<uuid:pk>/manage/', views.manage, name='manage'),
]
