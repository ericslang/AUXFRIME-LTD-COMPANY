from decimal import Decimal

from django import forms

from .models import Member, Group, Loan, Payment
from .models import Staff, SavingTransaction
from .models import StaffTask
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ["name", "group_number", "location", "meeting_day", "officer", "head", "formed_date"]
        widgets = {
            "formed_date": forms.DateInput(attrs={"type": "date"}),
            "name": forms.TextInput(attrs={"placeholder": "e.g. Umoja Women Group"}),
            "location": forms.TextInput(attrs={"placeholder": "e.g. Kawangware"}),
            "officer": forms.TextInput(attrs={"placeholder": "Staff name"}),
            "group_number": forms.TextInput(attrs={"readonly": True}),
        }


class ClientForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ["name", "group", "member_number", "phone", "id_number", "join_date", "status"]
        widgets = {
            "join_date": forms.DateInput(attrs={"type": "date"}),
            "name": forms.TextInput(attrs={"placeholder": "e.g. Jane Wanjiru"}),
            "phone": forms.TextInput(attrs={"placeholder": "07xx xxx xxx"}),
            "member_number": forms.TextInput(attrs={"readonly": True}),
        }


class LoanRequestForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ["client", "loan_type", "asset_description", "principal",
                  "duration_months", "request_date", "notes"]
        widgets = {
            "request_date": forms.DateInput(attrs={"type": "date"}),
            "asset_description": forms.TextInput(attrs={"placeholder": "e.g. Water pump, dairy cow, sewing machine"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "principal": forms.NumberInput(attrs={"min": 0, "step": "0.01"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        principal = cleaned_data.get("principal")
        duration = cleaned_data.get("duration_months") or 1
        if principal is not None:
            self.instance.interest_rate = Loan.FIXED_INTEREST_RATE
            self.instance.total_amount_to_be_paid = principal + (
                principal * (Loan.FIXED_INTEREST_RATE / Decimal("100")) * Decimal(duration)
            )
        return cleaned_data

    def save(self, commit=True):
        loan = super().save(commit=False)
        principal = loan.principal or Decimal("0")
        duration = loan.duration_months or 1
        loan.interest_rate = Loan.FIXED_INTEREST_RATE
        loan.total_amount_to_be_paid = principal + (
            principal * (Loan.FIXED_INTEREST_RATE / Decimal("100")) * Decimal(duration)
        )
        if commit:
            loan.save()
        return loan


class ApproveLoanForm(forms.Form):
    disbursement_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["amount", "date"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "amount": forms.NumberInput(attrs={"min": 0, "step": "0.01"}),
        }


class StaffForm(forms.ModelForm):
    # allow creating a new User inline when adding a staff
    username = forms.CharField(required=False, help_text="Provide a username to create a new user")
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    email = forms.EmailField(required=False)
    password = forms.CharField(required=False, widget=forms.PasswordInput, help_text="Optional: set a password for the new user")

    class Meta:
        model = Staff
        fields = ["username", "first_name", "last_name", "email", "password", "role", "phone", "assigned_groups"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # add friendly placeholders
        self.fields['username'].widget.attrs.update({'placeholder': 'newusername'})
        self.fields['first_name'].widget.attrs.update({'placeholder': 'First name'})
        self.fields['last_name'].widget.attrs.update({'placeholder': 'Last name'})
        self.fields['email'].widget.attrs.update({'placeholder': 'email@example.com'})
        self.fields['password'].widget.attrs.update({'placeholder': 'optional password'})
        # if editing existing staff, preload user fields
        if self.instance and self.instance.pk and self.instance.user:
            u = self.instance.user
            self.fields['username'].initial = u.username
            self.fields['first_name'].initial = u.first_name
            self.fields['last_name'].initial = u.last_name
            self.fields['email'].initial = u.email

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get('username')
        if not username:
            raise ValidationError('Username is required.')

        if not self.instance or not self.instance.pk:
            password = cleaned.get('password')
            if not password:
                raise ValidationError('Password is required for a new user.')

        existing_user = None
        if self.instance and self.instance.pk:
            try:
                existing_user = self.instance.user
            except Staff.user.RelatedObjectDoesNotExist:
                existing_user = None
        qs = User.objects.filter(username=username)
        if existing_user:
            qs = qs.exclude(pk=existing_user.pk)
        if qs.exists():
            raise ValidationError({'username': 'Username already in use.'})

        return cleaned

    def save(self, commit=True):
        username = self.cleaned_data.get('username')
        user = User.objects.filter(username=username).first()
        if not user:
            password = self.cleaned_data.get('password')
            if not password:
                raise ValidationError('Password is required for a new user.')
            user = User.objects.create_user(
                username=username,
                email=self.cleaned_data.get('email', ''),
                password=password,
                first_name=self.cleaned_data.get('first_name', ''),
                last_name=self.cleaned_data.get('last_name', ''),
            )
        elif self.cleaned_data.get('password'):
            user.set_password(self.cleaned_data['password'])
            if commit:
                user.save()

        self.instance.user = user
        return super().save(commit=commit)


class SavingTransactionForm(forms.ModelForm):
    class Meta:
        model = SavingTransaction
        fields = ["member", "group", "transaction_type", "amount", "date", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "amount": forms.NumberInput(attrs={"min": 0, "step": "0.01"}),
        }


class StaffTaskForm(forms.ModelForm):
    class Meta:
        model = StaffTask
        fields = ["staff", "title", "description", "due_date", "status"]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }