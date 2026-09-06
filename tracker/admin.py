from django.contrib import admin

from .models import Member, Group, Loan, Payment, Staff, AuditLog, MemberSaving, GroupSaving, OrganizationSaving, SavingTransaction
from .models import StaffTask


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("group_number", "name", "location", "meeting_day", "officer", "member_count")
    search_fields = ("group_number", "name", "location")


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("member_number", "name", "group", "phone", "status", "join_date")
    list_filter = ("group", "status")
    search_fields = ("member_number", "name", "phone", "id_number")


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("client", "loan_type", "principal", "status", "maturity_date")
    list_filter = ("loan_type", "stage")
    search_fields = ("client__name",)
    inlines = [PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("loan", "amount", "date", "recorded_by")


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "phone")
    list_filter = ("role",)
    search_fields = ("user__username", "user__first_name", "user__last_name")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "action", "model", "object_id")
    readonly_fields = ("timestamp",)
    search_fields = ("user__username", "action", "details")


@admin.register(MemberSaving)
class MemberSavingAdmin(admin.ModelAdmin):
    list_display = ("member", "balance", "updated_at")
    search_fields = ("member__name",)


@admin.register(GroupSaving)
class GroupSavingAdmin(admin.ModelAdmin):
    list_display = ("group", "balance", "updated_at")
    search_fields = ("group__name",)


@admin.register(OrganizationSaving)
class OrganizationSavingAdmin(admin.ModelAdmin):
    list_display = ("name", "balance", "updated_at")


@admin.register(SavingTransaction)
class SavingTransactionAdmin(admin.ModelAdmin):
    list_display = ("transaction_type", "amount", "member", "group", "date", "recorded_by")
    list_filter = ("transaction_type",)
    search_fields = ("member__name", "group__name", "recorded_by__username")


@admin.register(StaffTask)
class StaffTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "staff", "status", "due_date", "assigned_by")
    list_filter = ("status",)
    search_fields = ("title", "staff__user__username", "staff__user__first_name", "staff__user__last_name")