from django.contrib import admin
from .models import (
    City, FuelPrice, PetrolStation, BikeUser, CreditAccount,
    QRToken, Transaction, FraudFlag
)

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(FuelPrice)
class FuelPriceAdmin(admin.ModelAdmin):
    list_display = ['fuel_type', 'price_per_litre', 'effective_date', 'updated_by']
    list_filter = ['fuel_type', 'effective_date']
    search_fields = ['fuel_type']
    readonly_fields = ['created_at']

@admin.register(PetrolStation)
class PetrolStationAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'status', 'owner_name', 'registered_at']
    list_filter = ['status', 'city', 'registered_at']
    search_fields = ['name', 'owner_name', 'license_no']
    readonly_fields = ['api_key', 'registered_at']
    fieldsets = (
        ('Basic Info', {'fields': ('user', 'name', 'city', 'address')}),
        ('Owner Details', {'fields': ('owner_name', 'phone')}),
        ('License', {'fields': ('license_no', 'api_key')}),
        ('Status', {'fields': ('status', 'registered_at')}),
    )

@admin.register(BikeUser)
class BikeUserAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'cnic', 'city', 'is_verified', 'is_active', 'registered_at']
    list_filter = ['is_verified', 'is_active', 'city', 'registered_at']
    search_fields = ['full_name', 'cnic', 'bike_registration']
    readonly_fields = ['registered_at']
    fieldsets = (
        ('User', {'fields': ('user',)}),
        ('Personal Info', {'fields': ('full_name', 'cnic', 'phone', 'city')}),
        ('Bike Details', {'fields': ('bike_registration', 'bike_type')}),
        ('Status', {'fields': ('is_verified', 'is_active', 'registered_at')}),
    )

@admin.register(CreditAccount)
class CreditAccountAdmin(admin.ModelAdmin):
    list_display = ['bike_user', 'balance', 'monthly_quota', 'total_credited', 'total_redeemed']
    list_filter = ['last_reset', 'created_at']
    search_fields = ['bike_user__full_name']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(QRToken)
class QRTokenAdmin(admin.ModelAdmin):
    list_display = ['token', 'bike_user', 'status', 'created_at', 'expires_at']
    list_filter = ['status', 'created_at', 'expires_at']
    search_fields = ['token', 'bike_user__full_name']
    readonly_fields = ['token', 'created_at']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'bike_user', 'station', 'amount_deducted', 'status', 'created_at']
    list_filter = ['status', 'created_at', 'station']
    search_fields = ['transaction_id', 'bike_user__full_name', 'station__name']
    readonly_fields = ['transaction_id', 'created_at']

@admin.register(FraudFlag)
class FraudFlagAdmin(admin.ModelAdmin):
    list_display = ['bike_user', 'reason', 'resolved', 'created_at']
    list_filter = ['reason', 'resolved', 'created_at']
    search_fields = ['bike_user__full_name', 'details']
    readonly_fields = ['created_at']
