from unittest.mock import patch
from django.test import TestCase, Client, LiveServerTestCase, tag
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver

from forms.models import User
from forms.tests.factories import FormResponseFactory, FormInstanceFactory, TagFactory, UserFactory


@patch('webpack_loader.loader.WebpackLoader.get_bundle')
class FormReponseListViewTest(TestCase):
    def setUp(self):
        self.form_instance = FormInstanceFactory.create()
        for index, status in enumerate(["V", "V", "S", "S"]):
            json = {"has_car": True} if index % 2 == 0 else {}
            FormResponseFactory.create(status=status,
                                       form_instance=self.form_instance,
                                       json=json)

        User.objects.create_superuser('admin@crowdnewsroom.org', 'password')
        self.client = Client()
        self.client.login(email='admin@crowdnewsroom.org', password='password')

    def test_inbox(self, *args):
        form = self.form_instance.form

        response = self.client.get("/forms/admin/investigations/{}/forms/{}/responses/inbox".format(form.investigation.slug, form.slug))
        self.assertEquals(len(response.context_data["formresponse_list"]), 2)

        response = self.client.get("/forms/admin/investigations/{}/forms/{}/responses/trash".format(form.investigation.slug, form.slug))
        self.assertEquals(len(response.context_data["formresponse_list"]), 0)

        response = self.client.get("/forms/admin/investigations/{}/forms/{}/responses/verified".format(form.investigation.slug, form.slug))
        self.assertEquals(len(response.context_data["formresponse_list"]), 2)

    def test_has_filters(self, *args):
        form = self.form_instance.form

        response = self.client.get("/forms/admin/investigations/{}/forms/{}/responses/verified?has=has_car".format(form.investigation.slug, form.slug))
        self.assertEquals(len(response.context_data["formresponse_list"]), 1)

    def test_tag_filters(self, *args):
        form = self.form_instance.form
        tag = TagFactory.create(investigation=form.investigation, name="Avocado", slug="avocado")
        form_response = FormResponseFactory.create(form_instance=self.form_instance)
        form_response.tags.set([tag])

        response = self.client.get(
            "/forms/admin/investigations/{}/forms/{}/responses/inbox?tag=avocado".format(form.investigation.slug, form.slug))
        self.assertListEqual(
            list(response.context_data["formresponse_list"].all()),
            [form_response]
        )

    def test_assignee_filters(self, *args):
        form = self.form_instance.form
        user = UserFactory.create()
        form_response = FormResponseFactory.create(form_instance=self.form_instance)
        form_response.assignees.set([user])

        # create another one to make sure that this one is not returned later
        FormResponseFactory.create(form_instance=self.form_instance)

        response = self.client.get(
            "/forms/admin/investigations/{}/forms/{}/responses/inbox?assignee={}".format(form.investigation.slug, form.slug, user.email))
        self.assertListEqual(
            list(response.context_data["formresponse_list"].all()),
            [form_response]
        )

    def test_email_filters(self, *args):
        form = self.form_instance.form
        edwards_response = FormResponseFactory.create(form_instance=self.form_instance, json={"email": "edward@example.com"})

        FormResponseFactory.create(form_instance=self.form_instance, json={"email": "edwardina@example.com"})

        response = self.client.get(
            "/forms/admin/investigations/{}/forms/{}/responses/inbox?email=edward@example.com".format(form.investigation.slug, form.slug))
        self.assertListEqual(
            list(response.context_data["formresponse_list"].all()),
            [edwards_response]
        )

    def test_email_filters_partial(self, *args):
        form = self.form_instance.form
        FormResponseFactory.create(form_instance=self.form_instance, json={"email": "edward@example.com"})
        FormResponseFactory.create(form_instance=self.form_instance, json={"email": "edwardina@example.com"})
        FormResponseFactory.create(form_instance=self.form_instance, json={"email": "bella@example.com"})

        response = self.client.get(
            "/forms/admin/investigations/{}/forms/{}/responses/inbox?email=edward".format(form.investigation.slug, form.slug))
        self.assertEqual(len(response.context_data["formresponse_list"]), 2)


@tag("browsertest")
@patch('webpack_loader.loader.WebpackLoader.get_bundle')
class FormResponseListBrowserTest(LiveServerTestCase):
    def setUp(self):
        self.form_instance = FormInstanceFactory.create()
        User.objects.create_superuser('admin@crowdnewsroom.org', 'password')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        options = webdriver.ChromeOptions()
        options.set_headless()
        options.add_argument("--no-sandbox")
        cls.selenium = WebDriver(options=options)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_login(self, *args):
        self.selenium.get('%s%s' % (self.live_server_url, '/accounts/login/'))
        username_input = self.selenium.find_element_by_name("username")
        username_input.send_keys('admin@crowdnewsroom.org')
        password_input = self.selenium.find_element_by_name("password")
        password_input.send_keys('password')
        self.selenium.find_element_by_xpath('//button[@type="submit"]').click()

        url = "/forms/admin/investigations/{}/forms/{}/responses/inbox".format(
            self.form_instance.form.investigation.slug,
            self.form_instance.form.slug
        )
        self.selenium.get('%s%s' % (self.live_server_url, url))

        email_input = self.selenium.find_element_by_name("email")
        self.assertEqual(email_input.get_attribute("value"), "")




