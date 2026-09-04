from unittest.mock import patch

from django.db.utils import OperationalError
from redis.exceptions import ConnectionError
from rest_framework import status
from rest_framework.test import APITestCase


class CoreApiTests(APITestCase):
    def test_health_check_is_public(self):
        response = self.client.get("/api/health/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"status": "ok", "service": "JOIN API"})

    def test_readiness_check_reports_dependencies_ready(self):
        response = self.client.get("/api/readiness/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {"status": "ready", "database": "ok", "cache": "ok"},
        )

    @patch("core.views.connection.cursor", side_effect=OperationalError)
    def test_readiness_check_returns_503_when_database_is_unavailable(self, _cursor):
        response = self.client.get("/api/readiness/")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(
            response.data,
            {"status": "unavailable", "database": "unavailable", "cache": "unknown"},
        )

    @patch("core.views.cache.set", side_effect=ConnectionError)
    def test_readiness_check_returns_503_when_cache_is_unavailable(self, _cache_set):
        response = self.client.get("/api/readiness/")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(
            response.data,
            {"status": "unavailable", "database": "ok", "cache": "unavailable"},
        )
