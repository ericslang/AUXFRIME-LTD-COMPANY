import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse


MEETING_DAYS = [
    ("Monday", "Monday"), ("Tuesday", "Tuesday"), ("Wednesday", "Wednesday"),
    ("Thursday", "Thursday"), ("Friday", "Friday"), ("Saturday", "Saturday"),
    ("Sunday", "Sunday"),
]


class Group(models.Model):
    name = models.CharField(max_length=150)
    location = models.CharField(max_length=150, blank=True)
    meeting_day = models.CharField(max_length=10, choices=MEETING_DAYS, default="Monday")
    officer = models.CharField("Loan officer", max_length=120, blank=True)
    head = models.ForeignKey('Member', on_delete=models.SET_NULL, null=True, blank=True, related_name='headed_groups')
    formed_date = models.DateField(default=datetime.date.today)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("group_list")

    @property
    def member_count(self):
        return self.members.count()


class Member(models.Model):
    STATUS_CHOICES = [("active", "Active"), ("inactive", "Inactive")]

    name = models.CharField(max_length=150)
    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name="members", null=True, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    id_number = models.CharField("National ID number", max_length=40, blank=True)
    join_date = models.DateField(default=datetime.date.today)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("client_list")


class Loan(models.Model):
    TYPE_CHOICES = [("cash", "Cash"), ("asset", "Asset")]
    STAGE_CHOICES = [("requested", "Requested"), ("active", "Active")]

    client = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="loans")
    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name="loans", null=True, blank=True)
    loan_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="cash")
    asset_description = models.CharField(max_length=200, blank=True)
    principal = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField("Interest rate (% flat, over full term)", max_digits=5, decimal_places=2, default=Decimal("10.00"))
    duration_months = models.PositiveIntegerField(default=6)

    request_date = models.DateField(default=datetime.date.today)
    disbursement_date = models.DateField(null=True, blank=True)
    maturity_date = models.DateField(null=True, blank=True)
    stage = models.CharField(max_length=10, choices=STAGE_CHOICES, default="requested")

    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="loans_requested")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-request_date", "-id"]

    def __str__(self):
        return f"{self.client.name} — {self.get_loan_type_display()} loan"

    def save(self, *args, **kwargs):
        if self.client_id and not self.group_id:
            self.group = self.client.group
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("loan_detail", args=[self.pk])

    @property
    def total_due(self):
        return (self.principal or Decimal("0")) * (Decimal("1") + (self.interest_rate or Decimal("0")) / Decimal("100"))

    @property
    def total_paid(self):
        return sum((p.amount for p in self.payments.all()), Decimal("0"))

    @property
    def balance(self):
        remaining = self.total_due - self.total_paid
        return remaining if remaining > 0 else Decimal("0")

    @property
    def status(self):
        if self.stage == "requested":
            return "pending"
        if self.balance <= 0:
            return "paid"
        if self.maturity_date and datetime.date.today() > self.maturity_date:
            return "overdue"
        return "active"

    @property
    def status_label(self):
        return {
            "pending": "Pending request",
            "active": "Active",
            "overdue": "Not paid / overdue",
            "paid": "Paid off",
        }[self.status]

    def approve(self, disbursement_date):
        self.disbursement_date = disbursement_date
        month = disbursement_date.month - 1 + self.duration_months
        year = disbursement_date.year + month // 12
        month = month % 12 + 1
        day = min(disbursement_date.day, 28)
        self.maturity_date = datetime.date(year, month, day)
        self.stage = "active"
        self.save()


class Payment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=datetime.date.today)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.amount} on {self.date}"


class Staff(models.Model):
    ROLE_CHOICES = [
        ("loan_officer", "Loan Officer"),
        ("treasurer", "Treasurer"),
        ("secretary", "Secretary"),
        ("chairman", "Chairman"),
        ("employee", "Employee"),
        ("admin", "Administrator"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="staff_profile")
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default="employee")
    phone = models.CharField(max_length=30, blank=True)
    assigned_groups = models.ManyToManyField(Group, blank=True, related_name="assigned_staff")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=200)
    model = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        who = self.user.get_username() if self.user else "System"
        return f"{self.timestamp.isoformat()} — {who} — {self.action}"


class MemberSaving(models.Model):
    member = models.OneToOneField(Member, on_delete=models.CASCADE, related_name="saving")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Saving: {self.member.name} — {self.balance}"


class GroupSaving(models.Model):
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name="saving")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Group saving: {self.group.name} — {self.balance}"


class OrganizationSaving(models.Model):
    name = models.CharField(max_length=150, default="Organization")
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Org saving: {self.name} — {self.balance}"


class SavingTransaction(models.Model):
    TRANSACTION_TYPES = [("deposit", "Deposit"), ("withdrawal", "Withdrawal")]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, null=True, blank=True, related_name="saving_transactions")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True, related_name="saving_transactions")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    date = models.DateField(default=datetime.date.today)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        who = self.recorded_by.get_username() if self.recorded_by else "System"
        target = self.member.name if self.member else (self.group.name if self.group else "Organization")
        return f"{self.transaction_type} {self.amount} — {target} by {who}"

    def apply(self):
        # Apply the transaction to the correct saving account
        if self.member:
            acc, _ = MemberSaving.objects.get_or_create(member=self.member)
            if self.transaction_type == "deposit":
                acc.balance += self.amount
            else:
                acc.balance -= self.amount
            acc.save()
        elif self.group:
            acc, _ = GroupSaving.objects.get_or_create(group=self.group)
            if self.transaction_type == "deposit":
                acc.balance += self.amount
            else:
                acc.balance -= self.amount
            acc.save()
        else:
            acc, _ = OrganizationSaving.objects.get_or_create(pk=1)
            if self.transaction_type == "deposit":
                acc.balance += self.amount
            else:
                acc.balance -= self.amount
            acc.save()
        # record audit
        AuditLog.objects.create(
            user=self.recorded_by,
            action=f"saving_{self.transaction_type}",
            model="SavingTransaction",
            object_id=str(self.pk or ""),
            details=f"Applied {self.amount} to {'member' if self.member else ('group' if self.group else 'organization')}",
        )


class StaffTask(models.Model):
    STATUS_CHOICES = [("open", "Open"), ("in_progress", "In Progress"), ("done", "Done")]

    staff = models.ForeignKey("Staff", on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tasks")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.staff}"