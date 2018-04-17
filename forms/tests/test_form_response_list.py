from django.test import TestCase, Client

from forms.models import User
from forms.tests.factories import FormResponseFactory, FormInstanceFactory


class FormReponseListViewTest(TestCase):
    def setUp(self):
        self.form_instance = FormInstanceFactory.create()
        for status in ["V", "S", "S"]:
            FormResponseFactory.create(status=status, form_instance=self.form_instance)

        User.objects.create_superuser('admin@crowdnewsroom.org', 'password')

    def test_inbox(self):
        client = Client()
        client.login(email='admin@crowdnewsroom.org', password='password')
        form = self.form_instance.form

        response = client.get("/forms/admin/investigations/{}/forms/{}/responses/inbox".format(form.investigation.slug, form.slug))
        self.assertEquals(len(response.context_data["formresponse_list"]), 2)

        response = client.get("/forms/admin/investigations/{}/forms/{}/responses/trash".format(form.investigation.slug, form.slug))
        self.assertEquals(len(response.context_data["formresponse_list"]), 0)

        response = client.get("/forms/admin/investigations/{}/forms/{}/responses/verified".format(form.investigation.slug, form.slug))
        self.assertEquals(len(response.context_data["formresponse_list"]), 1)

