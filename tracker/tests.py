import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .forms import LoanRequestForm, StaffForm
from .models import AuditLog, Group, Loan, Member, Staff


class LoanInterestAndIdentifiersTests(TestCase):
    def test_fixed_interest_is_1_8_percent_and_auto_numbers_are_assigned(self):
        group = Group.objects.create(name="Umoja Group")

        self.assertRegex(group.group_number, r"^G-\d{4}$")

        member = Member.objects.create(name="Jane Wanjiru", group=group)

        self.assertRegex(member.member_number, r"^G-\d{4}-M-\d{3}$")

        loan = Loan.objects.create(client=member, principal=Decimal("1000.00"), duration_months=1)

        self.assertEqual(loan.interest_rate, Decimal("1.80"))
        self.assertEqual(loan.total_amount_to_be_paid, Decimal("1018.00"))
        self.assertEqual(loan.profit_collected, Decimal("18.00"))

    def test_interest_is_calculated_per_month_on_the_principal(self):
        group = Group.objects.create(name="Kibera Group")
        member = Member.objects.create(name="John Kamau", group=group)
        loan = Loan.objects.create(client=member, principal=Decimal("1000.00"), duration_months=6)

        self.assertEqual(loan.total_amount_to_be_paid, Decimal("1108.00"))
        self.assertEqual(loan.monthly_installment, Decimal("184.6666666666666666666666667"))

    def test_monthly_installment_and_missed_installments_are_calculated(self):
        group = Group.objects.create(name="Yetu Group")
        member = Member.objects.create(name="Mary Njeri", group=group)
        loan = Loan.objects.create(
            client=member,
            principal=Decimal("1200.00"),
            duration_months=6,
            disbursement_date=datetime.date(2026, 1, 10),
        )

        self.assertEqual(loan.monthly_installment, Decimal("221.60"))
        self.assertEqual(loan.current_monthly_due_count, 6)
        self.assertEqual(loan.missed_installments, 6)

    def test_loan_request_form_accepts_valid_submission(self):
        group = Group.objects.create(name="Nakuru Group")
        member = Member.objects.create(name="Grace Achieng", group=group)

        form = LoanRequestForm(data={
            "client": member.pk,
            "loan_type": "cash",
            "asset_description": "",
            "principal": "1000",
            "duration_months": "6",
            "request_date": "2026-09-06",
            "notes": "",
        })

        self.assertTrue(form.is_valid(), form.errors.as_json())
        loan = form.save(commit=False)
        self.assertEqual(loan.total_amount_to_be_paid, Decimal("1108.00"))

    def test_staff_form_creates_related_user_before_save(self):
        form = StaffForm(data={
            "username": "agent_one",
            "first_name": "Alice",
            "last_name": "Mwangi",
            "email": "alice@example.com",
            "password": "secret123",
            "role": "employee",
            "phone": "0712345678",
        })

        self.assertTrue(form.is_valid(), form.errors.as_json())
        staff = form.save()
        self.assertEqual(staff.user.username, "agent_one")
        self.assertTrue(staff.user.check_password("secret123"))
        self.assertTrue(Staff.objects.filter(pk=staff.pk).exists())

    def test_staff_delete_removes_related_profile_and_user(self):
        User = get_user_model()
        user = User.objects.create_user(username="agent_delete", email="delete@example.com", password="secret123")
        staff = Staff.objects.create(user=user, role="employee", phone="0712345678")
        self.client.force_login(User.objects.create_superuser(username="admin_delete", email="admin@example.com", password="adminpass"))

        response = self.client.post(f"/staff/{staff.pk}/delete/")

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Staff.objects.filter(pk=staff.pk).exists())
        self.assertFalse(User.objects.filter(pk=user.pk).exists())

    def test_staff_delete_missing_record_redirects_instead_of_404(self):
        User = get_user_model()
        self.client.force_login(User.objects.create_superuser(username="admin_missing", email="admin_missing@example.com", password="adminpass"))

        response = self.client.get("/staff/99999/delete/")

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/staff/")

    def test_member_and_group_search_support_unique_numbers(self):
        User = get_user_model()
        self.client.force_login(User.objects.create_superuser(username="search_admin", email="search@example.com", password="adminpass"))

        group = Group.objects.create(name="Kisumu Group")
        member = Member.objects.create(name="Jane Maina", group=group, phone="0712345678", id_number="12345678")

        member_response = self.client.get(f"/clients/?q={member.member_number}")
        self.assertContains(member_response, member.name)

        group_response = self.client.get(f"/groups/?q={group.group_number}")
        self.assertContains(group_response, group.name)

    def test_group_delete_route_removes_group_record(self):
        User = get_user_model()
        self.client.force_login(User.objects.create_superuser(username="group_delete_admin", email="group_delete@example.com", password="adminpass"))
        group = Group.objects.create(name="Delete Me Group")

        response = self.client.post(f"/groups/{group.pk}/delete/")

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Group.objects.filter(pk=group.pk).exists())

    def test_group_delete_get_returns_confirmation_page(self):
        User = get_user_model()
        self.client.force_login(User.objects.create_superuser(username="group_delete_get_admin", email="group_delete_get@example.com", password="adminpass"))
        group = Group.objects.create(name="Confirm Delete Group")

        response = self.client.get(f"/groups/{group.pk}/delete/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Delete group")

    def test_group_delete_logs_the_event(self):
        User = get_user_model()
        admin = User.objects.create_superuser(username="audit_delete_admin", email="audit_delete@example.com", password="adminpass")
        self.client.force_login(admin)
        group = Group.objects.create(name="Audit Delete Group")

        self.client.post(f"/groups/{group.pk}/delete/")

        self.assertTrue(AuditLog.objects.filter(user=admin, action="group_deleted", model="Group", object_id=str(group.pk)).exists())

    def test_loan_payment_logs_a_transaction_event(self):
        User = get_user_model()
        admin = User.objects.create_superuser(username="payment_audit_admin", email="payment_audit@example.com", password="adminpass")
        self.client.force_login(admin)
        group = Group.objects.create(name="Payment Audit Group")
        member = Member.objects.create(name="Loan Payer", group=group, phone="0711111111", id_number="33333333")
        loan = Loan.objects.create(client=member, principal=Decimal("1000.00"), duration_months=6)

        response = self.client.post(f"/loans/{loan.pk}/payment/", {
            "amount": "200.00",
            "date": "2026-09-06",
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(AuditLog.objects.filter(user=admin, action="loan_payment_recorded", model="Payment", object_id__isnull=False).exists())

    def test_missed_installment_report_only_includes_missed_rows_and_amount_due(self):
        User = get_user_model()
        self.client.force_login(User.objects.create_superuser(username="missed_report_admin", email="missed_report@example.com", password="adminpass"))
        group = Group.objects.create(name="Missed Report Group")
        on_time_member = Member.objects.create(name="On Time Member", group=group, phone="0700000001", id_number="11111111")
        missed_member = Member.objects.create(name="Missed Member", group=group, phone="0700000002", id_number="22222222")

        Loan.objects.create(client=on_time_member, principal=Decimal("1200.00"), duration_months=6, disbursement_date=datetime.date.today())
        Loan.objects.create(client=missed_member, principal=Decimal("1200.00"), duration_months=6, disbursement_date=datetime.date(2026, 1, 10))

        response = self.client.get("/reports/installments/view/")

        self.assertContains(response, missed_member.name)
        self.assertNotContains(response, on_time_member.name)
        self.assertContains(response, "Amount due")
        self.assertContains(response, "KES 1,329.60")
        self.assertContains(response, "6")
