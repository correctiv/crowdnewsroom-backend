import datetime
from collections import OrderedDict

import pytz
from django.test import TestCase
from django.utils import timezone

from forms.tests.factories import FormResponseFactory, FormInstanceFactory, FormFactory


class FormTest(TestCase):
    def setUp(self):
        form_instance = FormInstanceFactory.create()
        response_data = [
            (timezone.datetime(2018, 1, 2, tzinfo=pytz.utc), "S"),
            (timezone.datetime(2018, 1, 5, tzinfo=pytz.utc), "S"),
            (timezone.datetime(2018, 1, 1, tzinfo=pytz.utc), "I"),
            (timezone.datetime(2018, 1, 1, tzinfo=pytz.utc), "V"),
            (timezone.datetime(2018, 1, 1, tzinfo=pytz.utc), "V")
        ]

        for date, status in response_data:
            FormResponseFactory.create(submission_date=date,
                                       form_instance=form_instance,
                                       status=status)

        self.form = form_instance.form

    def test_submissions_by_date(self):
        self.assertQuerysetEqual(self.form.submissions_by_date(),
                                 [OrderedDict({'date': datetime.date(2018, 1, 1), 'c': 3}),
                                  OrderedDict({'date': datetime.date(2018, 1, 2), 'c': 1}),
                                  OrderedDict({'date': datetime.date(2018, 1, 5), 'c': 1})],
                                 transform=lambda entry: OrderedDict(entry)
                                 )

    def test_submissions_by_date_no_submissions(self):
        form = FormFactory.create()
        self.assertQuerysetEqual(form.submissions_by_date(), [])

    def test_count_by_bucket(self):
        self.assertDictEqual(self.form.count_by_bucket(), {'I': 1, 'S': 2, 'V': 2})

