from django.test import TestCase, Client
from django.urls import reverse

from forms.models import User, FormResponse, UserGroup
from forms.tests.factories import FormResponseFactory, FormInstanceFactory, UserFactory, TagFactory


class FormReponseTest(TestCase):
    def setUp(self):
        self.response = FormResponseFactory.create()

        form_instance = self.response.form_instance
        form_instance.form_json = [{"schema": {
            "name": "Step 1",
            "slug": "step-1",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "format": "data-url"
                    }
                }
            }
        }
        }]
        form_instance.save()

    def test_multiple_files(self):
        self.response.json = {"files": ["data-url:base64...", "data-url:base64..."]}
        self.response.save()
        form = self.response.form_instance.form
        base_url = '/forms/admin/investigations/{}/forms/{}'.format(form.investigation.slug, form.slug)
        url_template = '{}/responses/{{}}/files/files/{{}}'.format(base_url)
        expected = [
            {'json_name': 'files-0',
             'title': 'files 0',
             'type': 'link',
             'value': url_template.format(self.response.id, 0)},
            {'json_name': 'files-1',
             'title': 'files 1',
             'type': 'link',
             'value': url_template.format(self.response.id, 1)}
        ]
        self.assertListEqual(list(self.response.rendered_fields()), expected)

    def test_multiple_files_without_files(self):
        self.response.json = {}
        self.response.save()

        expected = []
        self.assertListEqual(list(self.response.rendered_fields()), expected)


def make_url(form):
    params = {
        "form_slug": form.slug,
        "investigation_slug": form.investigation.slug
    }

    return reverse("form_responses_edit", kwargs=params)


class FormReponseBatchEditTest(TestCase):
    def setUp(self):
        form_instances = [FormInstanceFactory.create() for _ in range(2)]
        investigations = [instance.form.investigation for instance in form_instances]
        responses = [[], []]
        for index, instance in enumerate(form_instances):
            for _ in range(5):
                response = FormResponseFactory.create(form_instance=instance)
                responses[index].append(response)

        user = UserFactory.create()
        admin_user_group = UserGroup.objects.filter(investigation=investigations[0],
                                                    role="A").first()
        admin_user_group.group.user_set.add(user)

        self.responses = responses
        self.admin_user = user

        self.client = Client()
        self.client.force_login(self.admin_user)

    def test_assign_tags_multiple(self):
        TagFactory.create(name='Pasta', slug='pasta')
        responses = self.responses[0]
        form = responses[0].form_instance.form
        payload = {
            "selected_responses": [responses[3].id, responses[4].id],
            "tag": "pasta"
        }
        
        self.client.post(make_url(form), data=payload)

        updated_responses = FormResponse.objects.filter(form_instance__form=form).all()
        tags = [response.tags.all() for response in updated_responses]

        self.assertQuerysetEqual(tags[0], [])
        self.assertQuerysetEqual(tags[1], [])
        self.assertQuerysetEqual(tags[2], [])
        self.assertQuerysetEqual(tags[3], ['<Tag: Pasta>'])
        self.assertQuerysetEqual(tags[4], ['<Tag: Pasta>'])

    def test_archive_multiple_allowed(self):
        responses = self.responses[0]
        form = responses[0].form_instance.form

        payload = {
            "selected_responses": [str(r.id) for r in responses],
            "action": "mark_invalid"
        }
        self.client.post(make_url(form), data=payload)

        updated_responses = FormResponse.objects.filter(form_instance__form=form).all()
        statuses = [response.status for response in updated_responses]

        self.assertListEqual(statuses, ["I"] * 5)

    def test_verify_multiple_allowed(self):
        responses = self.responses[0]
        form = responses[0].form_instance.form

        payload = {
            "selected_responses": [str(r.id) for r in responses],
            "action": "mark_verified"
        }
        self.client.post(make_url(form), data=payload)

        updated_responses = FormResponse.objects.filter(form_instance__form=form).all()
        statuses = [response.status for response in updated_responses]

        self.assertListEqual(statuses, ["V"] * 5)

    def test_edit_disallowed(self):
        responses = self.responses[0]
        form = self.responses[1][0].form_instance.form

        payload = {
            "selected_responses": [str(r.id) for r in responses],
            "action": "mark_invalid"
        }

        self.client.post(make_url(form), data=payload)

        updated_responses = FormResponse.objects.filter(form_instance__form=form).all()
        statuses = [response.status for response in updated_responses]

        self.assertListEqual(statuses, ["S"] * 5)

    def test_edit_disallowed_and_allowed(self):
        owned_responses = self.responses[0]
        other_responses = self.responses[1]
        responses = owned_responses + other_responses
        form = owned_responses[0].form_instance.form

        payload = {
            "selected_responses": [str(r.id) for r in responses],
            "action": "mark_invalid"
        }

        self.client.post(make_url(form), data=payload)

        updated_responses = FormResponse.objects.all()
        statuses = [response.status for response in updated_responses]

        self.assertListEqual(statuses,
                             ["S"] * 5 + ["I"] * 5,
                             "Should edit the ones for which user"
                             " has permission and leave others untouched")
