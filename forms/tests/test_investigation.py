from unittest.mock import patch

import pytz
from django.test import TestCase
from django.utils import timezone

from forms.tests.factories import FormResponseFactory, FormInstanceFactory


def make_date(day):
    return timezone.datetime(2018, 1, day, tzinfo=pytz.utc)


class FormReponseTest(TestCase):
    def setUp(self):
        form_instance = FormInstanceFactory.create()
        submission_data = [
            (make_date(1), "S"),
            (make_date(2), "V"),
            (make_date(2), "V"),
            (make_date(5), "I"),
        ]

        for (date, status) in submission_data:
            FormResponseFactory.create(submission_date=date,
                                       status=status,
                                       form_instance=form_instance)

        self.investigation = form_instance.form.investigation

    @patch('django.utils.timezone.now', return_value=timezone.datetime(2018, 1, 6, tzinfo=pytz.utc))
    def test_submission_stats(self, mock_now):
        stats = self.investigation.submission_stats()
        expected = {
            "total": 4,
            "yesterday": 1,
            "to_verify": 1,
        }
        self.assertDictEqual(stats, expected)
