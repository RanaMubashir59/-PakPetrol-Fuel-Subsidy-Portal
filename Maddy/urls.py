from django.contrib import admin
from django.urls import path
from Maddy import views

urlpatterns = [
path('', views.home, name='home'),
    path('register/rider/', views.register_rider, name='register_rider'),
    path('register/station/', views.register_station, name='register_station'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('survey/', views.survey_view, name='survey'),

    # Rider
    path('rider/', views.rider_dashboard, name='rider_dashboard'),
    path('rider/generate-qr/', views.generate_qr, name='generate_qr'),

    # Station
    path('station/', views.station_dashboard, name='station_dashboard'),
    path('station/verify-qr/', views.verify_qr, name='verify_qr'),
    path('station/redeem/', views.process_redemption, name='process_redemption'),

    # Admin
    path('admin-portal/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-portal/verify-rider/<int:rider_id>/', views.verify_rider, name='verify_rider'),
    path('admin-portal/approve-station/<int:station_id>/', views.approve_station, name='approve_station'),
    path('admin-portal/set-price/', views.set_fuel_price, name='set_fuel_price'),
    path('admin-portal/credit-all/', views.credit_all_riders, name='credit_all_riders'),

    # API
    path('api/fuel-price/', views.api_fuel_price, name='api_fuel_price'),
    ]