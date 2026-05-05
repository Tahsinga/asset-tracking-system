from django.contrib import admin
from .models import UserProfile, RegisteredDevice, DeviceLog, DeviceCheckout, ESPStatus

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'department')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email')

@admin.register(RegisteredDevice)
class RegisteredDeviceAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'device_name', 'device_model', 'is_active', 'registered_date')
    list_filter = ('is_active', 'registered_date')
    search_fields = ('serial_number', 'device_name')
    readonly_fields = ('registered_date', 'registered_by')
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new device
            obj.registered_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(DeviceLog)
class DeviceLogAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'serial_number', 'timestamp', 'owner_name')
    search_fields = ('device_id', 'serial_number', 'owner_name')

@admin.register(DeviceCheckout)
class DeviceCheckoutAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'user_name', 'status', 'checkout_time')
    list_filter = ('status', 'checkout_time')
    search_fields = ('serial_number', 'user_name')
    readonly_fields = ('checkout_time', 'user', 'registered_device')

@admin.register(ESPStatus)
class ESPStatusAdmin(admin.ModelAdmin):
    list_display = ('sta_connected', 'ap_ip', 'sta_ip', 'last_update')
