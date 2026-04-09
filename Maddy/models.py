from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class City(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Cities"


class FuelPrice(models.Model):
    FUEL_TYPES = [('petrol', 'Petrol'), ('diesel', 'Diesel'), ('cng', 'CNG')]
    fuel_type = models.CharField(max_length=20, choices=FUEL_TYPES, default='petrol')
    price_per_litre = models.DecimalField(max_digits=8, decimal_places=2)
    effective_date = models.DateField(default=timezone.now)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.fuel_type} - Rs.{self.price_per_litre}/L (from {self.effective_date})"

    class Meta:
        ordering = ['-effective_date']

    @classmethod
    def current_price(cls, fuel_type='petrol'):
        obj = cls.objects.filter(fuel_type=fuel_type).first()
        return obj.price_per_litre if obj else 300.00


class PetrolStation(models.Model):
    STATUS = [('pending', 'Pending'), ('active', 'Active'), ('suspended', 'Suspended')]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='station')
    name = models.CharField(max_length=200)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True)
    address = models.TextField()
    license_no = models.CharField(max_length=50, unique=True)
    owner_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    api_key = models.UUIDField(default=uuid.uuid4, unique=True)
    status = models.CharField(max_length=20, choices=STATUS, default='pending')
    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.city})"

    def total_transactions(self):
        return self.transactions.count()

    def total_litres_dispensed(self):
        from django.db.models import Sum
        result = self.transactions.aggregate(Sum('litres_dispensed'))
        return result['litres_dispensed__sum'] or 0


class BikeUser(models.Model):
    BIKE_TYPES = [('100cc', '100cc'), ('125cc', '125cc'), ('150cc', '150cc'), ('other', 'Other')]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='bike_profile')
    cnic = models.CharField(max_length=15, unique=True, help_text="Format: 12345-1234567-1")
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True)
    bike_registration = models.CharField(max_length=20, unique=True, help_text="e.g. LHR-1234")
    bike_type = models.CharField(max_length=10, choices=BIKE_TYPES, default='125cc')
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.cnic})"

    def get_or_create_account(self):
        account, _ = CreditAccount.objects.get_or_create(bike_user=self)
        return account


class CreditAccount(models.Model):
    bike_user = models.OneToOneField(BikeUser, on_delete=models.CASCADE, related_name='credit_account')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    monthly_quota = models.DecimalField(max_digits=10, decimal_places=2, default=1500.00)
    total_credited = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_redeemed = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    last_reset = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Account: {self.bike_user.full_name} | Balance: Rs.{self.balance}"

    def credit_monthly_quota(self):
        today = timezone.now().date()
        if self.last_reset and self.last_reset.month == today.month and self.last_reset.year == today.year:
            return False, "Already credited this month"
        self.balance += self.monthly_quota
        self.total_credited += self.monthly_quota
        self.last_reset = today
        self.save()
        return True, f"Rs.{self.monthly_quota} credited"

    def deduct(self, amount):
        if self.balance < amount:
            return False, "Insufficient balance"
        self.balance -= amount
        self.total_redeemed += amount
        self.save()
        return True, "Deducted successfully"


class QRToken(models.Model):
    STATUS = [('active', 'Active'), ('used', 'Used'), ('expired', 'Expired')]
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    bike_user = models.ForeignKey(BikeUser, on_delete=models.CASCADE, related_name='qr_tokens')
    amount_requested = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"QR:{self.token} | {self.bike_user.full_name} | {self.status}"

    def is_valid(self):
        return self.status == 'active' and timezone.now() < self.expires_at

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=10)
        super().save(*args, **kwargs)


class Transaction(models.Model):
    STATUS = [('success', 'Success'), ('failed', 'Failed'), ('reversed', 'Reversed')]
    transaction_id = models.UUIDField(default=uuid.uuid4, unique=True)
    bike_user = models.ForeignKey(BikeUser, on_delete=models.CASCADE, related_name='transactions')
    station = models.ForeignKey(PetrolStation, on_delete=models.CASCADE, related_name='transactions')
    qr_token = models.OneToOneField(QRToken, on_delete=models.SET_NULL, null=True, blank=True)
    amount_deducted = models.DecimalField(max_digits=10, decimal_places=2)
    litres_dispensed = models.DecimalField(max_digits=8, decimal_places=3)
    fuel_price_at_time = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS, default='success')
    balance_before = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"TXN-{str(self.transaction_id)[:8]} | {self.bike_user.full_name} | Rs.{self.amount_deducted}"

    class Meta:
        ordering = ['-created_at']


class FraudFlag(models.Model):
    REASON = [
        ('duplicate_qr', 'Duplicate QR Use'),
        ('rapid_redemption', 'Rapid Redemption'),
        ('multi_city', 'Multi-City Same Day'),
        ('excessive_amount', 'Excessive Amount'),
    ]
    bike_user = models.ForeignKey(BikeUser, on_delete=models.CASCADE, related_name='fraud_flags')
    reason = models.CharField(max_length=30, choices=REASON)
    details = models.TextField()
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"FRAUD: {self.bike_user.full_name} - {self.get_reason_display()}"
