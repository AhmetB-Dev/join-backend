from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from tasks.cache import invalidate_task_list_cache

from .models import Contact
from .serializers import ContactSerializer


class ContactViewSet(ModelViewSet):
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Contact.objects.filter(owner=self.request.user)
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset

    def perform_create(self, serializer):
        contact = serializer.save(owner=self.request.user)
        invalidate_task_list_cache(contact.owner_id)

    def perform_update(self, serializer):
        contact = serializer.save()
        invalidate_task_list_cache(contact.owner_id)

    def perform_destroy(self, instance):
        owner_id = instance.owner_id
        instance.delete()
        invalidate_task_list_cache(owner_id)
