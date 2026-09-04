from django.conf import settings
from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .cache import invalidate_task_list_cache, task_list_cache_key
from .models import Task
from .serializers import TaskSerializer


class TaskViewSet(ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Task.objects.filter(owner=self.request.user).prefetch_related(
            "assigned_contacts",
            "subtasks",
        )
        column = self.request.query_params.get("column", "").strip()
        if column:
            queryset = queryset.filter(column=column)
        return queryset

    def list(self, request, *args, **kwargs):
        # JOIN's summary page polls the complete task list frequently. Cache only
        # that exact, unfiltered response; filtered/query-specific lists bypass
        # this cache so future API filters cannot accidentally share stale data.
        if request.query_params:
            return super().list(request, *args, **kwargs)

        key = task_list_cache_key(request.user.pk)
        cached_data = cache.get(key)
        if cached_data is not None:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)
        if response.status_code == 200:
            cache.set(key, list(response.data), timeout=settings.JOIN_TASK_CACHE_TIMEOUT)
        return response

    def perform_create(self, serializer):
        task = serializer.save()
        invalidate_task_list_cache(task.owner_id)

    def perform_update(self, serializer):
        task = serializer.save()
        invalidate_task_list_cache(task.owner_id)

    def perform_destroy(self, instance):
        owner_id = instance.owner_id
        instance.delete()
        invalidate_task_list_cache(owner_id)
