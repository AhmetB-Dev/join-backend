from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def ensure_every_task_has_owner(apps, schema_editor):
    Task = apps.get_model("tasks", "Task")
    ownerless_count = Task.objects.filter(owner__isnull=True).count()
    if ownerless_count:
        raise RuntimeError(
            "Cannot make Task.owner required: "
            f"{ownerless_count} owner-less task(s) still exist. "
            "Assign an owner to those legacy rows before running this migration again."
        )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("contacts", "0003_require_contact_owner"),
        ("tasks", "0002_task_owner"),
    ]

    operations = [
        migrations.RunPython(ensure_every_task_has_owner, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="task",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="tasks",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
