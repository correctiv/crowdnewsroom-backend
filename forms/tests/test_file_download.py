from unittest.mock import patch

from django.test import TestCase, Client

from forms.admin_views import _get_file_data
from forms.models import User
from forms.tests.factories import FormInstanceFactory, FormResponseFactory


class FormReponseListViewTest(TestCase):
    def setUp(self):
        User.objects.create_superuser('admin@crowdnewsroom.org', 'password')
        self.client = Client()
        self.client.login(email='admin@crowdnewsroom.org', password='password')

    def test_get_file_data(self):
        file_base64 = "data:image/gif;name=spacer.gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAQAIBRAA7"
        file_name, file_type, file_content = _get_file_data(file_base64)
        self.assertEqual(file_name, "spacer.gif")
        self.assertEqual(file_type, "image/gif")
        self.assertTrue(file_content.startswith(b"GIF89"))

    @patch('forms.admin_views._get_file_data', return_value=("filename.png", "image/png", "c"))
    def test_file_download(self, mock_get_file_data):
        form_response = FormResponseFactory.create(json={"file_field": "data:image/png;base64,abc123"})
        form = form_response.form_instance.form

        response = self.client.get("/forms/admin/investigations/{}/forms/{}/responses/{}/files/file_field".format(form.investigation.slug, form.slug,form_response.id))
        self.assertEquals(response.status_code, 200)

        expected_filename = "crowdnewsroom_download_{}_{}.csv".format(form.investigation.slug, form.slug)
        expected_content_disposition = 'inline; filename="filename.png"'.format(expected_filename)
        self.assertEquals(response['Content-Disposition'], expected_content_disposition)

