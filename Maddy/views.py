from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Count
from django.views.decorators.http import require_POST, require_GET
import json, qrcode, io, base64, logging
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
from django.conf import settings

# 🔗 NEW: Import structured analytics framework
from analysis.analytics import enhance_analytics_payload, run_structured_analysis, make_json_serializable
from analysis.google_sheets_helper import load_google_sheet_data

from .models import (
    BikeUser, PetrolStation, CreditAccount, QRToken,
    Transaction, FuelPrice, City, FraudFlag
)
from .forms import (
    BikeUserRegistrationForm, StationRegistrationForm,
    RedemptionForm, LoginForm
)

logger = logging.getLogger(__name__)


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


# ─── Analytics Configuration ────────────────────────────────────────────────

ANALYTICS_CSV_PATH = Path(settings.BASE_DIR) / "analysis" / "google_form_responses.csv"
ANALYTICS_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

# Google Sheets settings (update with your actual Sheet ID)
GOOGLE_SHEET_ID = getattr(settings, 'GOOGLE_SHEET_ID', '1dYw3HbOm8UFDhz-1LKCETV7Igjgqy_YWDSw2xbIMt6E')
GOOGLE_SHEET_RANGE = getattr(settings, 'GOOGLE_SHEET_RANGE', 'Sheet1!A:Z')

LIKERT_MAPPING = {
    "Strongly disagree": 1, "Disagree": 2, "Neutral": 3, "Agree": 4, "Strongly agree": 5,
    "Never": 1, "Rarely": 2, "Sometimes": 3, "Often": 4, "Always": 5,
    "Very Low": 1, "Low": 2, "Medium": 3, "High": 4, "Very High": 5,
}


def map_likert_value(value):
    if pd.isna(value):
        return np.nan
    if isinstance(value, (int, float)):
        return float(value)
    return LIKERT_MAPPING.get(str(value).strip(), np.nan)


def group_value_counts(series):
    return series.fillna("Missing").astype(str).value_counts().to_dict()


def interpret_correlation(r_value):
    """Interpret correlation strength"""
    abs_r = abs(r_value)
    if abs_r >= 0.7: return "Strong"
    elif abs_r >= 0.5: return "Moderate"
    elif abs_r >= 0.3: return "Weak"
    else: return "Very Weak"


# ─── Analytics Data Loading ─────────────────────────────────────────────────

def load_analytics_data():
    """
    Load Google Form responses: Google Sheets → CSV fallback
    Returns DataFrame or None
    """
    try:
        # Try Google Sheets first
        df = load_google_sheet_data(
            sheet_id=GOOGLE_SHEET_ID,
            range_name=GOOGLE_SHEET_RANGE
        )
        if df is not None and not df.empty:
            logger.info(f"✅ Loaded {len(df)} rows from Google Sheets")
            return df
    except Exception as e:
        logger.warning(f"⚠️ Google Sheets load failed: {e}. Falling back to CSV...")
    
    # Fallback to CSV
    try:
        if ANALYTICS_CSV_PATH.exists():
            df = pd.read_csv(ANALYTICS_CSV_PATH)
            df.columns = df.columns.str.strip()
            logger.info(f"✅ Loaded {len(df)} rows from CSV cache")
            return df
    except Exception as e:
        logger.error(f"❌ CSV load failed: {e}")
    
    return None


# ─── Legacy Analytics (Backward Compatible) ─────────────────────────────────

