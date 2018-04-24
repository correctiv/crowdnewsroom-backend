from io import StringIO

import pytz
from django.test import TestCase
from django.utils.datetime_safe import datetime
from django.utils.text import slugify

from forms.models import Investigation, Form, FormInstance
from forms.tests.factories import FormResponseFactory
from forms.utils import create_form_csv


class Utils(TestCase):
    def setUp(self):
        investigation_name = "First Investigation"
        self.investigation = Investigation.objects.create(name=investigation_name, slug=slugify(investigation_name))

        form_name = "First Form"
        self.form = Form.objects.create(name=form_name,
                                        slug=slugify(form_name),
                                        investigation=self.investigation)

    def test_create_form_csv(self):
        buffer = StringIO()
        build_absolute_uri = lambda x: "http://example.com"

        form_instance = FormInstance.objects.create(form=self.form,
                                                    form_json=[{
                                                        "schema": {
                                                            "slug": "first",
                                                            "properties": {
                                                                "name": {"type": "string"},
                                                            }
                                                        }
                                                    }])

        response_1 = FormResponseFactory.create(form_instance=form_instance,
                                   email="peter@example.com",
                                   submission_date=datetime(2018, 1, 1, tzinfo=pytz.utc),
                                   json={
                                       "name": "Peter"
                                   })
        response_2 =FormResponseFactory.create(form_instance=form_instance,
                                   email="katharina@example.com",
                                   submission_date=datetime(2018, 1, 2, tzinfo=pytz.utc),
                                   json={
                                       "name": "Katharina"
                                   })
        create_form_csv(self.form, self.investigation.slug, build_absolute_uri, buffer)
        lines = buffer.getvalue().split('\n')

        header = lines[0].strip()
        expected_header = "meta_email,meta_id,meta_status,meta_submission_date,meta_url,meta_version,name"
        self.assertEquals(header, expected_header)

        first = lines[1].strip()
        expected_first = "peter@example.com,{},Submitted,2018-01-01 00:00:00+00:00,http://example.com,0,Peter".format(response_1.id)
        self.assertEquals(first, expected_first)

        second = lines[2].strip()
        expected_second = "katharina@example.com,{},Submitted,2018-01-02 00:00:00+00:00,http://example.com,0,Katharina".format(response_2.id)
        self.assertEquals(second, expected_second)

    def test_create_form_csv_file(self):
        buffer = StringIO()
        build_absolute_uri = lambda x: "https://example.com{}".format(x)

        form_instance = FormInstance.objects.create(form=self.form,
                                                    form_json=[{
                                                        "schema": {
                                                            "slug": "first",
                                                            "properties": {
                                                                "name": {"type": "string"},
                                                                "picture": {"type": "string",
                                                                            "format": "data-url"},
                                                            }
                                                        }
                                                    }])

        response = FormResponseFactory.create(form_instance=form_instance,
                                              email="katharina@example.com",
                                              submission_date=datetime(2018, 1, 2, tzinfo=pytz.utc),
                                              json={
                                                  "name": "Katharina",
                                                  "picture": "data-url...."
                                              })
        create_form_csv(form_instance.form, form_instance.form.investigation.slug, build_absolute_uri, buffer)
        lines = buffer.getvalue().split('\n')

        header = lines[0].strip()
        expected_header = "meta_email,meta_id,meta_status,meta_submission_date,meta_url,meta_version,name,picture"
        self.assertEquals(header, expected_header)

        first = lines[1].strip()
        expected_first = ",".join(["katharina@example.com",
                                   str(response.id),
                                   "Submitted",
                                   "2018-01-02 00:00:00+00:00",
                                   "https://example.com/forms/admin/investigations/first-investigation/forms/first-form/responses/{}".format(
                                       response.id),
                                   "0",
                                   "Katharina",
                                   "https://example.com/forms/admin/investigations/first-investigation/forms/first-form/responses/{}/files/picture".format(
                                       response.id)])
        self.assertEquals(first, expected_first)

    def test_create_form_csv_file_filter(self):
        buffer = StringIO()
        build_absolute_uri = lambda x: "https://example.com{}".format(x)

        form_instance = FormInstance.objects.create(form=self.form,
                                                    form_json=[{
                                                        "schema": {
                                                            "slug": "first",
                                                            "properties": {
                                                                "name": {"type": "string"},
                                                                "picture": {"type": "string",
                                                                            "format": "data-url"},
                                                            }
                                                        }
                                                    }])

        FormResponseFactory.create(form_instance=form_instance,
                                   json={
                                       "name": "Katharina",
                                       "picture": "data-url...."
                                   })
        FormResponseFactory.create(form_instance=form_instance,
                                   status="I",
                                   json={
                                       "name": "Peter",
                                   })
        create_form_csv(form_instance.form,
                        form_instance.form.investigation.slug,
                        build_absolute_uri,
                        buffer,
                        {"status": "I"})
        lines = [line for line in buffer.getvalue().split('\r\n') if line != ""]

        self.assertEqual(len(lines), 2)

    def test_create_form_csv_file_filter_json(self):
        buffer = StringIO()
        build_absolute_uri = lambda x: "https://example.com{}".format(x)

        form_instance = FormInstance.objects.create(form=self.form,
                                                    form_json=[{
                                                        "schema": {
                                                            "slug": "first",
                                                            "properties": {
                                                                "name": {"type": "string"},
                                                                "picture": {"type": "string",
                                                                            "format": "data-url"},
                                                            }
                                                        }
                                                    }])

        FormResponseFactory.create(form_instance=form_instance,
                                   json={
                                       "name": "Katharina",
                                       "picture": "data-url...."
                                   })
        FormResponseFactory.create(form_instance=form_instance,
                                   status="I",
                                   json={
                                       "name": "Peter",
                                   })
        create_form_csv(form_instance.form,
                        form_instance.form.investigation.slug,
                        build_absolute_uri,
                        buffer,
                        {"json__picture__isnull": False})
        lines = [line for line in buffer.getvalue().split('\r\n') if line != ""]

        self.assertEqual(len(lines), 2)

