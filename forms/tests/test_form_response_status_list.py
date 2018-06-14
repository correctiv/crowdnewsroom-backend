from django.db.models.functions import Coalesce
from django.test import TestCase, Client
from django.urls import reverse

from forms.models import FormResponse, User
from forms.tests.factories import FormResponseFactory, FormInstanceFactory


def make_url(form_response):
    form = form_response.form_instance.form
    params = {
        "form_slug": form.slug,
        "investigation_slug": form.investigation.slug,
        "response_id": form_response.id
    }

    return reverse("response_details_status", kwargs=params)


class FormReponseStatusListViewTest(TestCase):
    def setUp(self):
        self.form_instance = FormInstanceFactory.create()
        self.verified_response_1 = FormResponseFactory.create(
            status="V",
            form_instance=self.form_instance,
            json={"has_car": True,
                  "email": "edward@example.com"})
        self.submitted_response_1 = FormResponseFactory.create(
            status="S",
            form_instance=self.form_instance,
            json={"email": "hildegard@example.com"})
        self.submitted_response_2 = FormResponseFactory.create(
            status="S",
            form_instance=self.form_instance,
            json={"has_car": False,
                  "email": "gwendolyn@example.com"})

        User.objects.create_superuser('admin@crowdnewsroom.org', 'password')
        self.client = Client()
        self.client.login(email='admin@crowdnewsroom.org', password='password')

    def test_move_response_to_verified_appears_on_top(self):
        form = self.form_instance.form
        payload = {
            "status": "V",
        }
        self.client.post(make_url(self.submitted_response_1), data=payload)
        updated_response = FormResponse.objects \
                                       .get(id=self.submitted_response_1.id)

        verified_responses = FormResponse.objects \
            .filter(form_instance__form=form) \
            .filter(status="V") \
            .order_by(Coalesce('last_status_changed_date', 'submission_date')
                      .desc())

        self.assertEqual(updated_response, verified_responses.first())
