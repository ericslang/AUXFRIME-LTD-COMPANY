from django import forms

from .models import Member, Group, Loan, Payment
from .models import Staff, SavingTransaction
from .models import StaffTask
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ["name", "location", "meeting_day", "officer", "head", "formed_date"]
        widgets = {
            "formed_date": forms.DateInput(attrs={"type": "date"}),
            "name": forms.TextInput(attrs={"placeholder": "e.g. Umoja Women Group"}),
            "location": forms.TextInput(attrs={"placeholder": "e.g. Kawangware"}),
            "officer": forms.TextInput(attrs={"placeholder": "Staff name"}),
        }


class ClientForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ["name", "group", "phone", "id_number", "join_date", "status"]
        widgets = {
            "join_date": forms.DateInput(attrs={"type": "date"}),
            "name": forms.TextInput(attrs={"placeholder": "e.g. Jane Wanjiru"}),
            "phone": forms.TextInput(attrs={"placeholder": "07xx xxx xxx"}),
        }


class LoanRequestForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ["client", "loan_type", "asset_description", "principal",
                  "interest_rate", "duration_months", "request_date", "notes"]
        widgets = {
            "request_date": forms.DateInput(attrs={"type": "date"}),
            "asset_description": forms.TextInput(attrs={"placeholder": "e.g. Water pump, dairy cow, sewing machine"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "principal": forms.NumberInput(attrs={"min": 0, "step": "0.01"}),
        }


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
        fields = ["username", "first_name", "last_name", "email", "password", "user", "role", "phone", "assigned_groups"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # add friendly placeholders
        self.fields['username'].widget.attrs.update({'placeholder': 'newusername (leave blank to pick existing user)'})
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
        user = cleaned.get('user')
        username = cleaned.get('username')
        if not user and not username:
            raise ValidationError('Either select an existing user or provide a username to create one.')
        # if username provided, ensure it's not already taken (unless it's the same as the existing user)
        if username:
            qs = User.objects.filter(username=username)
            if self.instance and self.instance.user:
                qs = qs.exclude(pk=self.instance.user.pk)
            if qs.exists():
                raise ValidationError({'username': 'Username already in use.'})
        return cleaned

    def save(self, commit=True):
        user = self.cleaned_data.get('user')
        username = self.cleaned_data.get('username')
        if not user and username:
            # create new user
            u = User(username=username, first_name=self.cleaned_data.get('first_name', ''), last_name=self.cleaned_data.get('last_name', ''), email=self.cleaned_data.get('email', ''))
            pwd = self.cleaned_data.get('password')
            if pwd:
                u.set_password(pwd)
            else:
                u.set_unusable_password()
            if commit:
                u.save()
            user = u
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