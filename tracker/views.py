import csv
import datetime
from decimal import Decimal
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import ProtectedError, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .forms import (
    ApproveLoanForm, ClientForm, GroupForm, LoanRequestForm, PaymentForm,
    StaffForm, SavingTransactionForm, StaffTaskForm
)
from .models import Member, Group, Loan, Staff, AuditLog, MemberSaving, GroupSaving, OrganizationSaving, SavingTransaction
from .models import StaffTask


@login_required
def dashboard(request):
    loans = list(Loan.objects.select_related("client", "group").prefetch_related("payments"))

    counts = {"pending": 0, "active": 0, "overdue": 0, "paid": 0}
    outstanding = Decimal("0")
    disbursed = Decimal("0")
    for loan in loans:
        counts[loan.status] += 1
        if loan.status != "pending":
            disbursed += loan.principal
        if loan.status in ("active", "overdue"):
            outstanding += loan.balance

    recent = loans[:6]

    today = datetime.date.today()
    horizon = today + datetime.timedelta(days=7)
    due_soon = sorted(
        (l for l in loans if l.status == "active" and l.maturity_date and today <= l.maturity_date <= horizon),
        key=lambda l: l.maturity_date,
    )

    context = {
        "group_count": Group.objects.count(),
        "client_count": Member.objects.count(),
        "counts": counts,
        "outstanding": outstanding,
        "disbursed": disbursed,
        "recent": recent,
        "due_soon": due_soon,
    }

    # Savings totals and top savers
    from .models import MemberSaving, GroupSaving, OrganizationSaving
    total_member_savings = MemberSaving.objects.aggregate(total=Sum("balance"))["total"] or Decimal("0")
    total_group_savings = GroupSaving.objects.aggregate(total=Sum("balance"))["total"] or Decimal("0")
    org = OrganizationSaving.objects.first()
    org_balance = org.balance if org else Decimal("0")

    total_savings = (total_member_savings or Decimal("0")) + (total_group_savings or Decimal("0")) + (org_balance or Decimal("0"))

    top_member_savers = MemberSaving.objects.select_related("member").order_by("-balance")[:5]
    top_group_savers = GroupSaving.objects.select_related("group").order_by("-balance")[:5]

    context.update({
        "total_member_savings": total_member_savings,
        "total_group_savings": total_group_savings,
        "organization_savings": org_balance,
        "total_savings": total_savings,
        "top_member_savers": top_member_savers,
        "top_group_savers": top_group_savers,
    })
    return render(request, "tracker/dashboard.html", context)


# User profile
@login_required
def profile(request):
    user = request.user
    if request.method == "POST":
        first = request.POST.get("first_name", "").strip()
        last = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        user.first_name = first
        user.last_name = last
        user.email = email
        user.save()
        messages.success(request, "Profile updated.")
        return redirect("profile")
    return render(request, "registration/profile.html", {"user": user})


@login_required
def account_settings(request):
    user = request.user
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        current = request.POST.get("current_password", "")
        new1 = request.POST.get("new_password1", "")
        new2 = request.POST.get("new_password2", "")
        errors = []
        # username uniqueness
        if username and username != user.username:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if User.objects.filter(username=username).exclude(pk=user.pk).exists():
                errors.append("Username already taken.")

        # password change validation
        if new1 or new2:
            if not user.check_password(current):
                errors.append("Current password is incorrect.")
            if new1 != new2:
                errors.append("New passwords do not match.")
            else:
                try:
                    validate_password(new1, user)
                except ValidationError as e:
                    errors.extend(e.messages)

        if errors:
            for e in errors:
                messages.error(request, e)
            return redirect(request.META.get("HTTP_REFERER", "/"))

        if username and username != user.username:
            user.username = username

        if new1:
            user.set_password(new1)
            user.save()
            update_session_auth_hash(request, user)
        else:
            user.save()

        messages.success(request, "Account updated.")
        return redirect(request.META.get("HTTP_REFERER", "/"))

    return redirect("dashboard")


@login_required
def settings(request):
    # Render a settings page that shows profile and relevant settings
    return render(request, "tracker/settings.html", {"user": request.user})


# ---------------------------------------------------------------- Groups
@login_required
def group_list(request):
    groups = Group.objects.all()
    return render(request, "tracker/groups/list.html", {"groups": groups})


@login_required
def group_detail(request, pk):
    group = get_object_or_404(Group, pk=pk)
    clients = group.members.all()
    return render(request, "tracker/groups/detail.html", {"group": group, "clients": clients})


@login_required
def group_form(request, pk=None):
    group = get_object_or_404(Group, pk=pk) if pk else None
    if request.method == "POST":
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, "Group saved.")
            return redirect("group_list")
    else:
        form = GroupForm(instance=group)
    return render(request, "tracker/groups/form.html", {"form": form, "group": group})


@login_required
def group_delete(request, pk):
    group = get_object_or_404(Group, pk=pk)
    if request.method == "POST":
        try:
            group.delete()
            messages.success(request, "Group deleted.")
        except ProtectedError:
            messages.error(request, "This group still has clients assigned. Reassign or remove them first.")
    return redirect("group_list")


@login_required
def group_add_member(request, pk):
    group = get_object_or_404(Group, pk=pk)
    if request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            messages.success(request, f"Member '{client.name}' added to {group.name}.")
            return redirect("group_list")
    else:
        form = ClientForm(initial={"group": group})
    return render(request, "tracker/clients/form.html", {"form": form, "group": group, "client": None})


# ---------------------------------------------------------------- Clients
@login_required
def client_list(request):
    q = request.GET.get("q", "").strip()
    clients = Member.objects.select_related("group").all()
    if q:
        clients = clients.filter(Q(name__icontains=q) | Q(phone__icontains=q) | Q(id_number__icontains=q))
    return render(request, "tracker/clients/list.html", {"clients": clients, "q": q})


@login_required
def client_form(request, pk=None):
    client = get_object_or_404(Member, pk=pk) if pk else None
    if request.method == "POST":
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, "Member saved.")
            return redirect("client_list")
    else:
        form = ClientForm(instance=client)
    return render(request, "tracker/clients/form.html", {"form": form, "client": client})


@login_required
def client_delete(request, pk):
    client = get_object_or_404(Member, pk=pk)
    if request.method == "POST":
        try:
            client.delete()
            messages.success(request, "Member deleted.")
        except ProtectedError:
            messages.error(request, "This member has loan records. Loans must stay linked to their client.")
    return redirect("client_list")


# ---------------------------------------------------------------- Loans
@login_required
def loan_list(request):
    status_filter = request.GET.get("status", "all")
    loans = list(Loan.objects.select_related("client", "group").prefetch_related("payments"))
    if status_filter != "all":
        loans = [l for l in loans if l.status == status_filter]
    return render(request, "tracker/loans/list.html", {"loans": loans, "status_filter": status_filter})


@login_required
def loan_request(request):
    if request.method == "POST":
        form = LoanRequestForm(request.POST)
        if form.is_valid():
            loan = form.save(commit=False)
            loan.requested_by = request.user
            loan.stage = "requested"
            loan.save()
            messages.success(request, "Loan request submitted.")
            return redirect("loan_detail", pk=loan.pk)
    else:
        form = LoanRequestForm()
    return render(request, "tracker/loans/form.html", {"form": form})


@login_required
def loan_detail(request, pk):
    loan = get_object_or_404(Loan.objects.select_related("client", "group").prefetch_related("payments"), pk=pk)
    return render(request, "tracker/loans/detail.html", {"loan": loan})


@login_required
def loan_approve(request, pk):
    loan = get_object_or_404(Loan, pk=pk)
    if request.method == "POST":
        form = ApproveLoanForm(request.POST)
        if form.is_valid():
            loan.approve(form.cleaned_data["disbursement_date"])
            messages.success(request, "Loan approved and disbursed.")
            return redirect("loan_detail", pk=loan.pk)
    else:
        form = ApproveLoanForm(initial={"disbursement_date": datetime.date.today()})
    return render(request, "tracker/loans/approve.html", {"form": form, "loan": loan})


@login_required
def loan_payment(request, pk):
    loan = get_object_or_404(Loan, pk=pk)
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.loan = loan
            payment.recorded_by = request.user
            payment.save()
            messages.success(request, "Payment recorded.")
            return redirect("loan_detail", pk=loan.pk)
    else:
        form = PaymentForm(initial={"date": datetime.date.today()})
    return render(request, "tracker/loans/payment.html", {"form": form, "loan": loan})


@login_required
def loan_export_csv(request):
    status_filter = request.GET.get("status", "all")
    loans = list(Loan.objects.select_related("client", "group").prefetch_related("payments"))
    if status_filter != "all":
        loans = [l for l in loans if l.status == status_filter]

    response = HttpResponse(content_type="text/csv")
    filename = f"loans-{status_filter}-{datetime.date.today().isoformat()}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "Client", "Group", "Type", "Asset description", "Principal", "Interest rate (%)",
        "Duration (months)", "Requested", "Disbursed", "Maturity", "Status",
        "Total due", "Total paid", "Balance", "Requested by",
    ])
    for l in loans:
        writer.writerow([
            l.client.name, l.group.name if l.group else "", l.get_loan_type_display(),
            l.asset_description, l.principal, l.interest_rate, l.duration_months,
            l.request_date, l.disbursement_date or "", l.maturity_date or "", l.status_label,
            l.total_due, l.total_paid, l.balance, l.requested_by or "",
        ])
    return response


@login_required
def loan_delete(request, pk):
    loan = get_object_or_404(Loan, pk=pk)
    if request.method == "POST":
        loan.delete()
        messages.success(request, "Loan record deleted.")
        return redirect("loan_list")
    return render(request, "tracker/loans/delete.html", {"loan": loan})


# ---------------------- Staff / agents
@login_required
def staff_list(request):
    staffs = Staff.objects.select_related("user").all()
    return render(request, "tracker/staff/list.html", {"staffs": staffs})


