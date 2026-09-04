from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def ensure_every_contact_has_owner(apps, schema_editor):
    Contact = apps.get_model("contacts", "Contact")
    ownerless_count = Contact.objects.filter(owner__isnull=True).count()
    if ownerless_count:
        raise RuntimeError(
            "Cannot make Contact.owner required: "
            f"{ownerless_count} owner-less contact(s) still exist. "
            "Assign an owner to those legacy rows before running this migration again."
        )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("contacts", "0002_contact_owner"),
    ]

    operations = [
        migrations.RunPython(ensure_every_contact_has_owner, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="contact",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="contacts",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
