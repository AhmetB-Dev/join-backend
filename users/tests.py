from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from contacts.models import Contact
from tasks.models import Task


class AuthApiTests(APITestCase):
    def test_register_login_and_me(self):
        register = self.client.post(
            "/api/auth/register/",
            {"name": "Max Mustermann", "email": "max@example.com", "password": "StrongPass-2026!"},
            format="json",
        )
        self.assertEqual(register.status_code, status.HTTP_201_CREATED)
        self.assertIn("token", register.data)
        self.assertNotIn("password", register.data["user"])

        user = get_user_model().objects.get(email="max@example.com")
        self.assertNotEqual(user.password, "StrongPass-2026!")
        self.assertTrue(user.check_password("StrongPass-2026!"))

        login = self.client.post(
            "/api/auth/login/",
            {"email": "MAX@example.com", "password": "StrongPass-2026!"},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {login.data['token']}")
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data["email"], "max@example.com")

        self.assertEqual(Contact.objects.filter(owner_id=me.data["id"]).count(), 0)
        self.assertEqual(Task.objects.filter(owner_id=me.data["id"]).count(), 0)

    def test_duplicate_registration_is_rejected(self):
        payload = {
            "name": "Max Mustermann",
            "email": "max@example.com",
            "password": "StrongPass-2026!",
        }
        first = self.client.post("/api/auth/register/", payload, format="json")
        second = self.client.post(
            "/api/auth/register/",
            {**payload, "email": "MAX@example.com"},
            format="json",
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(get_user_model().objects.filter(email="max@example.com").count(), 1)

    def test_unknown_email_and_wrong_password_use_same_login_error(self):
        get_user_model().objects.create_user(
            username="login@example.com",
            email="login@example.com",
            name="Login User",
            password="StrongPass-2026!",
        )

        unknown = self.client.post(
            "/api/auth/login/",
            {"email": "unknown@example.com", "password": "StrongPass-2026!"},
            format="json",
        )
        wrong_password = self.client.post(
            "/api/auth/login/",
            {"email": "login@example.com", "password": "WrongPass-2026!"},
            format="json",
        )

        self.assertEqual(unknown.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(wrong_password.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(unknown.data, wrong_password.data)

    def test_logout_invalidates_token(self):
        user = get_user_model().objects.create_user(
            username="logout@example.com",
            email="logout@example.com",
            name="Logout User",
            password="StrongPass-2026!",
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        logout = self.client.post("/api/auth/logout/", {}, format="json")
        self.assertEqual(logout.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Token.objects.filter(key=token.key).exists())

        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_endpoints_reject_missing_token(self):
        me = self.client.get("/api/auth/me/")
        logout = self.client.post("/api/auth/logout/", {}, format="json")

        self.assertEqual(me.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(logout.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_guest_login_gets_isolated_demo_data(self):
        first = self.client.post("/api/auth/guest/", {}, format="json")
        second = self.client.post("/api/auth/guest/", {}, format="json")
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertTrue(first.data["isGuest"])
        self.assertNotEqual(first.data["token"], second.data["token"])

        first_user = get_user_model().objects.get(pk=first.data["user"]["id"])
        second_user = get_user_model().objects.get(pk=second.data["user"]["id"])
        self.assertGreater(Contact.objects.filter(owner=first_user).count(), 0)
        self.assertGreater(Task.objects.filter(owner=first_user).count(), 0)
        self.assertEqual(
            Contact.objects.filter(owner=first_user).count(),
            Contact.objects.filter(owner=second_user).count(),
        )
        self.assertEqual(
            Task.objects.filter(owner=first_user).count(),
            Task.objects.filter(owner=second_user).count(),
        )

    def test_guest_logout_deletes_guest_demo_data(self):
        guest = self.client.post("/api/auth/guest/", {}, format="json")
        user_id = guest.data["user"]["id"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {guest.data['token']}")

        logout = self.client.post("/api/auth/logout/", {}, format="json")
        self.assertEqual(logout.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(get_user_model().objects.filter(pk=user_id).exists())
        self.assertFalse(Contact.objects.filter(owner_id=user_id).exists())
        self.assertFalse(Task.objects.filter(owner_id=user_id).exists())
