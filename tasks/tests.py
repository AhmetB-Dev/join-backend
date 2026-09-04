from datetime import date

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from contacts.models import Contact
from .models import Task


class TaskApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester@example.com",
            email="tester@example.com",
            name="Tester",
            password="StrongPass-2026!",
        )
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    @staticmethod
    def valid_payload(**overrides):
        payload = {
            "title": "Board erstellen",
            "description": "No description provided",
            "dueDate": "11/10/2026",
            "category": "Technical task",
            "column": "toDoColumn",
            "priority": "../img/priority-img/urgent.png",
            "progress": 0,
            "users": [{"name": "Thomas Müller"}],
            "subtasks": [{"text": "API testen", "completed": False}],
        }
        payload.update(overrides)
        return payload

    def test_create_and_patch_join_compatible_task(self):
        response = self.client.post(
            "/api/tasks/",
            self.valid_payload(users=[{"name": "Thomas Müller"}, {"name": "Frederik Schneider"}]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["priority"], "../img/priority-img/urgent.png")
        self.assertEqual(response.data["dueDate"], "11/10/2026")
        self.assertEqual(len(response.data["users"]), 2)
        self.assertEqual(len(response.data["subtasks"]), 1)
        self.assertEqual(Task.objects.get(pk=response.data["id"]).owner, self.user)

        task_id = response.data["id"]
        patched = self.client.patch(f"/api/tasks/{task_id}/", {"column": "done"}, format="json")
        self.assertEqual(patched.status_code, status.HTTP_200_OK)
        self.assertEqual(patched.data["column"], "done")
        self.assertEqual(len(patched.data["users"]), 2)
        self.assertEqual(len(patched.data["subtasks"]), 1)

    def test_tasks_from_other_users_are_hidden(self):
        other = get_user_model().objects.create_user(
            username="other@example.com",
            email="other@example.com",
            name="Other",
            password="StrongPass-2026!",
        )
        Task.objects.create(
            owner=other,
            title="Hidden Task",
            due_date=date(2026, 10, 11),
        )

        response = self.client.get("/api/tasks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_unauthenticated_task_access_is_rejected(self):
        self.client.credentials()

        list_response = self.client.get("/api/tasks/")
        create_response = self.client.post(
            "/api/tasks/",
            self.valid_payload(),
            format="json",
        )

        self.assertEqual(list_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(create_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Task.objects.count(), 0)

    def test_foreign_task_detail_cannot_be_read_modified_or_deleted(self):
        other = get_user_model().objects.create_user(
            username="other-detail@example.com",
            email="other-detail@example.com",
            name="Other",
            password="StrongPass-2026!",
        )
        task = Task.objects.create(
            owner=other,
            title="Private Task",
            due_date=date(2026, 10, 11),
        )
        url = f"/api/tasks/{task.pk}/"

        get_response = self.client.get(url)
        patch_response = self.client.patch(url, {"title": "Stolen"}, format="json")
        delete_response = self.client.delete(url)

        self.assertEqual(get_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(patch_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(delete_response.status_code, status.HTTP_404_NOT_FOUND)
        task.refresh_from_db()
        self.assertEqual(task.title, "Private Task")

    def test_invalid_task_values_are_rejected(self):
        invalid_cases = (
            {"title": "   "},
            {"column": "unknown-column"},
            {"priority": "not-urgent"},
            {"dueDate": "31/31/2026"},
        )

        for override in invalid_cases:
            with self.subTest(override=override):
                response = self.client.post(
                    "/api/tasks/",
                    self.valid_payload(**override),
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(Task.objects.count(), 0)

    def test_assignment_never_reuses_another_users_contact(self):
        other = get_user_model().objects.create_user(
            username="contact-owner@example.com",
            email="contact-owner@example.com",
            name="Other",
            password="StrongPass-2026!",
        )
        foreign_contact = Contact.objects.create(owner=other, name="Thomas Müller")

        response = self.client.post(
            "/api/tasks/",
            self.valid_payload(users=[{"name": "Thomas Müller"}]),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        task = Task.objects.get(pk=response.data["id"])
        assigned_contact = task.assigned_contacts.get()
        self.assertEqual(assigned_contact.owner, self.user)
        self.assertNotEqual(assigned_contact.pk, foreign_contact.pk)


    def test_progress_is_calculated_from_subtasks_and_client_value_is_ignored(self):
        response = self.client.post(
            "/api/tasks/",
            self.valid_payload(
                progress=99,
                subtasks=[
                    {"text": "One", "completed": True},
                    {"text": "Two", "completed": False},
                    {"text": "Three", "completed": True},
                ],
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["progress"], 67)
        task = Task.objects.get(pk=response.data["id"])
        self.assertEqual(task.progress, 67)

        manipulated = self.client.patch(
            f"/api/tasks/{task.pk}/",
            {"progress": 5},
            format="json",
        )
        self.assertEqual(manipulated.status_code, status.HTTP_200_OK)
        self.assertEqual(manipulated.data["progress"], 67)

    def test_progress_recalculates_when_subtasks_change(self):
        created = self.client.post(
            "/api/tasks/",
            self.valid_payload(
                subtasks=[
                    {"text": "One", "completed": False},
                    {"text": "Two", "completed": False},
                ]
            ),
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        self.assertEqual(created.data["progress"], 0)

        patched = self.client.patch(
            f"/api/tasks/{created.data['id']}/",
            {
                "subtasks": [
                    {"text": "One", "completed": True},
                    {"text": "Two", "completed": False},
                ]
            },
            format="json",
        )

        self.assertEqual(patched.status_code, status.HTTP_200_OK, patched.data)
        self.assertEqual(patched.data["progress"], 50)

    def test_blank_subtask_is_rejected_instead_of_silently_dropped(self):
        response = self.client.post(
            "/api/tasks/",
            self.valid_payload(subtasks=[{"text": "   ", "completed": False}]),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Task.objects.count(), 0)

    def test_task_owner_is_required_at_database_level(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Task.objects.create(
                    title="Ownerless",
                    due_date=date(2026, 10, 11),
                )

    def test_column_filter_only_returns_owned_matching_tasks(self):
        Task.objects.create(
            owner=self.user,
            title="Own To Do",
            due_date=date(2026, 10, 11),
            column=Task.Column.TODO,
        )
        Task.objects.create(
            owner=self.user,
            title="Own Done",
            due_date=date(2026, 10, 12),
            column=Task.Column.DONE,
        )
        other = get_user_model().objects.create_user(
            username="filter-other@example.com",
            email="filter-other@example.com",
            name="Other",
            password="StrongPass-2026!",
        )
        Task.objects.create(
            owner=other,
            title="Hidden To Do",
            due_date=date(2026, 10, 13),
            column=Task.Column.TODO,
        )

        response = self.client.get("/api/tasks/?column=toDoColumn")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["title"] for item in response.data], ["Own To Do"])
