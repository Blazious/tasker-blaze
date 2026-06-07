from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0004_platforminvoicepayment"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="econfirm_confirmation_code",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
