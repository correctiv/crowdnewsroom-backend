from django.test import TestCase, Client
from django.urls import reverse

from forms.models import FormResponse, UserGroup
from forms.tests.factories import FormResponseFactory, UserFactory


def make_url(form_response):
    form = form_response.form_instance.form
    params = {
        "form_slug": form.slug,
        "investigation_slug": form.investigation.slug,
        "response_id": form_response.id
    }

    return reverse("response_details_status", kwargs=params)


def make_form_detail_url(form_response):
    form = form_response.form_instance.form
    params = {
        "form_slug": form.slug,
        "investigation_slug": form.investigation.slug,
        "response_id": form_response.id
    }

    return reverse("response_details", kwargs=params)


class FormReponseStatusTest(TestCase):
    def setUp(self):
        self.admin_user = UserFactory.create()
        self.response = FormResponseFactory.create()

        admin_user_group = UserGroup.objects.filter(investigation=self.response.form_instance.form.investigation,
                                                    role="A").first()
        admin_user_group.group.user_set.add(self.admin_user)

        self.client = Client()
        self.client.force_login(self.admin_user)

    def test_update_status_works(self):
        payload = {
            "status": "V",
        }
        self.client.post(make_url(self.response), data=payload)
        updated_response = FormResponse.objects.get(id=self.response.id)
        self.assertEqual(updated_response.status, "V")

    def test_redirect(self):
        payload = {
            "status": "V",
        }
        response = self.client.post(make_url(self.response), data=payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, make_form_detail_url(self.response))
