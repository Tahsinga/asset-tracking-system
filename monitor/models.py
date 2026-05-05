from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('USER', 'Regular User'),
        ('ADMIN', 'Admin'),
        ('GATE_GUARD', 'Gate Guard'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='USER')
    department = models.CharField(max_length=120, blank=True)
    contact = models.CharField(max_length=120, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"

class RegisteredDevice(models.Model):
    """Device registry - admin adds serial numbers here"""
    serial_number = models.CharField(max_length=120, unique=True)
    device_name = models.CharField(max_length=200)
    device_model = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    registered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='registered_devices')
    registered_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.serial_number} - {self.device_name}"
    
    class Meta:
        verbose_name = 'Registered Device'
        verbose_name_plural = 'Registered Devices'

class DeviceLog(models.Model):
    device_id = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(default='Device reported at gate')
    owner_name = models.CharField(max_length=120, blank=True)
    owner_contact = models.CharField(max_length=120, blank=True)
    created_date = models.DateField(null=True, blank=True)
    serial_number = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return f"{self.device_id} at {self.timestamp}"

class DeviceCheckout(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('CHECKED_OUT', 'Checked Out'),
        ('COMPLETED', 'Completed'),
        ('DENIED', 'Denied'),
    )
    
    registered_device = models.ForeignKey(RegisteredDevice, on_delete=models.CASCADE, related_name='checkouts', null=True, blank=True)
    serial_number = models.CharField(max_length=120, blank=True, null=True)  # denormalized for quick lookup
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='checkouts', null=True, blank=True)
    user_name = models.CharField(max_length=120)
    user_contact = models.CharField(max_length=120, blank=True)
    user_department = models.CharField(max_length=120, blank=True)
    checkout_time = models.DateTimeField(auto_now_add=True)
    checkin_time = models.DateTimeField(null=True, blank=True)
    purpose = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approvals')
    approval_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.serial_number} checked out by {self.user_name}"
    class Meta:
        verbose_name = 'Device Checkout'
        verbose_name_plural = 'Device Checkouts'

class ESPStatus(models.Model):
    sta_connected = models.BooleanField(default=False)
    ap_ip = models.CharField(max_length=20, default='')
    sta_ip = models.CharField(max_length=20, default='')
    last_update = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'ESP Status'
        verbose_name_plural = 'ESP Status'