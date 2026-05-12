from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from datetime import timedelta
from .models import DeviceLog, ESPStatus, DeviceCheckout, UserProfile, RegisteredDevice
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import json
from functools import wraps

# Timeout in seconds to consider ESP offline (reduced from 60s to 10s for quicker detection)
ESP_OFFLINE_TIMEOUT_SECONDS = 10

# Helper to sanitize text fields before saving to the database
def _sanitize_field(value, max_length):
    if value is None:
        return ''
    try:
        text = str(value)
    except Exception:
        text = ''
    return text[:max_length]

def _create_device_log_from_json(data):
    device_id = _sanitize_field(data.get('device_id', 'unknown'), 100)
    notes = _sanitize_field(data.get('notes', 'Device reported at gate'), 2000)
    owner_name = _sanitize_field(data.get('owner_name', ''), 120)
    owner_contact = _sanitize_field(data.get('owner_contact', ''), 120)
    serial_number = _sanitize_field(data.get('serial_number', ''), 120)
    created_date = data.get('created_date', '')

    kwargs = {
        'device_id': device_id,
        'notes': notes,
        'owner_name': owner_name,
        'owner_contact': owner_contact,
        'serial_number': serial_number,
    }
    if created_date:
        try:
            from datetime import datetime
            kwargs['created_date'] = datetime.strptime(created_date, '%Y-%m-%d').date()
        except Exception:
            kwargs['created_date'] = None

    DeviceLog.objects.create(**kwargs)
    return JsonResponse({'status': 'success'})


def _handle_login_request(request, data, use_json=False, next_url=None):
    username = _sanitize_field(data.get('username', ''), 150)
    password = _sanitize_field(data.get('password', ''), 128)
    selected_role = _sanitize_field(data.get('role', ''), 20)

    if not username or not password or not selected_role:
        message = 'Username, password, and role are required'
        if use_json:
            return JsonResponse({'status': 'error', 'message': message}, status=400)
        return render(request, 'login.html', {
            'error': message,
            'selected_role': selected_role,
            'next': next_url,
        })

    user = authenticate(request, username=username, password=password)
    if user is None:
        # Fallback to seeded demo accounts when the database is empty or missing users.
        default_accounts = {
            'user1': {'password': 'password', 'role': 'USER', 'is_staff': False, 'is_superuser': False},
            'admin1': {'password': 'password', 'role': 'ADMIN', 'is_staff': True, 'is_superuser': False},
            'guard1': {'password': 'password', 'role': 'GATE_GUARD', 'is_staff': False, 'is_superuser': False},
        }
        if not User.objects.filter(username=username).exists():
            fallback = default_accounts.get(username)
            if fallback and password == fallback['password']:
                user = User.objects.create_user(username=username, password=password)
                user.is_staff = fallback['is_staff']
                user.is_superuser = fallback['is_superuser']
                user.save()

                profile, _ = UserProfile.objects.get_or_create(user=user)
                profile.role = fallback['role']
                profile.save()
                user = authenticate(request, username=username, password=password)

    if user is None:
        message = 'Invalid username or password'
        if use_json:
            return JsonResponse({'status': 'error', 'message': message}, status=401)
        return render(request, 'login.html', {
            'error': message,
            'selected_role': selected_role,
            'next': next_url,
        })

    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = None

    if selected_role == 'ADMIN':
        if not (user.is_staff or user.is_superuser or (profile and profile.role == 'ADMIN')):
            message = 'Your account is not assigned to the Admin role'
            if use_json:
                return JsonResponse({'status': 'error', 'message': message}, status=403)
            return render(request, 'login.html', {
                'error': message,
                'selected_role': selected_role,
                'next': next_url,
            })
    elif selected_role == 'GATE_GUARD':
        if not (profile and profile.role == 'GATE_GUARD'):
            message = 'Your account is not assigned to the Gate Guard role'
            if use_json:
                return JsonResponse({'status': 'error', 'message': message}, status=403)
            return render(request, 'login.html', {
                'error': message,
                'selected_role': selected_role,
                'next': next_url,
            })
    else:
        if profile and profile.role != 'USER':
            message = 'Your account is not assigned to the User role'
            if use_json:
                return JsonResponse({'status': 'error', 'message': message}, status=403)
            return render(request, 'login.html', {
                'error': message,
                'selected_role': selected_role,
                'next': next_url,
            })
        if profile is None:
            UserProfile.objects.create(user=user, role='USER')

    login(request, user)
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts=None):
        redirect_target = next_url
    else:
        redirect_target = 'dashboard'

    if use_json:
        return JsonResponse({'status': 'success', 'redirect': redirect_target})
    return redirect(redirect_target)


