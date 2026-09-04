from django.db import connection
from django.db.utils import OperationalError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.reverse import reverse


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Report that the Django process is alive."""
    return Response({"status": "ok", "service": "JOIN API"})


@api_view(["GET"])
@permission_classes([AllowAny])
def readiness_check(request):
    """Report whether the API can reach its database and accept traffic."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except OperationalError:
        return Response(
            {"status": "unavailable", "database": "unavailable"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return Response({"status": "ready", "database": "ok"})


@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request):
    return Response(
        {
            "health": reverse("health-check", request=request),
            "readiness": reverse("readiness-check", request=request),
            "register": reverse("register", request=request),
            "login": reverse("login", request=request),
            "guestLogin": reverse("guest-login", request=request),
            "contacts": reverse("contact-list", request=request),
            "tasks": reverse("task-list", request=request),
        }
    )
