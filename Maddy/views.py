from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Count
from django.views.decorators.http import require_POST
import json, qrcode, io, base64

from .models import (
    BikeUser, PetrolStation, CreditAccount, QRToken,
    Transaction, FuelPrice, City, FraudFlag
)
from .forms import (
    BikeUserRegistrationForm, StationRegistrationForm,
    RedemptionForm, LoginForm
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_user_role(user):
    if user.is_superuser or user.is_staff:
        return 'admin'
    if hasattr(user, 'bike_profile'):
        return 'rider'
    if hasattr(user, 'station'):
        return 'station'
    return None


def generate_qr_image(data):
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0a2540", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode()


def check_fraud(bike_user, station, amount):
    """Basic fraud detection checks"""
    today = timezone.now().date()
    now = timezone.now()

    # Check: same user transacted less than 30 mins ago
    recent = Transaction.objects.filter(
        bike_user=bike_user,
        created_at__gte=now - timezone.timedelta(minutes=30),
        status='success'
    )
    if recent.exists():
        FraudFlag.objects.create(
            bike_user=bike_user,
            reason='rapid_redemption',
            details=f"Transaction attempted within 30 mins of last one."
        )
        return False, "Fraud alert: Too soon since last redemption."

    # Check: same user in different city today
    today_txn = Transaction.objects.filter(
        bike_user=bike_user,
        created_at__date=today,
        status='success'
    ).exclude(station__city=station.city).first()
    if today_txn:
        FraudFlag.objects.create(
            bike_user=bike_user,
            reason='multi_city',
            details=f"Same-day transactions in different cities."
        )
        return False, "Fraud alert: Multi-city redemption detected."

    return True, "OK"


# ─── Public Views ─────────────────────────────────────────────────────────────

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    stats = {
        'total_riders': BikeUser.objects.filter(is_verified=True).count(),
        'total_stations': PetrolStation.objects.filter(status='active').count(),
        'total_transactions': Transaction.objects.filter(status='success').count(),
    }
    return render(request, 'home.html', {'stats': stats})


def register_rider(request):
    form = BikeUserRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        user = User.objects.create_user(
            username=d['username'], email=d['email'], password=d['password']
        )
        city = d['city']
        rider = BikeUser.objects.create(
            user=user, cnic=d['cnic'], full_name=d['full_name'],
            phone=d['phone'], city=city,
            bike_registration=d['bike_registration'].upper(),
            bike_type=d['bike_type']
        )
        CreditAccount.objects.create(bike_user=rider, monthly_quota=1500.00)
        messages.success(request, "Registration successful! Please wait for admin verification.")
        return redirect('login')
    return render(request, 'register_rider.html', {'form': form})


def register_station(request):
    form = StationRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        user = User.objects.create_user(
            username=d['username'], email=d['email'], password=d['password']
        )
        PetrolStation.objects.create(
            user=user, name=d['station_name'], owner_name=d['owner_name'],
            phone=d['phone'], city=d['city'], address=d['address'],
            license_no=d['license_no']
        )
        messages.success(request, "Station registered! Awaiting admin approval.")
        return redirect('login')
    return render(request, 'register_station.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect('dashboard')
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


# ─── Dashboard Router ─────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    role = get_user_role(request.user)
    if role == 'rider':
        return redirect('rider_dashboard')
    elif role == 'station':
        return redirect('station_dashboard')
    elif role == 'admin':
        return redirect('admin_dashboard')
    return render(request, 'no_role.html')


# ─── Rider Views ──────────────────────────────────────────────────────────────

@login_required
def rider_dashboard(request):
    if not hasattr(request.user, 'bike_profile'):
        return redirect('dashboard')
    rider = request.user.bike_profile
    account = rider.get_or_create_account()
    recent_txns = rider.transactions.filter(status='success').order_by('-created_at')[:10]
    current_price = FuelPrice.current_price()
    litres_available = float(account.balance) / float(current_price) if current_price else 0

    # Expire old QR tokens
    QRToken.objects.filter(bike_user=rider, status='active', expires_at__lt=timezone.now()).update(status='expired')

    return render(request, 'rider_dashboard.html', {
        'rider': rider,
        'account': account,
        'recent_txns': recent_txns,
        'current_price': current_price,
        'litres_available': round(litres_available, 2),
    })


@login_required
def generate_qr(request):
    if not hasattr(request.user, 'bike_profile'):
        return JsonResponse({'error': 'Not a rider'}, status=403)
    rider = request.user.bike_profile

    if not rider.is_verified:
        return JsonResponse({'error': 'Account not yet verified by admin.'}, status=403)

    account = rider.get_or_create_account()
    if account.balance <= 0:
        return JsonResponse({'error': 'No balance available.'}, status=400)

    # Expire old active tokens
    QRToken.objects.filter(bike_user=rider, status='active').update(status='expired')

    token = QRToken.objects.create(
        bike_user=rider,
        expires_at=timezone.now() + timezone.timedelta(minutes=10)
    )

    qr_data = str(token.token)
    qr_image = generate_qr_image(qr_data)

    return JsonResponse({
        'token': qr_data,
        'qr_image': qr_image,
        'expires_in': 600,
        'balance': str(account.balance),
    })


# ─── Station Views ────────────────────────────────────────────────────────────

@login_required
def station_dashboard(request):
    if not hasattr(request.user, 'station'):
        return redirect('dashboard')
    station = request.user.station
    recent_txns = station.transactions.order_by('-created_at')[:15]
    today_txns = station.transactions.filter(
        created_at__date=timezone.now().date(), status='success'
    )
    today_total = today_txns.aggregate(Sum('amount_deducted'))['amount_deducted__sum'] or 0
    today_litres = today_txns.aggregate(Sum('litres_dispensed'))['litres_dispensed__sum'] or 0

    return render(request, 'portal/station_dashboard.html', {
        'station': station,
        'recent_txns': recent_txns,
        'today_total': today_total,
        'today_litres': round(float(today_litres), 2),
        'today_count': today_txns.count(),
        'current_price': FuelPrice.current_price(),
    })


@login_required
def verify_qr(request):
    """AJAX: station verifies QR and gets rider info"""
    if not hasattr(request.user, 'station'):
        return JsonResponse({'error': 'Not a station'}, status=403)

    station = request.user.station
    if station.status != 'active':
        return JsonResponse({'error': 'Your station is not active.'}, status=403)

    token_str = request.GET.get('token', '').strip()
    if not token_str:
        return JsonResponse({'error': 'No token provided.'}, status=400)

    try:
        qr_token = QRToken.objects.get(token=token_str)
    except QRToken.DoesNotExist:
        return JsonResponse({'error': 'Invalid QR token.'}, status=404)

    if not qr_token.is_valid():
        return JsonResponse({'error': f'QR token is {qr_token.status}.'}, status=400)

    rider = qr_token.bike_user
    account = rider.get_or_create_account()
    current_price = FuelPrice.current_price()

    return JsonResponse({
        'rider_name': rider.full_name,
        'cnic': rider.cnic[:5] + '-XXXXXXX-X',
        'bike_reg': rider.bike_registration,
        'bike_type': rider.bike_type,
        'balance': str(account.balance),
        'litres_possible': str(round(float(account.balance) / float(current_price), 2)),
        'fuel_price': str(current_price),
        'token': token_str,
    })


@login_required
@require_POST
def process_redemption(request):
    """AJAX: process the actual fuel redemption"""
    if not hasattr(request.user, 'station'):
        return JsonResponse({'error': 'Not a station'}, status=403)

    station = request.user.station
    if station.status != 'active':
        return JsonResponse({'error': 'Station not active.'}, status=403)

    try:
        data = json.loads(request.body)
        token_str = data.get('token')
        litres = float(data.get('litres', 0))
    except Exception:
        return JsonResponse({'error': 'Invalid data.'}, status=400)

    if litres <= 0 or litres > 10:
        return JsonResponse({'error': 'Litres must be between 0.1 and 10.'}, status=400)

    try:
        qr_token = QRToken.objects.get(token=token_str)
    except QRToken.DoesNotExist:
        return JsonResponse({'error': 'Invalid token.'}, status=404)

    if not qr_token.is_valid():
        return JsonResponse({'error': f'Token is {qr_token.status}.'}, status=400)

    rider = qr_token.bike_user
    account = rider.get_or_create_account()
    current_price = float(FuelPrice.current_price())
    amount = round(litres * current_price, 2)

    # Fraud check
    ok, msg = check_fraud(rider, station, amount)
    if not ok:
        return JsonResponse({'error': msg}, status=400)

    if float(account.balance) < amount:
        return JsonResponse({'error': f'Insufficient balance. Available: Rs.{account.balance}'}, status=400)

    balance_before = account.balance
    success, deduct_msg = account.deduct(amount)
    if not success:
        return JsonResponse({'error': deduct_msg}, status=400)

    # Mark QR as used
    qr_token.status = 'used'
    qr_token.used_at = timezone.now()
    qr_token.save()

    # Create transaction record
    txn = Transaction.objects.create(
        bike_user=rider,
        station=station,
        qr_token=qr_token,
        amount_deducted=amount,
        litres_dispensed=litres,
        fuel_price_at_time=current_price,
        balance_before=balance_before,
        balance_after=account.balance,
        status='success'
    )

    return JsonResponse({
        'success': True,
        'transaction_id': str(txn.transaction_id)[:12].upper(),
        'rider_name': rider.full_name,
        'litres': litres,
        'amount': amount,
        'balance_after': str(account.balance),
        'station': station.name,
        'timestamp': txn.created_at.strftime('%d %b %Y %H:%M'),
    })


# ─── Admin Views ──────────────────────────────────────────────────────────────

@login_required
def admin_dashboard(request):
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('dashboard')

    total_riders = BikeUser.objects.count()
    verified_riders = BikeUser.objects.filter(is_verified=True).count()
    total_stations = PetrolStation.objects.count()
    active_stations = PetrolStation.objects.filter(status='active').count()
    total_txns = Transaction.objects.filter(status='success').count()
    total_amount = Transaction.objects.filter(status='success').aggregate(
        Sum('amount_deducted'))['amount_deducted__sum'] or 0
    total_litres = Transaction.objects.filter(status='success').aggregate(
        Sum('litres_dispensed'))['litres_dispensed__sum'] or 0
    pending_riders = BikeUser.objects.filter(is_verified=False).order_by('-registered_at')[:10]
    pending_stations = PetrolStation.objects.filter(status='pending').order_by('-registered_at')[:10]
    fraud_flags = FraudFlag.objects.filter(resolved=False).order_by('-created_at')[:10]
    recent_txns = Transaction.objects.filter(status='success').order_by('-created_at')[:15]

    # City-wise stats
    city_stats = Transaction.objects.filter(status='success').values(
        'station__city__name'
    ).annotate(
        count=Count('id'),
        total=Sum('amount_deducted')
    ).order_by('-total')[:6]

    current_price = FuelPrice.current_price()

    return render(request, 'admin_dashboard.html', {
        'total_riders': total_riders, 'verified_riders': verified_riders,
        'total_stations': total_stations, 'active_stations': active_stations,
        'total_txns': total_txns, 'total_amount': total_amount,
        'total_litres': round(float(total_litres), 1),
        'pending_riders': pending_riders, 'pending_stations': pending_stations,
        'fraud_flags': fraud_flags, 'recent_txns': recent_txns,
        'city_stats': city_stats, 'current_price': current_price,
    })


@login_required
def verify_rider(request, rider_id):
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    rider = get_object_or_404(BikeUser, id=rider_id)
    rider.is_verified = True
    rider.save()
    # Credit first month quota
    rider.get_or_create_account().credit_monthly_quota()
    messages.success(request, f"{rider.full_name} verified and credited Rs.1500.")
    return redirect('admin_dashboard')


@login_required
def approve_station(request, station_id):
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    station = get_object_or_404(PetrolStation, id=station_id)
    station.status = 'active'
    station.save()
    messages.success(request, f"{station.name} approved.")
    return redirect('admin_dashboard')


@login_required
def set_fuel_price(request):
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    if request.method == 'POST':
        price = request.POST.get('price')
        try:
            FuelPrice.objects.create(
                price_per_litre=float(price),
                fuel_type='petrol',
                updated_by=request.user
            )
            messages.success(request, f"Petrol price updated to Rs.{price}/L")
        except Exception as e:
            messages.error(request, str(e))
    return redirect('admin_dashboard')


@login_required
def credit_all_riders(request):
    """Admin credits all verified riders their monthly quota"""
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    credited = 0
    for rider in BikeUser.objects.filter(is_verified=True, is_active=True):
        ok, _ = rider.get_or_create_account().credit_monthly_quota()
        if ok:
            credited += 1
    messages.success(request, f"Credited {credited} riders with monthly quota.")
    return redirect('admin_dashboard')


# ─── API endpoints ────────────────────────────────────────────────────────────

def api_fuel_price(request):
    price = FuelPrice.current_price()
    return JsonResponse({'petrol_price': str(price), 'currency': 'PKR'})