@csrf_exempt
def home(request):
    """Root route: redirect users to login/dashboard and accept JSON device posts."""
    if request.method == 'POST':
        content_type = request.META.get('CONTENT_TYPE', '')
        if content_type.startswith('application/json'):
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

            if data.get('username') or data.get('password'):
                return JsonResponse({'status': 'error', 'message': 'Use /login/ to authenticate'}, status=400)
            try:
                return _create_device_log_from_json(data)
            except Exception as e:
                print(f"Error creating DeviceLog from root POST: {e}")
                return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

        if request.POST.get('username') or request.POST.get('password'):
            next_url = request.POST.get('next')
            return _handle_login_request(request, request.POST, use_json=False, next_url=next_url)

        return JsonResponse({'status': 'method not allowed'}, status=405)

    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')

# Decorator to check user role
def role_required(required_role):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            try:
                if request.user.is_staff or request.user.is_superuser:
                    # Allow staff/superusers access to everything
                    return view_func(request, *args, **kwargs)
                profile = request.user.profile
                if profile.role == required_role:
                    return view_func(request, *args, **kwargs)
                return redirect('dashboard')
            except UserProfile.DoesNotExist:
                if request.user.is_staff or request.user.is_superuser:
                    return view_func(request, *args, **kwargs)
                if required_role == 'USER':
                    UserProfile.objects.create(user=request.user, role='USER')
                    return view_func(request, *args, **kwargs)
                return redirect('dashboard')
        return wrapper
    return decorator

@ensure_csrf_cookie
def login_view(request):
    next_url = request.GET.get('next') or request.POST.get('next')
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        content_type = request.META.get('CONTENT_TYPE', '')
        if content_type.startswith('application/json'):
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError as e:
                print(f"Error processing login JSON: {e}")
                return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
            return _handle_login_request(request, data, use_json=True, next_url=next_url)

        return _handle_login_request(request, request.POST, use_json=False, next_url=next_url)

    return render(request, 'login.html', {'next': next_url, 'selected_role': ''})

def logout_view(request):
    logout(request)
    return redirect('home')

@login_required(login_url='login')
def dashboard(request):
    """Route user to appropriate dashboard based on their role"""
    try:
        profile = request.user.profile
        role = profile.role
    except UserProfile.DoesNotExist:
        # Create default profile if it doesn't exist
        profile = UserProfile.objects.create(user=request.user, role='USER')
        role = 'USER'
    
    if request.user.is_staff or request.user.is_superuser:
        role = 'ADMIN'
    
    if role == 'ADMIN':
        return redirect('admin_approvals')
    elif role == 'GATE_GUARD':
        # gate guard should see the main monitor page
        return redirect('monitor')
    else:
        return redirect('user_dashboard')

# User Views
@login_required(login_url='login')
@role_required('USER')
def user_dashboard(request):
    """User can request device checkout"""
    # Get all active registered devices
    all_registered_devices = RegisteredDevice.objects.filter(is_active=True).order_by('device_name')
    
    # Get all devices with pending or checked out requests (not yet completed)
    unavailable_serials = DeviceCheckout.objects.filter(
        status__in=['PENDING', 'CHECKED_OUT']
    ).values_list('serial_number', flat=True)
    
    # Filter out unavailable devices from the list
    available_devices = all_registered_devices.exclude(serial_number__in=unavailable_serials)
    
    # Get user's checkout requests (all statuses)
    user_checkouts = DeviceCheckout.objects.filter(user=request.user).order_by('-checkout_time')
    
    # Separate by status for display - exclude COMPLETED
    pending_checkouts = user_checkouts.filter(status='PENDING')
    approved_checkouts = user_checkouts.filter(status='CHECKED_OUT')
    
    return render(request, 'user_dashboard.html', {
        'available_devices': available_devices,
        'pending_checkouts': pending_checkouts,
        'approved_checkouts': approved_checkouts
    })