def compute_legacy_analytics_payload(df):
    """
    Original analytics computation - kept for backward compatibility.
    New structured analysis will be merged on top via enhance_analytics_payload().
    """
    payload = {
        "generated_at": timezone.now().isoformat(),
        "descriptive_stats": {},
        "demographics": {},
        "regression": {},
        "correlations": {},
        "anova": {},
        "chi_square": {},
        "awareness": {},
        "subsidy_perception": {},
    }

    # ============= 1. DESCRIPTIVE STATISTICS =============
    numeric_cols = [
        "Age", "How far do you travel daily?",
        "What is your approximate weekly fuel expense? (PKR)",
        "Rising fuel prices affect my daily travel decisions",
        "I reduce my travel due to high fuel costs",
        "High fuel costs negatively impact my academic productivity",
        "I feel financial stress due to fuel expenses",
    ]
    
    desc_stats = {}
    for col in numeric_cols:
        if col in df.columns:
            numeric_series = pd.to_numeric(df[col], errors="coerce").dropna()
            if not numeric_series.empty:
                desc_stats[col] = {
                    "count": int(numeric_series.count()),
                    "mean": float(numeric_series.mean()),
                    "median": float(numeric_series.median()),
                    "mode": float(numeric_series.mode()[0]) if not numeric_series.mode().empty else None,
                    "std_dev": float(numeric_series.std()),
                    "variance": float(numeric_series.var()),
                    "min": float(numeric_series.min()),
                    "max": float(numeric_series.max()),
                }
    payload["descriptive_stats"] = desc_stats

    # ============= 2. DEMOGRAPHICS =============
    dem_cols = ["Age", "Gender", "City"]
    for col in dem_cols:
        if col in df.columns:
            payload["demographics"][col] = group_value_counts(df[col])

    # ============= 3. REGRESSION ANALYSIS =============
    col_fuel_impact = "Rising fuel prices affect my daily travel decisions"
    col_travel_reduction = "I reduce my travel due to high fuel costs"
    
    if col_fuel_impact in df.columns and col_travel_reduction in df.columns:
        x = pd.to_numeric(df[col_fuel_impact], errors="coerce")
        y = pd.to_numeric(df[col_travel_reduction], errors="coerce")
        valid = pd.concat([x, y], axis=1).dropna()
        
        if len(valid) >= 2:
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                valid[col_fuel_impact], valid[col_travel_reduction]
            )
            x_sorted = np.sort(valid[col_fuel_impact].values)
            y_pred = slope * x_sorted + intercept
            
            payload["regression"] = {
                "title": "Regression: Fuel Impact vs Travel Reduction",
                "x_label": "Rising Fuel Prices (Impact Score)",
                "y_label": "Travel Reduction",
                "x": valid[col_fuel_impact].astype(float).tolist(),
                "y": valid[col_travel_reduction].astype(float).tolist(),
                "x_line": x_sorted.tolist(),
                "y_line": y_pred.tolist(),
                "equation": f"Y = {intercept:.4f} + {slope:.4f}X",
                "slope": float(slope), "intercept": float(intercept),
                "r_squared": float(r_value ** 2), "r_value": float(r_value),
                "p_value": float(p_value), "std_err": float(std_err),
                "n_samples": len(valid),
                "significance": "Significant" if p_value < 0.05 else "Not Significant",
            }

    # ============= 4. CORRELATION ANALYSIS =============
    correlation_pairs = [
        ("Age", "What is your approximate weekly fuel expense? (PKR)"),
        (col_fuel_impact, col_travel_reduction),
        ("How far do you travel daily?", "What is your approximate weekly fuel expense? (PKR)"),
    ]
    
    correlations = {}
    for var1, var2 in correlation_pairs:
        if var1 in df.columns and var2 in df.columns:
            v1 = pd.to_numeric(df[var1], errors="coerce").dropna()
            v2 = pd.to_numeric(df[var2], errors="coerce").dropna()
            common_idx = v1.index.intersection(v2.index)
            if len(common_idx) >= 2:
                v1_aligned, v2_aligned = v1[common_idx], v2[common_idx]
                corr, p_val = stats.pearsonr(v1_aligned, v2_aligned)
                correlations[f"{var1[:20]} vs {var2[:20]}"] = {
                    "pearson_r": float(corr), "p_value": float(p_val),
                    "n": len(common_idx), "strength": interpret_correlation(corr),
                }
    payload["correlations"] = correlations

    # ============= 5. ANOVA =============
    grouping_col = "How often do you use your motorcycle?"
    if grouping_col in df.columns and col_fuel_impact in df.columns:
        groups_data, group_names = [], []
        for group_val, subset in df.groupby(df[grouping_col].fillna("Unknown").astype(str)):
            impact_scores = pd.to_numeric(subset[col_fuel_impact], errors="coerce").dropna()
            if len(impact_scores) > 0:
                groups_data.append(impact_scores.values)
                group_names.append(str(group_val))
        
        if len(groups_data) >= 2:
            try:
                f_stat, p_val = stats.f_oneway(*groups_data)
                payload["anova"] = {
                    "title": f"ANOVA: {col_fuel_impact[:40]} by Usage Frequency",
                    "groups": group_names,
                    "f_statistic": float(f_stat), "p_value": float(p_val),
                    "significance": "Significant difference" if p_val < 0.05 else "No significant difference",
                    "group_means": {name: float(np.mean(data)) for name, data in zip(group_names, groups_data)},
                    "group_stds": {name: float(np.std(data)) for name, data in zip(group_names, groups_data)},
                }
            except Exception as e:
                logger.warning(f"ANOVA error: {e}")

    # ============= 6. CHI-SQUARE TESTS =============
    chi_square_tests = [
        ("Subsidy Benefit", "Are you aware of any government fuel subsidy programs?", "A fuel subsidy would improve my mobility"),
        ("Missed Days vs Gender", "Gender", "On average how many days per month do you miss due to fuel issues?"),
    ]
    
    for test_name, row_var, col_var in chi_square_tests:
        if row_var in df.columns and col_var in df.columns:
            try:
                clean_df = df[[row_var, col_var]].dropna()
                if len(clean_df) >= 2:
                    contingency = pd.crosstab(
                        clean_df[row_var].astype(str), 
                        clean_df[col_var].astype(str)
                    )
                    if not contingency.empty and contingency.shape[0] >= 1 and contingency.shape[1] >= 1:
                        chi2, p, dof, _ = stats.chi2_contingency(contingency)
                        payload["chi_square"][test_name] = {
                            "title": f"χ² Test: {test_name}",
                            "contingency": contingency.to_dict(),
                            "z": contingency.values.tolist(),
                            "x": contingency.columns.tolist(),
                            "y": contingency.index.tolist(),
                            "chi2": float(chi2), "p_value": float(p), "dof": int(dof),
                        }
            except Exception as e:
                logger.warning(f"Chi-square error for {test_name}: {e}")

    # ============= 7. AWARENESS & PERCEPTION =============
    awareness_col = "Are you aware of any government fuel subsidy programs?"
    if awareness_col in df.columns:
        payload["awareness"] = {"subsidy_awareness": group_value_counts(df[awareness_col])}

    subsidy_cols = [
        "A fuel subsidy would improve my mobility",
        "A digital system (QR-based) would make subsidy distribution more transparent",
        "I would use a digital fuel subsidy system if available"
    ]
    subsidy_cols_present = [col for col in subsidy_cols if col in df.columns]
    if subsidy_cols_present:
        distributions, means = {}, {}
        for col in subsidy_cols_present:
            scores = pd.to_numeric(df[col], errors="coerce").dropna().astype(float)
            distributions[col] = group_value_counts(df[col])
            means[col] = float(scores.mean()) if not scores.empty else None
        payload["subsidy_perception"] = {"distributions": distributions, "mean_scores": means}
    
    return payload


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


