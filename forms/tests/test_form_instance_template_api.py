from django.urls import reverse
from rest_framework.test import APITestCase

from forms.models import FormInstanceTemplate
from forms.tests.factories import UserFactory, FormInstanceTemplateFactory


class InvestigationAPITest(APITestCase):
    def setUp(self):
        self.user = UserFactory.create()

    def test_list_templates_requires_auth(self):
        response = self.client.get(reverse("template_list"))
        # should really be a 401...
        self.assertEqual(response.status_code, 403)

    def test_list_templates_works(self):
        template = FormInstanceTemplateFactory.create()
        self.client.force_login(self.user)

        response = self.client.get(reverse("template_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [{"id": template.id,
                                          "name": template.name,
                                          "description": template.description}])

    def test_template_details_requires_auth(self):
        template = FormInstanceTemplateFactory.create()

        response = self.client.get(reverse("template", kwargs={"pk": template.id}))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data, {'detail': 'Authentication credentials were not provided.'})

    def test_template_details_works(self):
        template = FormInstanceTemplateFactory.create(form_json=["test"])  # type: FormInstanceTemplate
        self.client.force_login(self.user)

        response = self.client.get(reverse("template", kwargs={"pk": template.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"id": template.id,
                                         "name": template.name,
                                         "description": template.description,
                                         "form_json": ["test"],
                                         "ui_schema_json": {},
                                         "priority_fields": [],
                                         "email_template": template.email_template,
                                         "email_template_html": template.email_template_html,
                                         "redirect_url_template": template.redirect_url_template})