@login_required(login_url='login')
@role_required('USER')
def request_checkout(request):
    """User requests to checkout a registered device"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            serial_number = data.get('serial_number')
            user = data.get('user', '').strip()
            department = data.get('department', '').strip()
            contact = data.get('contact', '').strip()
            purpose = data.get('purpose', '').strip()
            
            # Validate required fields
            if not user or not department or not contact:
                return JsonResponse({'status': 'error', 'message': 'User, Department, and Contact are required'}, status=400)
            
            # Verify device exists and is registered
            registered_device = RegisteredDevice.objects.get(serial_number=serial_number, is_active=True)
            
            # Check if device is already checked out or pending
            existing_checkout = DeviceCheckout.objects.filter(
                serial_number=serial_number, 
                status__in=['PENDING', 'CHECKED_OUT']
            ).first()
            if existing_checkout:
                return JsonResponse({'status': 'error', 'message': f'Device {serial_number} is already checked out or pending approval'}, status=400)
            
            checkout = DeviceCheckout.objects.create(
                registered_device=registered_device,
                serial_number=serial_number,
                user=request.user,
                user_name=user,
                user_contact=contact,
                user_department=department,
                purpose=purpose,
                status='PENDING'
            )
            return JsonResponse({'status': 'success', 'checkout_id': checkout.id})
        except RegisteredDevice.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Device not found or inactive'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'method not allowed'}, status=405)

# Admin Views
@login_required(login_url='login')
@role_required('ADMIN')
def admin_approvals(request):
    """Admin can approve or deny checkout requests"""
    pending_checkouts = DeviceCheckout.objects.filter(status='PENDING').order_by('-checkout_time')
    approved_checkouts = DeviceCheckout.objects.filter(status='CHECKED_OUT').order_by('-checkout_time')
    
    return render(request, 'admin_dashboard.html', {
        'pending_checkouts': pending_checkouts,
        'approved_checkouts': approved_checkouts
    })

@login_required(login_url='login')
@role_required('ADMIN')
def admin_manual_checkout(request):
    """Admin can manually checkout a device"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            serial_number = data.get('serial_number')
            user_name = data.get('user_name', '').strip()
            user_contact = data.get('user_contact', '').strip()
            user_department = data.get('user_department', '').strip()
            purpose = data.get('purpose', '').strip()
            
            # Validate required fields
            if not user_name or not user_contact or not user_department:
                return JsonResponse({'status': 'error', 'message': 'User name, contact, and department are required'}, status=400)
            
            # Verify device exists and is registered
            registered_device = RegisteredDevice.objects.get(serial_number=serial_number, is_active=True)
            
            # Check if device is already checked out
            existing_checkout = DeviceCheckout.objects.filter(
                serial_number=serial_number,
                status='CHECKED_OUT'
            ).first()
            if existing_checkout:
                return JsonResponse({'status': 'error', 'message': f'Device {serial_number} is already checked out'}, status=400)
            
            # Create immediate checkout (already approved by admin)
            checkout = DeviceCheckout.objects.create(
                registered_device=registered_device,
                serial_number=serial_number,
                user_name=user_name,
                user_contact=user_contact,
                user_department=user_department,
                purpose=purpose,
                status='CHECKED_OUT',
                approved_by=request.user,
                approval_date=timezone.now()
            )
            return JsonResponse({'status': 'success', 'checkout_id': checkout.id})
        except RegisteredDevice.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Device not found or inactive'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    # GET request - show available devices
    available_devices = RegisteredDevice.objects.filter(is_active=True).exclude(
        serial_number__in=DeviceCheckout.objects.filter(status='CHECKED_OUT').values_list('serial_number', flat=True)
    ).order_by('device_name')
    
    return render(request, 'admin_manual_checkout.html', {
        'available_devices': available_devices
    })

