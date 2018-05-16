from django.test import TestCase, Client
from django.urls import reverse

from forms.models import User, FormResponse, UserGroup
from forms.tests.factories import FormResponseFactory, FormInstanceFactory, UserFactory


def make_url(form_response):
    form = form_response.form_instance.form
    params = {
        "form_slug": form.slug,
        "investigation_slug": form.investigation.slug,
        "response_id": form_response.id
    }

    return reverse("response_details_assignees", kwargs=params)


class FormReponseAssigneesTest(TestCase):
    def setUp(self):
        self.admin_user = UserFactory.create()
        self.response = FormResponseFactory.create()

        admin_user_group = UserGroup.objects.filter(investigation=self.response.form_instance.form.investigation,
                                                    role="A").first()
        admin_user_group.group.user_set.add(self.admin_user)

        self.client = Client()
        self.client.force_login(self.admin_user)

    def test_assign_user_works(self):
        payload = {
            "assignees": [self.admin_user.id],
        }
        response = self.client.post(make_url(self.response), data=payload)
        self.assertEqual(response.status_code, 302)
        self.assertQuerysetEqual(self.response.assignees.all(), [self.admin_user.__repr__()])

    def test_unassign_user_works(self):
        self.response.assignees.add(self.admin_user)
        self.assertQuerysetEqual(self.response.assignees.all(), [self.admin_user.__repr__()])
        payload = {
            "assignees": [],
        }
        response = self.client.post(make_url(self.response), data=payload)
        self.assertEqual(response.status_code, 302)
        self.assertQuerysetEqual(self.response.assignees.all(), [])

    def test_assign_user_from_other_investigation_fails(self):
        # This user is not part of any groups that are part of the investigation
        # so she cannot be added to the investigation. Since we are
        # using a ModelForm that has a queryset Django actually makes sure that
        # we can only add objects that are part of the queryset. Pretty nice!
        user_without_groups = UserFactory.create()
        payload = {
            "assignees": [user_without_groups.id],
        }
        response = self.client.post(make_url(self.response), data=payload)
        self.assertEqual(response.status_code, 403)
        self.assertQuerysetEqual(self.response.assignees.all(), [])


