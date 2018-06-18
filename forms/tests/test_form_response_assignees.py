import json
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from forms.models import User, FormResponse, UserGroup
from forms.tests.factories import FormResponseFactory, FormInstanceFactory, UserFactory


def make_url(form_response):
    params = {
        "response_id": form_response.id
    }

    return reverse("form_response_edit", kwargs=params)


@override_settings(DEBUG=True)
class FormReponseAssigneesTest(APITestCase):
    def setUp(self):
        self.admin_user = UserFactory.create()
        self.response = FormResponseFactory.create()

        admin_user_group = UserGroup.objects.filter(investigation=self.response.form_instance.form.investigation,
                                                    role="A").first()
        admin_user_group.group.user_set.add(self.admin_user)

        self.client.force_login(self.admin_user)

    def test_assign_user_works(self):
        payload = {
            "assignees": [self.admin_user.id],
        }
        response = self.client.patch(make_url(self.response), data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(self.response.assignees.all(), [self.admin_user.__repr__()])

    def test_unassign_user_works(self):
        self.response.assignees.add(self.admin_user)
        self.assertQuerysetEqual(self.response.assignees.all(), [self.admin_user.__repr__()])
        payload = {
            "assignees": [],
        }
        response = self.client.patch(make_url(self.response),
                                     data=json.dumps(payload),
                                     content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(self.response.assignees.all(), [])

    def test_assign_user_from_other_investigation_fails(self):
        user_without_groups = UserFactory.create()
        payload = {
            "assignees": [user_without_groups.id],
        }
        response = self.client.patch(make_url(self.response), data=payload)
        expected_message = 'Invalid pk "{}" - object does not exist.'.format(user_without_groups.id)
        self.assertEqual(json.loads(response.content.decode("utf-8")), {"assignees":[expected_message]})
        self.assertEqual(response.status_code, 400)
        self.assertQuerysetEqual(self.response.assignees.all(), [])