def survey_view(request):
    return render(request, 'Survey.html')


def analytics_dashboard(request):
    csv_exists = ANALYTICS_CSV_PATH.exists()
    if request.method == 'POST' and request.FILES.get('csv_upload'):
        uploaded = request.FILES['csv_upload']
        ANALYTICS_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
        with ANALYTICS_CSV_PATH.open('wb') as csv_file:
            for chunk in uploaded.chunks():
                csv_file.write(chunk)
        messages.success(request, 'Google Forms CSV uploaded successfully. Refreshing charts...')
        return redirect('analytics_dashboard')
    return render(request, 'analytics_dashboard.html', {'csv_exists': csv_exists})


@require_GET
def analytics_data(request):
    """
    Analytics data endpoint - returns JSON for chart rendering.
    ✅ INTEGRATED: Structured statistical analysis framework
    """
    try:
        logger.info("📊 Analytics endpoint called")
        
        # Load data (Google Sheets → CSV fallback)
        df = load_analytics_data()
        if df is None or df.empty:
            logger.error("❌ No data loaded")
            return JsonResponse({
                'error': 'CSV data file not found. Upload the CSV to analysis/google_form_responses.csv or via the analytics page.'
            }, status=404)
        
        logger.info(f"✅ Data loaded: {len(df)} rows, {len(df.columns)} columns")
        
        # Step 1: Compute legacy payload (backward compatibility)
        payload = compute_legacy_analytics_payload(df)
        
        # Step 2: 🔗 ENHANCE WITH STRUCTURED ANALYSIS (NEW FEATURE)
        payload = enhance_analytics_payload(payload, df)
        
        # Step 3: Ensure JSON-serializable output
        payload = make_json_serializable(payload)
        
        logger.info("✅ Analytics payload computed and enhanced successfully")
        return JsonResponse(payload)
        
    except Exception as e:
        logger.error(f"❌ Error in analytics_data: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': f'Internal error: {str(e)}'
        }, status=500)