@login_required(login_url='login')
@role_required('ADMIN')
def register_device(request):
    """Admin registers new devices"""
    if request.method == 'POST':
        serial_number = request.POST.get('serial_number')
        device_name = request.POST.get('device_name')
        device_model = request.POST.get('device_model')
        description = request.POST.get('description', '')
        
        # Check if device already registered
        if RegisteredDevice.objects.filter(serial_number=serial_number).exists():
            return render(request, 'register_device.html', {
                'error': f'Device with serial number {serial_number} is already registered'
            })
        
        try:
            RegisteredDevice.objects.create(
                serial_number=serial_number,
                device_name=device_name,
                device_model=device_model,
                description=description,
                registered_by=request.user
            )
            return render(request, 'register_device.html', {
                'success': f'Device {serial_number} registered successfully!'
            })
        except Exception as e:
            return render(request, 'register_device.html', {
                'error': f'Error registering device: {str(e)}'
            })
    
    registered_devices = RegisteredDevice.objects.all().order_by('-registered_date')
    return render(request, 'register_device.html', {
        'registered_devices': registered_devices
    })

@login_required(login_url='login')
@role_required('ADMIN')
def approve_checkout(request):
    """Admin approves a checkout request"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            checkout_id = data.get('checkout_id')
            action = data.get('action')  # 'approve' or 'deny'
            
            checkout = DeviceCheckout.objects.get(id=checkout_id)
            
            if action == 'approve':
                checkout.status = 'CHECKED_OUT'
                checkout.approved_by = request.user
                checkout.approval_date = timezone.now()
                checkout.is_active = True
            elif action == 'deny':
                checkout.status = 'DENIED'
                checkout.approved_by = request.user
                checkout.approval_date = timezone.now()
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid action'}, status=400)
            
            checkout.save()
            return JsonResponse({'status': 'success'})
        except DeviceCheckout.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Checkout not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'method not allowed'}, status=405)

@login_required(login_url='login')
@role_required('ADMIN')
def finalize_checkout(request):
    """Finalize checkout by marking device as COMPLETED and clearing user details"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            checkout_id = data.get('checkout_id')
            
            if not checkout_id:
                return JsonResponse({'status': 'error', 'message': 'Checkout ID required'}, status=400)
            
            checkout = DeviceCheckout.objects.filter(id=checkout_id, status='CHECKED_OUT').first()
            if not checkout:
                return JsonResponse({'status': 'error', 'message': 'Checkout not found or already completed'}, status=404)
            
            # Mark as completed and clear user details
            checkout.status = 'COMPLETED'
            checkout.checkin_time = timezone.now()
            checkout.user_name = ''  # Clear user details
            checkout.user_contact = ''
            checkout.user_department = ''
            checkout.purpose = ''
            checkout.save()
            
            # Verify the save worked
            updated_checkout = DeviceCheckout.objects.get(id=checkout_id)
            print(f'DEBUG: Checkout {checkout_id} status is now: {updated_checkout.status}')
            
            return JsonResponse({'status': 'success', 'message': 'Device checked in and removed from checkout list'})
        except Exception as e:
            print(f'Error in finalize_checkout: {e}')
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'method not allowed'}, status=405)

# Gate Guard Views
@login_required(login_url='login')
@role_required('GATE_GUARD')
def guard_dashboard(request):
    """Redirect gate guard to main monitor interface."""
    # reuse existing monitor view and logic
    return redirect('monitor')



@login_required(login_url='login')
@ensure_csrf_cookie
def monitor(request):
    logs = DeviceLog.objects.order_by('-timestamp')[:20]  # Last 20 logs
    status = ESPStatus.objects.first()  # Assuming one ESP
    is_online = status and (timezone.now() - status.last_update).total_seconds() < ESP_OFFLINE_TIMEOUT_SECONDS if status else False
    return render(request, 'monitor.html', {'logs': logs, 'status': status, 'is_online': is_online})

