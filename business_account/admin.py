from django.contrib import admin
from .models import BusinessAccount, BusinessVerification

@admin.register(BusinessAccount)
class BusinessAccountAdmin(admin.ModelAdmin):
    list_display = ('email', 'business_name', 'is_active', 'is_staff', 'is_email_verified', 'is_profile_complete', 'is_verified')
    list_filter = ('is_active', 'is_staff', 'is_email_verified', 'is_profile_complete', 'is_verified', 'date_joined')
    search_fields = ('email', 'business_name', 'role_position', 'industry_category')
    ordering = ('-date_joined',)
    filter_horizontal = ('groups', 'user_permissions') # Assuming BusinessAccount uses these

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('role_position', 'business_name', 'industry_category')}),
        ('Address', {'fields': ('address', 'address_line_2', 'city', 'state', 'zip_code')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Verification & Profile', {'fields': ('is_email_verified', 'is_profile_complete', 'is_verified', 'otp', 'otp_created_at')}),
    )
    readonly_fields = ('last_login', 'date_joined', 'otp_created_at')


@admin.register(BusinessVerification)
class BusinessVerificationAdmin(admin.ModelAdmin):
    list_display = ('business_account', 'status', 'submitted_at', 'updated_at')
    list_filter = ('status', 'submitted_at')
    search_fields = ('business_account__business_name', 'business_account__email')
    readonly_fields = ('submitted_at', 'updated_at')
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Note: The model's save() method already handles updating BusinessAccount.is_verified
