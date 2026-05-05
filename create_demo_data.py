import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','webapp.settings')
import django
django.setup()

from django.contrib.auth.models import User
from monitor.models import UserProfile, RegisteredDevice, DeviceCheckout, DeviceLog
from django.utils import timezone
import random
from datetime import timedelta

# Create demo users if they don't exist
users_data = [
    ('user1','password','USER'),
    ('admin1','password','ADMIN'),
    ('guard1','password','GATE_GUARD'),
]

for username,password,role in users_data:
    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_password(password)
        if role=='ADMIN':
            user.is_staff=True
        user.save()
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.role=role
    profile.save()
    print(f'Set {username} role {role}')

# Create demo registered devices
devices_data = [
    ('ABC123', 'Laptop Dell XPS', 'Dell XPS 13'),
    ('ABC123456709', 'Tablet Samsung', 'Samsung Galaxy Tab'),
    ('XDDHS253572746', 'Phone iPhone', 'iPhone 14'),
    ('TEST-123', 'Test Device', 'Test Model'),
]

for serial, name, model in devices_data:
    device, created = RegisteredDevice.objects.get_or_create(
        serial_number=serial,
        defaults={
            'device_name': name,
            'device_model': model,
            'description': f'Demo device {name}',
            'registered_by': User.objects.filter(is_staff=True).first()
        }
    )
    if created:
        print(f'Created device {serial}')

# Create demo device logs (recent checkins)
# First delete existing logs
DeviceLog.objects.all().delete()

log_data = [
    ('TEST-123', 'Test device'),
    ('Asset_002', 'XDDHS253572746', 'Device reported at gate'),
    ('unknown', '-', 'Device reported at gate'),
    ('Asset_001', 'ABC123', 'Device reported at gate'),
    ('AA12B3423HIT', 'ABC123456709', 'Device reported at gate'),
]

for i, log in enumerate(log_data):
    device_id = log[0]
    serial = log[1] if len(log) > 1 else ''
    notes = log[-1]
    
    # Create log with recent timestamp (last few days)
    days_ago = random.randint(0, 5)
    hours_ago = random.randint(0, 23)
    timestamp = timezone.now() - timedelta(days=days_ago, hours=hours_ago)
    
    log_entry = DeviceLog.objects.create(
        device_id=device_id,
        serial_number=serial,
        notes=notes
    )
    # Update the timestamp manually since auto_now_add overrides it
    log_entry.timestamp = timestamp
    log_entry.save(update_fields=['timestamp'])
    print(f'Created log for {device_id} at {timestamp}')

# Create demo checkouts (recent activities)
checkout_data = [
    ('ABC123', 'user1', 'John Doe', 'IT Department', 'john@example.com', 'Software development'),
    ('ABC123456709', 'user1', 'Jane Smith', 'HR Department', 'jane@example.com', 'Employee training'),
    ('XDDHS253572746', 'admin1', 'Admin User', 'Admin', 'admin@example.com', 'System maintenance'),
]

for serial, username, name, dept, contact, purpose in checkout_data:
    try:
        device = RegisteredDevice.objects.get(serial_number=serial)
        user = User.objects.get(username=username)
        
        # Create checkout with recent timestamp
        days_ago = random.randint(0, 3)
        hours_ago = random.randint(1, 24)
        checkout_time = timezone.now() - timedelta(days=days_ago, hours=hours_ago)
        
        # Some checkouts are completed, some active
        is_completed = random.choice([True, False])
        
        checkout = DeviceCheckout.objects.create(
            registered_device=device,
            serial_number=serial,
            user=user,
            user_name=name,
            user_contact=contact,
            user_department=dept,
            purpose=purpose,
            status='CHECKED_OUT' if not is_completed else 'COMPLETED',
            is_active=not is_completed,
            checkout_time=checkout_time,
            approved_by=User.objects.filter(is_staff=True).first(),
            approval_date=checkout_time + timedelta(minutes=30)
        )
        
        if is_completed:
            checkout.checkin_time = checkout_time + timedelta(hours=random.randint(1, 8))
            checkout.save()
        
        print(f'Created checkout for {serial} by {name} - {"Active" if not is_completed else "Completed"}')
        
    except RegisteredDevice.DoesNotExist:
        print(f'Device {serial} not found, skipping checkout')
    except User.DoesNotExist:
        print(f'User {username} not found, skipping checkout')

print('Demo data creation completed!')