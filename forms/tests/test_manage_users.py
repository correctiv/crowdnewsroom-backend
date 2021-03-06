from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from forms.models import User, UserGroup, INVESTIGATION_ROLES
from forms.tests.factories import UserFactory, InvestigationFactory


@override_settings(DEBUG=True)
class InvestigationUserTest(APITestCase):
    def setUp(self):
        self.admin_user = UserFactory.create()  # type: User
        self.investigation = InvestigationFactory.create()
        self.investigation.add_user(self.admin_user, INVESTIGATION_ROLES.OWNER)

        self.client.force_login(self.admin_user)

    def test_get_users_one_user(self):
        response = self.client.get(
            reverse("investigation_users", kwargs={"investigation_slug": self.investigation.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"users": [
            {"id": self.admin_user.id,
             "first_name": self.admin_user.first_name,
             "last_name": self.admin_user.last_name,
             "email": self.admin_user.email,
             "role": INVESTIGATION_ROLES.OWNER,
             "is_requester": True}
        ]})

    def test_get_users_multiple_users(self):
        investigation_editor = UserFactory.create()
        other_investigation_editor = UserFactory.create()

        self.investigation.add_user(investigation_editor, "E")

        response = self.client.get(
            reverse("investigation_users", kwargs={"investigation_slug": self.investigation.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"users": [
            {"id": self.admin_user.id,
             "first_name": self.admin_user.first_name,
             "last_name": self.admin_user.last_name,
             "email": self.admin_user.email,
             "role": INVESTIGATION_ROLES.OWNER,
             "is_requester": True},
            {"id": investigation_editor.id,
             "first_name": investigation_editor.first_name,
             "last_name": investigation_editor.last_name,
             "email": investigation_editor.email,
             "role": "E",
             "is_requester": False}
        ]})
