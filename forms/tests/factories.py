import factory
from django.utils import timezone
from django.utils.text import slugify

from forms import models


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.User

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("safe_email")


class InvestigationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Investigation

    name = factory.Sequence(lambda n: 'Investigation %s' % n)
    slug = factory.LazyAttribute(lambda a: slugify(a.name))


class FormFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Form

    name = factory.Sequence(lambda n: 'Form %s' % n)
    slug = factory.LazyAttribute(lambda a: slugify(a.name))
    investigation = factory.SubFactory(InvestigationFactory)


class FormInstanceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.FormInstance

    form = factory.SubFactory(FormFactory)
    form_json = []


class FormResponseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.FormResponse

    form_instance = factory.SubFactory(FormInstanceFactory)
    submission_date = timezone.now()
    json = {}


class TagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Tag

    name = factory.Sequence(lambda n: 'Tag %s' % n)
    slug = factory.LazyAttribute(lambda a: slugify(a.name))
    investigation = factory.SubFactory(InvestigationFactory)


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Comment

    text = factory.Faker("paragraph")
    author = factory.SubFactory(UserFactory)
    date = timezone.now()
    form_response = factory.SubFactory(FormResponseFactory)
