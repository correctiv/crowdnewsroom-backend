import json
from django.urls import reverse
from rest_framework.test import APITestCase

from forms.models import FormResponse, UserGroup
from forms.tests.factories import FormResponseFactory, UserFactory


def make_url(form_response):
    params = {
        "response_id": form_response.id
    }

    return reverse("form_response_edit", kwargs=params)


class FormReponseStatusTest(APITestCase):
    def setUp(self):
        self.admin_user = UserFactory.create()
        self.response = FormResponseFactory.create()

        admin_user_group = UserGroup.objects.filter(investigation=self.response.form_instance.form.investigation,
                                                    role="A").first()
        admin_user_group.group.user_set.add(self.admin_user)

        self.client.force_login(self.admin_user)

    def test_update_status_works(self):
        payload = {
            "status": "V",
        }
        response = self.client.patch(make_url(self.response), data=payload)
        self.assertEqual(response.status_code, 200)
        updated_response = FormResponse.objects.get(id=self.response.id)
        self.assertEqual(updated_response.status, "V")

    def test_update_status_fails_for_invalid_value(self):
        payload = {
            "status": "X",
        }
        response = self.client.patch(make_url(self.response),
                                     data=json.dumps(payload),
                                     content_type="application/json")
        self.assertEqual(response.status_code, 400)
        updated_response = FormResponse.objects.get(id=self.response.id)
        self.assertEqual(updated_response.status, "S")