@require_POST
def sync_google_sheets(request):
    """
    Endpoint to manually sync Google Sheets data.
    Forces a fresh fetch from Google Forms → Google Sheets → CSV.
    """
    try:
        logger.info("📊 Manual sync requested from analytics dashboard")
        
        # Force fresh fetch from Google Sheets
        df = load_google_sheet_data(
            sheet_id=GOOGLE_SHEET_ID,
            range_name=GOOGLE_SHEET_RANGE
        )
        
        if df is None or df.empty:
            logger.error("❌ Failed to fetch data from Google Sheets")
            return JsonResponse({
                'error': 'Failed to sync. Check Google Sheets credentials or connection.',
                'success': False
            }, status=400)
        
        # Save to CSV for caching
        ANALYTICS_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(ANALYTICS_CSV_PATH, index=False)
        
        logger.info(f"✅ Successfully synced {len(df)} rows from Google Sheets")
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully synced {len(df)} responses from Google Sheets',
            'row_count': len(df),
            'last_sync': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error syncing Google Sheets: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': f'Sync failed: {str(e)}',
            'success': False
        }, status=500)


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
        'rider': rider, 'account': account, 'recent_txns': recent_txns,
        'current_price': current_price, 'litres_available': round(litres_available, 2),
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
        'token': qr_data, 'qr_image': qr_image, 'expires_in': 600,
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
        'station': station, 'recent_txns': recent_txns,
        'today_total': today_total, 'today_litres': round(float(today_litres), 2),
        'today_count': today_txns.count(), 'current_price': FuelPrice.current_price(),
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
        'rider_name': rider.full_name, 'cnic': rider.cnic[:5] + '-XXXXXXX-X',
        'bike_reg': rider.bike_registration, 'bike_type': rider.bike_type,
        'balance': str(account.balance),
        'litres_possible': str(round(float(account.balance) / float(current_price), 2)),
        'fuel_price': str(current_price), 'token': token_str,
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
        bike_user=rider, station=station, qr_token=qr_token,
        amount_deducted=amount, litres_dispensed=litres,
        fuel_price_at_time=current_price,
        balance_before=balance_before, balance_after=account.balance,
        status='success'
    )

    return JsonResponse({
        'success': True, 'transaction_id': str(txn.transaction_id)[:12].upper(),
        'rider_name': rider.full_name, 'litres': litres, 'amount': amount,
        'balance_after': str(account.balance), 'station': station.name,
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
        count=Count('id'), total=Sum('amount_deducted')
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
                price_per_litre=float(price), fuel_type='petrol', updated_by=request.user
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
        if ok: credited += 1
    messages.success(request, f"Credited {credited} riders with monthly quota.")
    return redirect('admin_dashboard')


# ─── API endpoints ────────────────────────────────────────────────────────────

def api_fuel_price(request):
    price = FuelPrice.current_price()
    return JsonResponse({'petrol_price': str(price), 'currency': 'PKR'})