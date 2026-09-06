from decimal import Decimal

from django.db import migrations, models


def populate_numbers_and_totals(apps, schema_editor):
    Group = apps.get_model('tracker', 'Group')
    Member = apps.get_model('tracker', 'Member')
    Loan = apps.get_model('tracker', 'Loan')

    for index, group in enumerate(Group.objects.order_by('id'), start=1):
        if not group.group_number:
            group.group_number = f'G-{index:04d}'
            group.save(update_fields=['group_number'])

        members = list(Member.objects.filter(group=group).order_by('id'))
        for member_index, member in enumerate(members, start=1):
            if not member.member_number:
                member.member_number = f'{group.group_number}-M-{member_index:03d}'
                member.save(update_fields=['member_number'])

    for loan in Loan.objects.all():
        loan.interest_rate = Decimal('1.80')
        loan.total_amount_to_be_paid = (loan.principal or Decimal('0')) * (Decimal('1') + loan.interest_rate / Decimal('100'))
        loan.save(update_fields=['interest_rate', 'total_amount_to_be_paid'])


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0005_group_head_alter_staff_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='group_number',
            field=models.CharField(blank=True, max_length=20, unique=True),
        ),
        migrations.AddField(
            model_name='loan',
            name='total_amount_to_be_paid',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12, verbose_name='Total amount to be paid'),
        ),
        migrations.AddField(
            model_name='member',
            name='member_number',
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AlterField(
            model_name='loan',
            name='interest_rate',
            field=models.DecimalField(decimal_places=2, default=Decimal('1.80'), max_digits=5, verbose_name='Interest rate (% flat, over full term)'),
        ),
        migrations.RunPython(populate_numbers_and_totals, reverse_code=migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='member',
            constraint=models.UniqueConstraint(fields=('group', 'member_number'), name='unique_member_number_per_group'),
        ),
    ]
