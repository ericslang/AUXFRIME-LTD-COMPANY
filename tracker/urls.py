from django.urls import path, include
from django.contrib import admin
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.dashboard, name="dashboard"),

    # Profile view
    path("accounts/profile/", views.profile, name='profile'),
    # Account settings (username / password change from dropdown)
    path("accounts/settings/", views.account_settings, name='account_settings'),

    path("groups/", views.group_list, name="group_list"),
    path("groups/new/", views.group_form, name="group_new"),
    path("groups/<int:pk>/", views.group_detail, name="group_detail"),
    path("groups/<int:pk>/edit/", views.group_form, name="group_edit"),
    path("groups/<int:pk>/delete/", views.group_delete, name="group_delete"),

    path("clients/", views.client_list, name="client_list"),
    path("clients/new/", views.client_form, name="client_new"),
    path("clients/<int:pk>/edit/", views.client_form, name="client_edit"),
    path("clients/<int:pk>/delete/", views.client_delete, name="client_delete"),
    path("groups/<int:pk>/members/new/", views.group_add_member, name="group_add_member"),

    path("loans/", views.loan_list, name="loan_list"),
    path("loans/export/", views.loan_export_csv, name="loan_export_csv"),
    path("loans/new/", views.loan_request, name="loan_new"),
    path("loans/<int:pk>/", views.loan_detail, name="loan_detail"),
    path("loans/<int:pk>/approve/", views.loan_approve, name="loan_approve"),
    path("loans/<int:pk>/payment/", views.loan_payment, name="loan_payment"),
    path("loans/<int:pk>/delete/", views.loan_delete, name="loan_delete"),
    path("settings/", views.settings, name="settings"),
    path("staff/", views.staff_list, name="staff_list"),
    path("staff/new/", views.staff_form, name="staff_new"),
    path("staff/<int:pk>/edit/", views.staff_form, name="staff_edit"),
    path("staff/<int:pk>/", views.staff_detail, name="staff_detail"),
    path("staff/<int:pk>/tasks/new/", views.staff_task_new, name="staff_task_new"),
    path("audit/", views.audit_list, name="audit_list"),
    path("savings/transaction/", views.saving_transaction, name="saving_transaction"),
    path("savings/member/<int:member_id>/", views.member_savings, name="member_savings"),
    path("savings/group/<int:group_id>/", views.group_savings, name="group_savings"),
    path("reports/financial/", views.financial_report, name="financial_report"),
    path("reports/loans/", views.loan_report, name="loan_report"),
    path("reports/financial/view/", views.financial_report_view, name="financial_report_view"),
    path("reports/loans/view/", views.loan_report_view, name="loan_report_view"),
    # Authentication (login/logout/password management)
    path("accounts/", include("django.contrib.auth.urls")),
]
