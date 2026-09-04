from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import Contact


class ContactApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester@example.com",
            email="tester@example.com",
            name="Tester",
            password="StrongPass-2026!",
        )
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_contact_crud_is_owned_by_current_user(self):
        created = self.client.post(
            "/api/contacts/",
            {"name": "Thomas Müller", "email": "THOMAS@example.com", "phone": "12345"},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["email"], "thomas@example.com")
        self.assertEqual(Contact.objects.get(pk=created.data["id"]).owner, self.user)

        response = self.client.get("/api/contacts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_contacts_from_other_users_are_hidden(self):
        other = get_user_model().objects.create_user(
            username="other@example.com",
            email="other@example.com",
            name="Other",
            password="StrongPass-2026!",
        )
        Contact.objects.create(owner=other, name="Hidden Contact")

        response = self.client.get("/api/contacts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_unauthenticated_contact_access_is_rejected(self):
        self.client.credentials()

        list_response = self.client.get("/api/contacts/")
        create_response = self.client.post(
            "/api/contacts/",
            {"name": "Unauthorized"},
            format="json",
        )

        self.assertEqual(list_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(create_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(Contact.objects.filter(name="Unauthorized").exists())

    def test_foreign_contact_detail_cannot_be_read_modified_or_deleted(self):
        other = get_user_model().objects.create_user(
            username="other-detail@example.com",
            email="other-detail@example.com",
            name="Other",
            password="StrongPass-2026!",
        )
        contact = Contact.objects.create(owner=other, name="Private Contact")
        url = f"/api/contacts/{contact.pk}/"

        get_response = self.client.get(url)
        patch_response = self.client.patch(url, {"name": "Stolen"}, format="json")
        delete_response = self.client.delete(url)

        self.assertEqual(get_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(patch_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(delete_response.status_code, status.HTTP_404_NOT_FOUND)
        contact.refresh_from_db()
        self.assertEqual(contact.name, "Private Contact")

    def test_contact_validation_rejects_blank_name_and_invalid_email(self):
        blank_name = self.client.post(
            "/api/contacts/",
            {"name": "   ", "email": "valid@example.com"},
            format="json",
        )
        invalid_email = self.client.post(
            "/api/contacts/",
            {"name": "Valid Name", "email": "not-an-email"},
            format="json",
        )

        self.assertEqual(blank_name.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid_email.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Contact.objects.filter(owner=self.user).count(), 0)


    def test_contact_owner_is_required_at_database_level(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Contact.objects.create(name="Ownerless")

    def test_search_is_scoped_to_current_user(self):
        Contact.objects.create(owner=self.user, name="Thomas Müller")
        Contact.objects.create(owner=self.user, name="Anna Becker")
        other = get_user_model().objects.create_user(
            username="search-other@example.com",
            email="search-other@example.com",
            name="Other",
            password="StrongPass-2026!",
        )
        Contact.objects.create(owner=other, name="Thomas Hidden")

        response = self.client.get("/api/contacts/?search=thomas")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["name"] for item in response.data], ["Thomas Müller"])
