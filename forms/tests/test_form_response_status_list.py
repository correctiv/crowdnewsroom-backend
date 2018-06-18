from django.db.models.functions import Coalesce
from django.urls import reverse
from rest_framework.test import APITestCase
from unittest.mock import patch

from forms.models import FormResponse, User
from forms.tests.factories import FormResponseFactory, FormInstanceFactory


def make_url(form_response):
    params = {
        "response_id": form_response.id
    }
    return reverse("form_response_edit", kwargs=params)


def make_url_for_response_list(form, bucket):
    params = {
        "investigation_slug": form.investigation.slug,
        "form_slug": form.slug,
        "bucket": bucket
    }
    return reverse("form_responses", kwargs=params)


class FormReponseStatusListViewTest(APITestCase):
    def setUp(self):
        self.form_instance = FormInstanceFactory.create()
        self.verified_response_1 = FormResponseFactory.create(
            status="V",
            form_instance=self.form_instance)
        self.submitted_response_1 = FormResponseFactory.create(
            status="S",
            form_instance=self.form_instance)
        self.submitted_response_2 = FormResponseFactory.create(
            status="S",
            form_instance=self.form_instance)

        User.objects.create_superuser('admin@crowdnewsroom.org', 'password')
        self.client.login(email='admin@crowdnewsroom.org', password='password')

    @patch('webpack_loader.loader.WebpackLoader.get_bundle')
    def test_move_response_to_verified_appears_on_top(self, *args):
        payload = {
            "status": "V",
        }
        self.client.patch(make_url(self.submitted_response_1), data=payload)
        updated_response = FormResponse.objects \
                                       .get(id=self.submitted_response_1.id)

        response_list = self.client.get(make_url_for_response_list(updated_response.form_instance.form, "verified"))
        expected_queryset = [repr(updated_response), repr(self.verified_response_1)]
        self.assertQuerysetEqual(response_list.context["formresponse_list"], expected_queryset)

