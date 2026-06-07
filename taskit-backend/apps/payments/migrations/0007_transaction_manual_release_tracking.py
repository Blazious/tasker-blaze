from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0006_transaction_buyer_confirmed_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="client_approved_release_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="transaction",
            name="manual_release_requested_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="transaction",
            name="manual_release_synced_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
