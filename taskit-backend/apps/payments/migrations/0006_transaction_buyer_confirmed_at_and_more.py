from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0005_transaction_econfirm_confirmation_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="buyer_confirmed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="transaction",
            name="econfirm_webhook_received_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