def favicon(request):
    return HttpResponse(status=204)

@login_required(login_url='login')
def checkout_history(request):
    return render(request, 'checkout_history.html')

@login_required(login_url='login')
@login_required(login_url='login')
def get_checkout_history(request):
    from django.db.models import Q
    checkouts_query = DeviceCheckout.objects.all()
    
    # Search filter
    search = request.GET.get('search', '').strip()
    if search:
        checkouts_query = checkouts_query.filter(
            Q(serial_number__icontains=search) |
            Q(user_name__icontains=search) |
            Q(user_department__icontains=search) |
            Q(purpose__icontains=search)
        )
    
    # Status filter
    status = request.GET.get('status', 'all')
    if status == 'active':
        checkouts_query = checkouts_query.filter(is_active=True)
    elif status == 'completed':
        checkouts_query = checkouts_query.filter(is_active=False)
    
    checkouts = checkouts_query.order_by('-checkout_time')
    
    data = []
    for checkout in checkouts:
        data.append({
            'id': checkout.id,
            'device_id': checkout.serial_number or checkout.registered_device.serial_number if checkout.registered_device else 'Unknown',
            'user_name': checkout.user_name,
            'user_contact': checkout.user_contact,
            'user_department': checkout.user_department,
            'checkout_time': checkout.checkout_time.strftime('%Y-%m-%d %H:%M:%S'),
            'checkin_time': checkout.checkin_time.strftime('%Y-%m-%d %H:%M:%S') if checkout.checkin_time else '',
            'purpose': checkout.purpose,
            'is_active': checkout.is_active,
            'duration': str(checkout.checkin_time - checkout.checkout_time) if checkout.checkin_time else 'Still checked out'
        })
    
    return JsonResponse({'checkouts': data})

