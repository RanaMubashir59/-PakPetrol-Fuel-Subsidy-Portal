from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from .models import BikeUser, PetrolStation, City
import re


class BikeUserRegistrationForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    full_name = forms.CharField(max_length=150)
    cnic = forms.CharField(max_length=15, help_text="Format: 12345-1234567-1")
    phone = forms.CharField(max_length=15)
    city = forms.ModelChoiceField(queryset=City.objects.all())
    bike_registration = forms.CharField(max_length=20)
    bike_type = forms.ChoiceField(choices=BikeUser.BIKE_TYPES)

    def clean_cnic(self):
        cnic = self.cleaned_data['cnic']
        if not re.match(r'^\d{5}-\d{7}-\d$', cnic):
            raise forms.ValidationError("CNIC must be in format: 12345-1234567-1")
        if BikeUser.objects.filter(cnic=cnic).exists():
            raise forms.ValidationError("This CNIC is already registered.")
        return cnic

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already taken.")
        return username

    def clean_bike_registration(self):
        bike_reg = self.cleaned_data['bike_registration'].upper()
        if BikeUser.objects.filter(bike_registration=bike_reg).exists():
            raise forms.ValidationError("This bike registration is already registered.")
        return bike_reg

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


class StationRegistrationForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    station_name = forms.CharField(max_length=200)
    owner_name = forms.CharField(max_length=100)
    phone = forms.CharField(max_length=15)
    city = forms.ModelChoiceField(queryset=City.objects.all())
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
    license_no = forms.CharField(max_length=50)

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already taken.")
        return username

    def clean_license_no(self):
        lic = self.cleaned_data['license_no']
        if PetrolStation.objects.filter(license_no=lic).exists():
            raise forms.ValidationError("This license number is already registered.")
        return lic

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


class RedemptionForm(forms.Form):
    qr_token = forms.CharField(max_length=40, label="QR Token / Code")
    litres = forms.DecimalField(min_value=0.1, max_value=10, decimal_places=2, label="Litres to Dispense")

    def clean_qr_token(self):
        token = self.cleaned_data['qr_token'].strip()
        return token


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
