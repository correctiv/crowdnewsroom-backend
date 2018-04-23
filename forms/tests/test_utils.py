from io import StringIO
from unittest.mock import Mock, MagicMock

import pytz
from django.test import TestCase
from django.utils.datetime_safe import datetime
from django.utils.text import slugify
from webob import Request

from forms.models import Investigation, Form, FormInstance, FormResponse
from forms.tests.factories import FormResponseFactory
from forms.utils import _get_file_keys, create_form_csv


class Utils(TestCase):
    def setUp(self):
        investigation_name = "First Investigation"
        self.investigation = Investigation.objects.create(name=investigation_name, slug=slugify(investigation_name))

        form_name = "First Form"
        self.form = Form.objects.create(name=form_name,
                                        slug=slugify(form_name),
                                        investigation=self.investigation)

    def test_get_file_keys_finds_file(self):
        form_instance = FormInstance.objects.create(form=self.form,
                                                    form_json=[{
                                                        "schema": {
                                                            "slug": "first",
                                                            "properties": {
                                                                "string": {"type": "string"},
                                                                "file": {"type": "string",
                                                                         "format": "data-url"}
                                                            }
                                                        }
                                                    }])

        expected = {"file"}
        file_keys = _get_file_keys(form_instance)
        self.assertEqual(file_keys, expected)

    def test_get_file_keys_finds_file_array(self):
        form_instance = FormInstance.objects.create(form=self.form,
                                                    form_json=[{
                                                        "schema": {
                                                            "slug": "first",
                                                            "properties": {
                                                                "files": {
                                                                    "type": "array",
                                                                    "items": {
                                                                        "type": "string",
                                                                        "format": "data-url"
                                                                    }
                                                                },
                                                            }
                                                        }
                                                    }])

        expected = {"files"}
        file_keys = _get_file_keys(form_instance)
        self.assertEqual(file_keys, expected)

    def test_get_file_keys_finds_signature(self):
        form_instance = FormInstance.objects.create(form=self.form,
                                                    form_json=[{
                                                        "schema": {
                                                            "slug": "first",
                                                            "properties": {
                                                                "signature": {"type": "string"},
                                                            }
                                                        }
                                                    }],
                                                    ui_schema_json={
                                                        "first": {
                                                            "signature": {
                                                                "ui:widget": "signatureWidget"
                                                            }
                                                        }
                                                    })

        expected = {"signature"}
        file_keys = _get_file_keys(form_instance)
        self.assertEqual(file_keys, expected)

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

        FormResponseFactory.create(form_instance=form_instance,
                                   email="peter@example.com",
                                   submission_date=datetime(2018, 1, 1, tzinfo=pytz.utc),
                                   json={
                                       "name": "Peter"
                                   })
        FormResponseFactory.create(form_instance=form_instance,
                                   email="katharina@example.com",
                                   submission_date=datetime(2018, 1, 2, tzinfo=pytz.utc),
                                   json={
                                       "name": "Katharina"
                                   })
        create_form_csv(self.form, self.investigation.slug, build_absolute_uri, buffer)
        lines = buffer.getvalue().split('\n')

        header = lines[0].strip()
        expected_header = "meta_email,meta_status,meta_submission_date,meta_url,meta_version,name"
        self.assertEquals(header, expected_header)

        first = lines[1].strip()
        expected_first = "peter@example.com,Submitted,2018-01-01 00:00:00+00:00,http://example.com,0,Peter"
        self.assertEquals(first, expected_first)

        second = lines[2].strip()
        expected_second = "katharina@example.com,Submitted,2018-01-02 00:00:00+00:00,http://example.com,0,Katharina"
        self.assertEquals(second, expected_second)