def get_logs(request):
    from django.db.models import Q
    logs_query = DeviceLog.objects.all()
    
    # Date filter
    date_filter = request.GET.get('date')
    if date_filter:
        try:
            from datetime import datetime
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            logs_query = logs_query.filter(timestamp__date=filter_date)
        except ValueError:
            pass  # Invalid date format, ignore filter
    
    # Search filter
    search = request.GET.get('search', '').strip()
    if search:
        logs_query = logs_query.filter(
            Q(device_id__icontains=search) |
            Q(owner_name__icontains=search) |
            Q(notes__icontains=search)
        )
    
    # Get unique devices by grouping and taking the latest log per device
    from django.db.models import Max
    unique_devices = logs_query.values('device_id').annotate(latest_timestamp=Max('timestamp')).order_by('-latest_timestamp')[:20]
    
    device_ids = [d['device_id'] for d in unique_devices]
    logs = DeviceLog.objects.filter(device_id__in=device_ids).order_by('-timestamp')
    
    # Ensure we get one log per device (the latest one)
    seen_devices = set()
    filtered_logs = []
    for log in logs:
        if log.device_id not in seen_devices:
            seen_devices.add(log.device_id)
            filtered_logs.append(log)
            if len(filtered_logs) >= 20:
                break
    
    # add two-hour offset to timestamps for display
    data = []
    for log in filtered_logs:
        display_time = (log.timestamp + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
        data.append({
            'time': display_time,
            'device_id': log.device_id,
            'notes': log.notes,
            'owner_name': log.owner_name,
            'owner_contact': log.owner_contact,
            'serial_number': log.serial_number,
            'created_date': log.created_date.strftime('%Y-%m-%d') if log.created_date else ''
        })
    return JsonResponse({'logs': data})

def get_status(request):
    status = ESPStatus.objects.first()
    if status:
        is_online = (timezone.now() - status.last_update).total_seconds() < ESP_OFFLINE_TIMEOUT_SECONDS
        data = {
            'is_online': is_online,
            'ap_ip': status.ap_ip,
            'sta_ip': status.sta_ip,
            'last_update': status.last_update.strftime('%H:%M:%S')
        }
    else:
        data = {'is_online': False, 'ap_ip': '', 'sta_ip': '', 'last_update': ''}
    return JsonResponse(data)

@csrf_exempt
def update_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            status, created = ESPStatus.objects.get_or_create(id=1, defaults={})
            status.sta_connected = data.get('sta_connected', False)
            status.ap_ip = data.get('ap_ip', '')
            status.sta_ip = data.get('sta_ip', '')
            status.save()
            return JsonResponse({'status': 'success'})
        except:
            return JsonResponse({'status': 'error'}, status=400)
    return JsonResponse({'status': 'method not allowed'}, status=405)

def get_devices(request):
    from django.db.models import Max
    # Only include devices seen within RECENT_DEVICE_SECONDS (default 10s for faster detection)
    RECENT_DEVICE_SECONDS = 10
    recent_seconds = int(request.GET.get('recent', RECENT_DEVICE_SECONDS))
    cutoff = timezone.now() - timedelta(seconds=recent_seconds)

    devices = DeviceLog.objects.values('device_id').annotate(last_seen=Max('timestamp')).filter(last_seen__gte=cutoff).order_by('-last_seen')
    data = []
    for d in devices[:10]:
        # apply two-hour offset to last_seen
        last_seen = (d['last_seen'] + timedelta(hours=2)) if isinstance(d['last_seen'], timezone.datetime) else d['last_seen']
        latest_log = DeviceLog.objects.filter(device_id=d['device_id']).order_by('-timestamp').first()
        
        owner = ''
        owner_contact = ''
        serial = ''
        created = ''
        if latest_log:
            owner = latest_log.owner_name or ''
            owner_contact = latest_log.owner_contact or ''
            serial = latest_log.serial_number or ''
            created = latest_log.created_date.strftime('%Y-%m-%d') if latest_log.created_date else ''
        
        # Check checkout status based on serial number
        is_checked_out = False
        current_user = ''
        current_user_contact = ''
        current_user_department = ''
        checkout_time = ''
        purpose = ''
        registered_device_info = ''
        registered = None
        
        if serial:
            # Check if device is registered and get its info
            registered = RegisteredDevice.objects.filter(serial_number=serial).first()
            if registered:
                registered_device_info = f"{registered.device_name} ({registered.device_model})" if registered.device_model else registered.device_name
            
            # Check if device is currently checked out
            checkout = DeviceCheckout.objects.filter(
                serial_number=serial,
                status='CHECKED_OUT'
            ).first()
            
            if checkout:
                is_checked_out = True
                current_user = checkout.user_name
                current_user_contact = checkout.user_contact
                current_user_department = checkout.user_department
                checkout_time = checkout.checkout_time.strftime('%Y-%m-%d %H:%M:%S')
                purpose = checkout.purpose
        
        # Get checkout ID if device is checked out
        checkout_id = ''
        if is_checked_out and serial:
            checkout = DeviceCheckout.objects.filter(
                serial_number=serial,
                status='CHECKED_OUT'
            ).first()
            if checkout:
                checkout_id = str(checkout.id)
        
        data.append({
            'id': d['device_id'], 
            'last_seen': last_seen.strftime('%H:%M:%S') if hasattr(last_seen, 'strftime') else last_seen, 
            'owner': owner, 
            'owner_contact': owner_contact, 
            'serial': serial, 
            'created': created,
            'is_checked_out': is_checked_out,
            'checkout_id': checkout_id,
            'registered_device_info': registered_device_info,
            'device_name': registered.device_name if registered else '',
            'device_model': registered.device_model if registered else '',
            'current_user': current_user,
            'current_user_contact': current_user_contact,
            'current_user_department': current_user_department,
            'checkout_time': checkout_time,
            'purpose': purpose
        })
    print(f"DEBUG: Returning {len(data)} devices: {data}")  # Debug output
    return JsonResponse({'devices': data})

@csrf_exempt
def checkout_device(request):
    """Checkout is now handled through admin dashboard only"""
    return JsonResponse({'status': 'error', 'message': 'Device checkout requests must be made through the user dashboard and approved by admin'}, status=403)

@csrf_exempt
def checkin_device(request):
    """Check-in a device and mark it as COMPLETED"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            checkout_id = data.get('checkout_id')
            
            if not checkout_id:
                return JsonResponse({'status': 'error', 'message': 'Checkout ID required'}, status=400)
            
            checkout = DeviceCheckout.objects.filter(id=checkout_id, status='CHECKED_OUT').first()
            if not checkout:
                return JsonResponse({'status': 'error', 'message': 'Checkout not found or already completed'}, status=404)
            
            # Mark as completed and clear checkout details
            checkout.status = 'COMPLETED'
            checkout.checkin_time = timezone.now()
            checkout.user_name = ''  # Clear user details
            checkout.user_contact = ''
            checkout.user_department = ''
            checkout.purpose = ''
            checkout.save()
            
            return JsonResponse({'status': 'success', 'message': 'Device checked in successfully'})
        except Exception as e:
            print(f'Error in checkin_device: {e}')
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

@csrf_exempt
def receive_data(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(f"DEBUG: Received data: {data}")  # Debug output
            device_id = data.get('device_id', 'unknown')
            notes = data.get('notes', 'Device reported at gate')
            owner_name = data.get('owner_name', '')
            owner_contact = data.get('owner_contact', '')
            serial_number = data.get('serial_number', '')
            created_date = data.get('created_date', '')

            kwargs = {
                'device_id': device_id,
                'notes': notes,
                'owner_name': owner_name,
                'owner_contact': owner_contact,
                'serial_number': serial_number,
            }
            # Parse created_date (YYYY-MM-DD) if provided
            if created_date:
                try:
                    from datetime import datetime
                    kwargs['created_date'] = datetime.strptime(created_date, '%Y-%m-%d').date()
                except:
                    pass

            DeviceLog.objects.create(**kwargs)
            return JsonResponse({'status': 'success'})
        except:
            return JsonResponse({'status': 'error'}, status=400)
    return JsonResponse({'status': 'method not allowed'}, status=405)


@csrf_exempt
def update_device(request):
    """Modify the latest log entry for a given device."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            device_id = data.get('device_id')
            if not device_id:
                return JsonResponse({'status': 'error', 'message': 'device_id required'}, status=400)
            log = DeviceLog.objects.filter(device_id=device_id).order_by('-timestamp').first()
            if not log:
                return JsonResponse({'status': 'error', 'message': 'no log entry for device'}, status=404)

            # update permitted fields
            if 'owner_name' in data:
                log.owner_name = data.get('owner_name', '')
            if 'owner_contact' in data:
                log.owner_contact = data.get('owner_contact', '')
            if 'serial_number' in data:
                log.serial_number = data.get('serial_number', '')
            if 'notes' in data:
                log.notes = data.get('notes', '')
            if 'created_date' in data:
                cd = data.get('created_date')
                if cd:
                    try:
                        from datetime import datetime
                        log.created_date = datetime.strptime(cd, '%Y-%m-%d').date()
                    except:
                        pass
                else:
                    log.created_date = None

            log.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'method not allowed'}, status=405)

@csrf_exempt
def check_device_status(request):
    """Check if a device is registered and currently checked out"""
    if request.method == 'GET':
        device_id = request.GET.get('device_id')
        if not device_id:
            return JsonResponse({'status': 'error', 'message': 'device_id required'}, status=400)
        
        # Check if device is registered
        try:
            registered_device = RegisteredDevice.objects.get(serial_number=device_id, is_active=True)
        except RegisteredDevice.DoesNotExist:
            return JsonResponse({
                'status': 'success',
                'registered': False,
                'checked_out': False,
                'message': 'Device not registered'
            })
        
        # Check if device is currently checked out
        active_checkout = DeviceCheckout.objects.filter(
            registered_device=registered_device,
            status='CHECKED_OUT',
            is_active=True
        ).exists()
        
        return JsonResponse({
            'status': 'success',
            'registered': True,
            'checked_out': active_checkout,
            'message': 'Device registered and checked out' if active_checkout else 'Device registered but not checked out'
        })
    
    return JsonResponse({'status': 'method not allowed'}, status=405)
