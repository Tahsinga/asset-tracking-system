from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    # path('test/', views.Test, name='test'),
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # User routes
    path('user/dashboard/', views.user_dashboard, name='user_dashboard'),
    path('user/request-checkout/', views.request_checkout, name='request_checkout'),
    
    # Admin routes
    path('approvals/', views.admin_approvals, name='admin_approvals'),
    path('approve-checkout/', views.approve_checkout, name='approve_checkout'),
    path('manual-checkout/', views.admin_manual_checkout, name='admin_manual_checkout'),
    path('register-device/', views.register_device, name='register_device'),
    path('finalize-checkout/', views.finalize_checkout, name='finalize_checkout'),
    
    # Gate Guard routes
    path('guard/dashboard/', views.guard_dashboard, name='guard_dashboard'),
    
    # Existing routes
    path('monitor/', views.monitor, name='monitor'),
    path('favicon.ico', views.favicon, name='favicon'),
    path('logs/', views.get_logs, name='get_logs'),
    path('status/', views.get_status, name='get_status'),
    path('devices/', views.get_devices, name='get_devices'),
    path('update_status/', views.update_status, name='update_status'),
    path('receive/', views.receive_data, name='receive_data'),
    path('update_device/', views.update_device, name='update_device'),
    path('check_device_status/', views.check_device_status, name='check_device_status'),
    path('checkout/', views.checkout_device, name='checkout_device'),
    path('checkin/', views.checkin_device, name='checkin_device'),
    path('checkout-history/', views.checkout_history, name='checkout_history'),
    path('checkout-history-data/', views.get_checkout_history, name='get_checkout_history'),
]