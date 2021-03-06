from django.urls import reverse
from rest_framework.test import APITestCase, APITransactionTestCase
from unittest.mock import patch

from forms.models import Invitation, User, INVESTIGATION_ROLES, Form
from forms.tests.factories import InvestigationFactory, UserFactory, FormFactory


class FormAPITestCase(APITestCase):
    def test_add_form_unauthorized(self):
        investigation = InvestigationFactory.create()

        response = self.client.post(reverse("interviewers", kwargs={"investigation_slug": investigation.slug}),
                                    data={"name": "test", "slug": "test"})
        # This should be 401...
        self.assertEqual(response.status_code, 403)

    def test_add_form_non_admin(self):
        editor = UserFactory.create()
        investigation = InvestigationFactory.create()
        investigation.add_user(editor, INVESTIGATION_ROLES.EDITOR)

        self.client.force_login(editor)

        response = self.client.post(reverse("interviewers", kwargs={"investigation_slug": investigation.slug}),
                                    data={"name": "test", "slug": "test"})
        self.assertEqual(response.status_code, 403)

    def test_admin_can_add_form(self):
        admin = UserFactory.create()
        investigation = InvestigationFactory.create()
        investigation.add_user(admin, INVESTIGATION_ROLES.ADMIN)

        self.client.force_login(admin)

        self.assertEqual(Form.objects.count(), 0)

        response = self.client.post(reverse("interviewers", kwargs={"investigation_slug": investigation.slug}),
                                    data={"name": "test", "slug": "test"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Form.objects.count(), 1)
        # make sure the right investigation was assigned
        self.assertEqual(response.data["investigation"], investigation.id)

    def test_wrong_admin_cannot_add_form(self):
        admin = UserFactory.create()
        investigation = InvestigationFactory.create()
        investigation.add_user(admin, INVESTIGATION_ROLES.ADMIN)
        other_investigation = InvestigationFactory()

        self.client.force_login(admin)

        self.assertEqual(Form.objects.count(), 0)

        response = self.client.post(reverse("interviewers", kwargs={"investigation_slug": other_investigation.slug}),
                                    data={"name": "test", "slug": "test"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Form.objects.count(), 0)


    def test_get_requires_login(self):
        form = FormFactory.create()

        response = self.client.get(reverse("form_details", kwargs={"form_slug": form.slug}))
        self.assertEqual(response.status_code, 403)

    def test_can_get_form(self):
        admin = UserFactory.create()
        investigation = InvestigationFactory.create()
        investigation.add_user(admin, INVESTIGATION_ROLES.ADMIN)
        form = FormFactory.create(investigation=investigation)

        self.client.force_login(admin)

        response = self.client.get(reverse("form_details", kwargs={"form_slug": form.slug}))
        self.assertEqual(response.status_code, 200)

    def test_get_wrong_investigation(self):
        admin = UserFactory.create()
        investigation = InvestigationFactory.create()
        investigation.add_user(admin, INVESTIGATION_ROLES.ADMIN)
        form = FormFactory.create()  # this will be part of another investigation

        self.client.force_login(admin)

        response = self.client.get(reverse("form_details", kwargs={"form_slug": form.slug}))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_edit(self):
        admin = UserFactory.create()
        investigation = InvestigationFactory.create()
        investigation.add_user(admin, INVESTIGATION_ROLES.ADMIN)
        form = FormFactory.create(investigation=investigation)

        self.client.force_login(admin)

        response = self.client.patch(reverse("form_details", kwargs={"form_slug": form.slug}),
                                     data={"name": "My new Name"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "My new Name")

    def test_slug_cannot_contain_special_characters(self):
        user = UserFactory.create()
        investigation = InvestigationFactory.create()
        investigation.add_user(user, INVESTIGATION_ROLES.ADMIN)

        self.client.force_login(user)

        response = self.client.post(reverse("interviewers", kwargs={"investigation_slug": investigation.slug}),
                                    data={"name": "test", "slug": "%$test"})
        self.assertEqual(response.status_code, 400)

    def test_slug_cannot_begin_with_number(self):
        user = UserFactory.create()
        investigation = InvestigationFactory.create()
        investigation.add_user(user, INVESTIGATION_ROLES.ADMIN)

        self.client.force_login(user)

        response = self.client.post(reverse("interviewers", kwargs={"investigation_slug": investigation.slug}),
                                    data={"name": "test", "slug": "123test"})
        self.assertEqual(response.status_code, 400)