@login_required
def staff_form(request, pk=None):
    staff = get_object_or_404(Staff, pk=pk) if pk else None
    if request.method == "POST":
        form = StaffForm(request.POST, instance=staff)
        if form.is_valid():
            s = form.save()
            AuditLog.objects.create(user=request.user, action="staff_saved", model="Staff", object_id=str(s.pk), details=str(s))
            messages.success(request, "Staff saved.")
            return redirect("staff_list")
    else:
        form = StaffForm(instance=staff)
    return render(request, "tracker/staff/form.html", {"form": form, "staff": staff})


@login_required
def staff_detail(request, pk):
    staff = get_object_or_404(Staff.objects.select_related('user'), pk=pk)
    tasks = staff.tasks.all()
    return render(request, "tracker/staff/detail.html", {"staff": staff, "tasks": tasks})


@login_required
def staff_task_new(request, pk=None):
    staff = get_object_or_404(Staff, pk=pk) if pk else None
    if request.method == 'POST':
        form = StaffTaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.assigned_by = request.user
            task.save()
            AuditLog.objects.create(user=request.user, action='task_assigned', model='StaffTask', object_id=str(task.pk), details=task.title)
            messages.success(request, 'Task assigned.')
            return redirect('staff_detail', pk=task.staff.pk)
    else:
        initial = { 'staff': staff } if staff else {}
        form = StaffTaskForm(initial=initial)
    return render(request, 'tracker/staff/task_form.html', { 'form': form, 'staff': staff })


# ---------------------- Audit logs
@login_required
def audit_list(request):
    logs = AuditLog.objects.select_related("user").all()[:200]
    return render(request, "tracker/audit/list.html", {"logs": logs})


# ---------------------- Savings
@login_required
def saving_transaction(request):
    members = Member.objects.select_related("group").all()
    member_group_map = {str(m.pk): (str(m.group.pk) if m.group else "") for m in members}
    member_group_json = json.dumps(member_group_map)

    if request.method == "POST":
        form = SavingTransactionForm(request.POST)
        if form.is_valid():
            tx = form.save(commit=False)
            tx.recorded_by = request.user
            tx.save()
            tx.apply()
            messages.success(request, "Saving transaction recorded.")
            return redirect("dashboard")
    else:
        form = SavingTransactionForm()
    return render(request, "tracker/savings/transaction.html", {"form": form, "member_group_json": member_group_json})


@login_required
def member_savings(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    acc, _ = MemberSaving.objects.get_or_create(member=member)
    transactions = member.saving_transactions.all()
    return render(request, "tracker/savings/member.html", {"account": acc, "transactions": transactions, "member": member})


@login_required
def group_savings(request, group_id):
    group = get_object_or_404(Group, pk=group_id)
    acc, _ = GroupSaving.objects.get_or_create(group=group)
    transactions = group.saving_transactions.all()
    return render(request, "tracker/savings/group.html", {"account": acc, "transactions": transactions, "group": group})


# ---------------------- Reports
@login_required
def financial_report(request):
    # produce a small CSV with key financial totals
    total_member_savings = MemberSaving.objects.aggregate(total=Sum("balance"))["total"] or 0
    total_group_savings = GroupSaving.objects.aggregate(total=Sum("balance"))["total"] or 0
    org = OrganizationSaving.objects.first()
    org_balance = org.balance if org else 0

    loans = list(Loan.objects.all())
    total_disbursed = sum((l.principal for l in loans), Decimal("0"))
    outstanding = sum((l.balance for l in loans), Decimal("0"))

    response = HttpResponse(content_type="text/csv")
    filename = f"financial-report-{datetime.date.today().isoformat()}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(["metric", "value"])
    writer.writerow(["total_member_savings", total_member_savings])
    writer.writerow(["total_group_savings", total_group_savings])
    writer.writerow(["organization_savings", org_balance])
    writer.writerow(["total_loan_principal", total_disbursed])
    writer.writerow(["outstanding_loan_balance", outstanding])
    return response


@login_required
def loan_report(request):
    # reuse loan_export_csv but add transactions summary
    return loan_export_csv(request)


@login_required
def financial_report_view(request):
    # Render a human-readable page showing financial metrics with download option
    total_member_savings = MemberSaving.objects.aggregate(total=Sum("balance"))["total"] or Decimal("0")
    total_group_savings = GroupSaving.objects.aggregate(total=Sum("balance"))["total"] or Decimal("0")
    org = OrganizationSaving.objects.first()
    org_balance = org.balance if org else Decimal("0")

    loans = list(Loan.objects.all())
    total_disbursed = sum((l.principal for l in loans), Decimal("0"))
    outstanding = sum((l.balance for l in loans), Decimal("0"))

    context = {
        "total_member_savings": total_member_savings,
        "total_group_savings": total_group_savings,
        "organization_savings": org_balance,
        "total_loan_principal": total_disbursed,
        "outstanding_loan_balance": outstanding,
    }
    return render(request, "tracker/reports/financial.html", context)


@login_required
def loan_report_view(request):
    # Render a human-readable loan report with option to download CSV
    loans = Loan.objects.select_related("client", "group").prefetch_related("payments").all()
    return render(request, "tracker/reports/loans.html", {"loans": loans})