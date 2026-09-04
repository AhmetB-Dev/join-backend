from django.db import migrations, models
from django.db.models import Q


def recalculate_task_progress(apps, schema_editor):
    Task = apps.get_model("tasks", "Task")
    Subtask = apps.get_model("tasks", "Subtask")

    for task in Task.objects.all().iterator():
        subtasks = Subtask.objects.filter(task_id=task.pk)
        total = subtasks.count()
        completed = subtasks.filter(completed=True).count()
        progress = round((completed / total) * 100) if total else 0
        Task.objects.filter(pk=task.pk).update(progress=progress)


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0003_require_task_owner"),
    ]

    operations = [
        migrations.RunPython(recalculate_task_progress, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.CheckConstraint(
                condition=Q(progress__gte=0, progress__lte=100),
                name="task_progress_between_0_and_100",
            ),
        ),
    ]
