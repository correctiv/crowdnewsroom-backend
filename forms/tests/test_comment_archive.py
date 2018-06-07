from django.test import TestCase, Client
from django.urls import reverse

from forms.models import Comment, UserGroup
from forms.tests.factories import UserFactory, CommentFactory


def make_url(comment):
    form_response = comment.form_response
    form = form_response.form_instance.form
    params = {
        "form_slug": form.slug,
        "investigation_slug": form.investigation.slug,
        "response_id": form_response.id,
        "comment_id": comment.id
    }

    return reverse("comment_delete", kwargs=params)


class FormReponseAssigneesTest(TestCase):
    def setUp(self):
        self.user1 = UserFactory.create()
        self.user2 = UserFactory.create()
        self.user3 = UserFactory.create()
        self.comment = CommentFactory.create(author=self.user1)

        admin_user_group = UserGroup.objects.filter(investigation=self.comment.form_response.form_instance.form.investigation,
                                                    role="A").first()
        admin_user_group.group.user_set.add(self.user1)
        admin_user_group.group.user_set.add(self.user2)

        self.client = Client()

    def test_delete_own_comment(self):
        self.client.force_login(self.user1)

        payload = {
            "archived": True,
            "text": self.comment.text
        }
        response = self.client.post(make_url(self.comment), data=payload)
        self.assertEqual(response.status_code, 302)

        updated_comment = Comment.objects.get(id=self.comment.id)
        self.assertEqual(updated_comment.archived, True)

    def test_delete_other_persons_comment_fails(self):
        self.client.force_login(self.user2)

        payload = {
            "archived": True,
            "text": self.comment.text
        }
        response = self.client.post(make_url(self.comment), data=payload)
        self.assertEqual(response.status_code, 403)

        updated_comment = Comment.objects.get(id=self.comment.id)
        self.assertEqual(updated_comment.archived, False)

    def test_delete_other_investigation_comment_fails(self):
        self.client.force_login(self.user3)

        payload = {
            "archived": True,
            "text": self.comment.text
        }
        response = self.client.post(make_url(self.comment), data=payload)
        self.assertEqual(response.status_code, 403)

        updated_comment = Comment.objects.get(id=self.comment.id)
        self.assertEqual(updated_comment.archived, False)
