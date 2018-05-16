import smtplib
from datetime import timedelta

from django.core.mail import send_mail
from django.db.models import Count
from django.template import Engine, Context
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe

from . import secrets  # TODO: Replace with included module once updated to python 3.6
from .mixins import UniqueSlugMixin

from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import Group, AbstractUser, BaseUserManager
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.dispatch import receiver
from guardian.shortcuts import assign_perm, get_users_with_perms
from django.db.models.functions import TruncDate


class Investigation(models.Model, UniqueSlugMixin):
    STATUSES = (
        ('D', _('Draft')),
        ('P', _('Published')),
        ('A', _('Archived'))
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    cover_image = models.FileField(blank=True, null=True, default=None)
    logo = models.FileField(blank=True, null=True, default=None)
    short_description = models.TextField()
    category = models.TextField()  # What is this?
    research_questions = models.TextField()
    status = models.CharField(max_length=1, choices=STATUSES, default='D')
    # The following fields might be separate?
    text = models.TextField()  # or is this the same as short_description?
    methodology = models.TextField()
    faq = models.TextField()
    data_privacy_url = models.URLField(null=True)

    @property
    def cover_image_url(self):
        if self.cover_image and hasattr(self.cover_image, 'url'):
            return self.cover_image.url
        return ""

    def tags(self):
        return list(Tag.objects.filter(investigation=self).all())

    class Meta:
        permissions = (
            ('view_investigation', _('View investigation')),
            ('manage_investigation', _('Manage investigation')),
        )

    def __str__(self):
        return self.name

    def submission_stats(self):
        investigations = FormResponse.objects.filter(form_instance__form__investigation=self)
        total = investigations.count()
        today_start = timezone.now().replace(minute=0, hour=0, second=0)
        yesterday_start = today_start - timedelta(days=1)
        yesterday = investigations.filter(submission_date__gte=yesterday_start)\
                                  .filter(submission_date__lt=today_start)\
                                  .count()
        to_verify = investigations.filter(status="S").count()
        return {
            "total": total,
            "yesterday": yesterday,
            "to_verify": to_verify,
        }

    @property
    def manager_users(self):
        user_perms = get_users_with_perms(self, with_superusers=True, attach_perms=True)
        return [user for (user, perms) in user_perms.items() if "manage_investigation" in perms]


@receiver(models.signals.post_save, sender=Investigation)
def execute_after_save(sender, instance, created, *args, **kwargs):
    investigation = instance
    if created:
        UserGroup.create_all_for(investigation)


class UserGroup(models.Model):
    ROLES = (
        ('O', _('Owner')),
        ('A', _('Admin')),
        ('E', _('Editor')),
        ('A', _('Auditor')),
        ('V', _('Viewer'))
    )
    investigation = models.ForeignKey(Investigation, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    role = models.CharField(max_length=1, choices=ROLES, default='V')

    def assign_permissions(self):
        assign_perm("view_investigation", self.group, self.investigation)
        if self.role in ["O", "A"]:
            assign_perm("manage_investigation", self.group, self.investigation)

    @classmethod
    def create_all_for(cls, investigation):
        for (key, name) in cls.ROLES:
            group_name = "{} - {}s".format(investigation.name, name)
            group = Group(name=group_name)
            group.save()

            user_group = UserGroup(role=key, investigation=investigation, group=group)
            user_group.save()

            user_group.assign_permissions()


@receiver(models.signals.post_delete, sender=UserGroup)
def my_post_delete_callback(sender, **kwargs):
    kwargs['instance'].group.delete()


class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.first_name or self.email


class Partner(models.Model):
    name = models.CharField(max_length=200)
    logo = models.FileField()
    url = models.TextField(max_length=1000)
    investigation = models.ForeignKey(Investigation, on_delete=models.CASCADE)


class Tag(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    investigation = models.ForeignKey(Investigation, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Form(models.Model, UniqueSlugMixin):
    STATUSES = (
        ('D', _('Draft')),
        ('U', _('Unlisted')),
        ('P', _('Published')),
        ('C', _('Closed')),
        ('A', _('Archived'))
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    status = models.CharField(max_length=1, choices=STATUSES, default='D')
    investigation = models.ForeignKey(Investigation, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    @classmethod
    def get_all_for_investigation(cls, investigation_slug):
        return cls.objects.filter(investigation__slug=investigation_slug).all()

    @property
    def instance_properties(self):
        keys = set()
        for instance in FormInstance.objects.filter(form=self).all():
            keys |= instance.json_properties
        return keys

    def submissions_by_date(self):
        return FormResponse.objects \
            .filter(form_instance__form=self) \
            .annotate(date=TruncDate('submission_date')) \
            .values('date') \
            .annotate(c=Count('id')) \
            .values('date', 'c') \
            .order_by('date')

    def count_by_bucket(self):
        results = FormResponse.objects \
            .filter(form_instance__form=self) \
            .values("status") \
            .annotate(count=Count('status'))
        return {bucket["status"]: bucket["count"] for bucket in results}


class FormInstance(models.Model):
    form_json = JSONField()
    ui_schema_json = JSONField(default={})
    version = models.IntegerField(default=0)
    form = models.ForeignKey(Form, on_delete=models.CASCADE)
    email_template = models.TextField(default=_("Thank you for participating in a crowdnewsroom investigation!"))
    email_template_html = models.TextField(default=_("Thank you for participating in a crowdnewsroom investigation!"));
    redirect_url_template = models.TextField(default="https://forms.crowdnewsroom.org")

    def __str__(self):
        return "{} - Instance version {}".format(self.form.name, self.version)

    @staticmethod
    def get_latest_for_form(form_slug):
        return FormInstance.objects \
            .filter(form__slug=form_slug) \
            .order_by("-version") \
            .first()

    @property
    def flat_schema(self):
        properties = {}
        for step in self.form_json:
            properties.update(step["schema"]["properties"])
        return {"type": "object", "properties": properties}

    @property
    def json_properties(self):
        return set(self.flat_schema["properties"].keys())


class FormResponse(models.Model):
    STATUSES = (
        ('S', _('Submitted')),
        ('V', _('Verified')),
        ('I', _('Invalid'))
    )
    json = JSONField()
    form_instance = models.ForeignKey(FormInstance, on_delete=models.CASCADE)
    status = models.CharField(max_length=1, choices=STATUSES, default='S')
    token = models.CharField(max_length=256, db_index=True, default=secrets.token_urlsafe)
    email = models.EmailField()
    submission_date = models.DateTimeField()
    tags = models.ManyToManyField(Tag)
    assignees = models.ManyToManyField(User)

    class Meta:
        permissions = (
            ('edit_response', _('Edit response')),
        )

    def all_json_properties(self):
        properties = {}
        for step in self.form_instance.form_json:
            properties.update(step["schema"].get("properties", {}))
        return properties

    @property
    def valid_keys(self):
        return self.all_json_properties().keys()

    def rendered_fields(self):
        form_data = self.json

        flat_ui_schema = {}
        for (key, values) in self.form_instance.ui_schema_json.items():
            flat_ui_schema.update(values)

        for name, props in self.all_json_properties().items():
            title = flat_ui_schema.get(name, {}).get("ui:title", name) or props.get("title")
            row = {"title": title, "json_name": name, "data_type": props.get("type")}
            if (flat_ui_schema.get(name, dict()).get("ui:widget") == "signatureWidget"
                    or props.get("format") == "data-url"):
                if form_data.get(name):
                    row["type"] = "link"
                    row["value"] = reverse("response_file",
                                           kwargs={"investigation_slug": self.form_instance.form.investigation.slug,
                                                   "form_slug": self.form_instance.form.slug,
                                                   "response_id": self.id,
                                                   "file_field": name
                                                   })
                else:
                    row["type"] = "text"
                    row["value"] = ""
            elif props.get("type") == "array" and props["items"]["format"] == "data-url":
                for index, part in enumerate(form_data.get(name, [])):
                    row = {"title": "{} {}".format(title, index),
                           "json_name": "{}-{}".format(name,index)}
                    row["type"] = "link"
                    row["value"] = reverse("response_file_array",
                                           kwargs={"investigation_slug": self.form_instance.form.investigation.slug,
                                                   "form_slug": self.form_instance.form.slug,
                                                   "response_id": self.id,
                                                   "file_field": name,
                                                   "file_index": index
                                                   })
                    yield row
                continue
            elif props.get("type") == "boolean":
                row["type"] = "text"
                row["value"] = _("Yes") if form_data.get(name) else _("No")
            else:
                row["type"] = "text"
                row["value"] = form_data.get(name, "")
            yield row

    @property
    def redirect_url(self):
        url_template = self.form_instance.redirect_url_template
        template = Engine().from_string(url_template)
        context = Context(dict(response=self.json))
        return template.render(context=context)

    @property
    def email_fields(self):
        entries = []
        for row in self.rendered_fields():
            value = row["value"] if row["type"] == "text" else _("<File>")
            entries.append("{}: {}".format(row["title"], value))
        return "\n".join(entries)

    @property
    def json_email(self):
        return self.json.get("email", "")

    def belongs_to_investigation(self, investigation_slug):
        return self.form_instance.form.investigation.slug == investigation_slug

    @property
    def taglist(self):
        investigation = self.form_instance.form.investigation
        return Tag.objects.filter(investigation=investigation)

    @classmethod
    def get_all_for_form(cls, form):
        return cls.objects\
                .filter(form_instance__form=form) \
                .order_by("-submission_date")

    def set_password_for_user(self, password):
        contributor, user_created = User.objects.get_or_create(email=self.email)
        if user_created:
            contributor.set_password(password)
            contributor.save()
        assign_perm("edit_response", contributor, self)


def generate_emails(form_response: FormResponse):
    plaintext_template = Engine().from_string(str(form_response.form_instance.email_template))
    html_template = Engine().from_string(str(form_response.form_instance.email_template_html))
    context = Context(dict(response=form_response.json,
                           field_list=mark_safe(form_response.email_fields)))
    return (plaintext_template.render(context=context),
            html_template.render(context=context))


@receiver(models.signals.post_save, sender=FormResponse)
def send_email(sender, instance, created, *args, **kwargs):
    form_response = instance
    if created:
        email = form_response.json.get("email")
        confirm_summary = form_response.json.get("confirm_summary")
        if email and confirm_summary:
            message, html_message = generate_emails(form_response)
            try:
                send_mail(subject=_("Thank you for your submission!"),
                          message=message,
                          from_email="wem-gehoert-hamburg@crowdnewsroom.org",
                          recipient_list=[email],
                          html_message=html_message)
            except smtplib.SMTPException:
                # TODO: Notify bugsnag here? Or do something else..
                pass


class Comment(models.Model):
    author = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    date = models.DateTimeField()
    form_response = models.ForeignKey(FormResponse, on_delete=models.CASCADE)
    text = models.TextField()

