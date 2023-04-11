import math
from collections import namedtuple
from datetime import timedelta

import django.core.validators as validators
from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager, Group
from django.contrib.postgres.fields import JSONField
from django.core.mail import send_mail
from django.db import models
from django.db.models import Count
from django.db.models.functions import Coalesce, TruncDate
from django.dispatch import receiver
from django.template import Context, Engine
from django.template.loader import get_template
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from guardian.shortcuts import assign_perm, get_users_with_perms

from .mixins import UniqueSlugMixin, validate_slug_stricter
from minio import Minio

Roles = namedtuple('Roles', ['ADMIN', 'OWNER', 'EDITOR', 'VIEWER'])
INVESTIGATION_ROLES = Roles(ADMIN="A", OWNER="O", EDITOR="E", VIEWER="V")


class Investigation(models.Model, UniqueSlugMixin):
    STATUSES = (
        ('D', _('Draft')),
        ('P', _('Published')),
        ('A', _('Archived'))
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True,
                            validators=[validators.validate_slug, validate_slug_stricter])
    cover_image = models.FileField(blank=True, null=True, default=None)
    logo = models.FileField(blank=True, null=True, default=None)
    short_description = models.TextField(blank=True)
    category = models.TextField(blank=True)  # What is this?
    research_questions = models.TextField(blank=True)
    status = models.CharField(max_length=1, choices=STATUSES, default='D')
    # The following fields might be separate?
    # or is this the same as short_description?
    text = models.TextField(blank=True)
    methodology = models.TextField(blank=True)
    faq = models.TextField(blank=True)
    data_privacy_url = models.URLField(null=True, blank=True)
    color = models.CharField(max_length=100, blank=True)

    @property
    def cover_image_url(self):
        if self.cover_image and hasattr(self.cover_image, 'url'):
            return self.cover_image.url
        return ""

    def tags(self):
        return Tag.objects.filter(investigation=self).all()

    class Meta:
        permissions = (
            ('manage_investigation', _('Manage investigation')),
            ('admin_investigation', _('Admin investigation')),
            ('master_investigation', _('Delete investigation and manage owners')),
        )

    def __str__(self):
        return self.name

    def submission_stats(self):
        investigations = FormResponse.objects.filter(
            form_instance__form__investigation=self)
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
        user_perms = get_users_with_perms(
            self, with_superusers=True, attach_perms=True)
        return [user for (user, perms) in user_perms.items() if "manage_investigation" in perms]

    @property
    def admin_users(self):
        user_perms = get_users_with_perms(
            self, with_superusers=True, attach_perms=True)
        return [user for (user, perms) in user_perms.items() if "admin_investigation" in perms]

    @property
    def all_users(self):
        user_perms = get_users_with_perms(
            self, with_superusers=True, attach_perms=True)
        return [user for (user, perms) in user_perms.items() if "view_investigation" in perms]

    def add_user(self, user, role):
        try:
            user_group = UserGroup.objects.get(investigation=self, role=role)
        except UserGroup.DoesNotExist:
            UserGroup.create_all_for(self)
            user_group = UserGroup.objects.get(investigation=self, role=role)
        user_group.group.user_set.add(user)

    def get_users(self, role):
        return UserGroup.objects.get(investigation=self, role=role).group.user_set


@receiver(models.signals.post_save, sender=Investigation)
def execute_after_save(sender, instance, created, *args, **kwargs):
    investigation = instance
    if created:
        UserGroup.create_all_for(investigation)


class UserGroup(models.Model):
    ROLES = (
        (INVESTIGATION_ROLES.OWNER, _('Owner')),
        (INVESTIGATION_ROLES.ADMIN, _('Admin')),
        (INVESTIGATION_ROLES.EDITOR, _('Editor')),
        (INVESTIGATION_ROLES.VIEWER, _('Viewer'))
    )
    investigation = models.ForeignKey(Investigation, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    role = models.CharField(max_length=1, choices=ROLES,
                            default=INVESTIGATION_ROLES.VIEWER)

    def add_user(self, user):
        user_groups = UserGroup.objects.filter(
            investigation=self.investigation)
        for user_group in user_groups:
            user_group.group.user_set.remove(user)
        self.group.user_set.add(user)

    def assign_permissions(self):
        assign_perm("view_investigation", self.group, self.investigation)
        if self.role in [INVESTIGATION_ROLES.EDITOR, INVESTIGATION_ROLES.OWNER, INVESTIGATION_ROLES.ADMIN]:
            assign_perm("manage_investigation", self.group, self.investigation)
        if self.role in [INVESTIGATION_ROLES.OWNER, INVESTIGATION_ROLES.ADMIN]:
            assign_perm("admin_investigation", self.group, self.investigation)
        if self.role == INVESTIGATION_ROLES.OWNER:
            assign_perm("master_investigation", self.group, self.investigation)

    @classmethod
    def create_all_for(cls, investigation):
        for (key, name) in cls.ROLES:
            group_name = "{} - {}s".format(investigation.name, name)
            group, _ = Group.objects.get_or_create(name=group_name)

            user_group, _ = UserGroup.objects.get_or_create(
                role=key, investigation=investigation, group=group)

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
    slug = models.SlugField(max_length=200, unique=True,
                            validators=[validators.validate_slug, validate_slug_stricter])
    status = models.CharField(max_length=1, choices=STATUSES, default='D')
    investigation = models.ForeignKey(Investigation, on_delete=models.CASCADE)
    is_simple = models.BooleanField(default=False)  # if `True`, this form is editable via the frontend form builder
    language = models.CharField(max_length=6, default='de', choices=settings.LANGUAGES)

    def __str__(self):
        return self.name

    @classmethod
    def get_all_for_investigation(cls, investigation_slug):
        return cls.objects.filter(investigation__slug=investigation_slug).all()

    @property
    def instance_properties(self):
        props = {}
        for instance in FormInstance.objects.filter(form=self).all():
            props.update(instance.json_properties)
        return props

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
    ui_schema_json = JSONField(default=dict, blank=True)
    version = models.IntegerField(default=0)
    form = models.ForeignKey(Form, on_delete=models.CASCADE)
    priority_fields = JSONField(default=list, blank=True)
    email_template = models.TextField(
        default=_("Thank you for participating in a crowdnewsroom investigation!"))
    email_template_html = models.TextField(
        default=_("Thank you for participating in a crowdnewsroom investigation!"))
    redirect_url_template = models.TextField(
        default="https://forms.crowdnewsroom.org")

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
            properties.update(
                step.get("schema", dict()).get("properties", dict()))
        return {"type": "object", "properties": properties}

    @property
    def json_properties(self):
        return {k: v.get('title', k.title()) for k, v in self.flat_schema["properties"].items()}

    @property
    def is_simple(self):
        return self.form.is_simple

    @property
    def language(self):
        return self.form.language

    @property
    def language_choices(self):
        return dict(settings.LANGUAGES)

    def form_status(self):
        return self.form.status


class FormResponse(models.Model):
    STATUSES = (
        ('S', _('Submitted')),
        ('V', _('Verified')),
        ('I', _('Invalid'))
    )
    json = JSONField()
    form_instance = models.ForeignKey(FormInstance, on_delete=models.CASCADE)
    status = models.CharField(max_length=1, choices=STATUSES, default='S')
    submission_date = models.DateTimeField()
    last_status_changed_date = models.DateTimeField(default=None, blank=True,
                                                    null=True)
    tags = models.ManyToManyField(Tag, blank=True)
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
    def visible_comments(self):
        return self.comments.filter(archived=False).order_by("-date")

    @property
    def valid_keys(self):
        return self.all_json_properties().keys()

    def _priority_order(self, elem):
        try:
            return self.form_instance.priority_fields.index(elem[0])
        except ValueError:
            return math.inf

    def rendered_fields(self):
        form_data = self.json

        flat_ui_schema = {}

        for (key, values) in self.form_instance.ui_schema_json.items():
            flat_ui_schema.update(values)

        sorted_properties = sorted(self.all_json_properties().items(),
                                   key=self._priority_order)

        for name, props in sorted_properties:
            # ignore one line
            if 'one-line' not in name:
                title = props.get("question") or flat_ui_schema.get(name, {}).get("ui:question", name)
                if not title or name == title:
                    title = props.get("title") or flat_ui_schema.get(name, {}).get("ui:title", name)
                if not title:
                    title = name
                row = {"title": title, "label":props.get("title"), "json_name": name,
                    "data_type": props.get("type")}

                if (flat_ui_schema.get(name, dict()).get("ui:widget") ==
                        "signatureWidget" or props.get("format") == "data-url"):
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
                elif props.get("type") == "array" and props["items"].get("format") == "data-url":
                    for index, part in enumerate(form_data.get(name, [])):
                        row = {"title": "{} {}".format(title, index),
                            "json_name": "{}-{}".format(name, index)}
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
                elif props.get("slug"):
                    if 'yes-no' in props.get("slug"):
                        row["type"] = "yes-no"
                        row["value"] = form_data.get(name, "")
                        for prop in props['items']['enum']:
                            if prop['next_slide'] == row["value"]:
                                row["value"] = prop['name']
                    else:
                        if props.get("slug") is not None and 'video' in props.get("slug"):
                            mc = Minio(
                                settings.MINIO_ASSETS_URL,
                                access_key=settings.MINIO_ACCESS_KEY,
                                secret_key=settings.MINIO_SECRET_KEY
                            )
                            url = mc.get_presigned_url(
                                "GET",
                                "videos",
                                form_data.get(name, ""),
                                expires=timedelta(days=1),
                            )
                            row["type"] = "link"
                            row["value"] = url
                        else:
                            row["type"] = "text"
                            row["value"] = form_data.get(name, "")
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
        try:
            return self.json["email"]
        except KeyError:
            for key in sorted(self.json.keys()):
                if "email" in key:
                    return self.json[key]
        return ""

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
            .order_by(Coalesce('last_status_changed_date', 'submission_date').desc())

    def __str__(self):
        try:
            return "{} - {}".format(self.json['email'], self.form_instance.form)
        except:
            return "Form Response {}".format(self.pk)



def generate_emails(form_response: FormResponse):
    plaintext_template = Engine().from_string(
        str(form_response.form_instance.email_template))
    html_template = Engine().from_string(
        str(form_response.form_instance.email_template_html))
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
            send_mail(subject=_("Thank you for your submission!"),
                      message=message,
                      from_email=settings.DEFAULT_FROM_EMAIL,
                      recipient_list=[email],
                      html_message=html_message)


class Comment(models.Model):
    author = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    date = models.DateTimeField()
    form_response = models.ForeignKey(
        FormResponse, on_delete=models.CASCADE, related_name="comments")
    text = models.TextField()
    archived = models.BooleanField(default=False)


class Invitation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    investigation = models.ForeignKey(Investigation, on_delete=models.CASCADE)
    accepted = models.NullBooleanField()

    class Meta:
        unique_together = ('user', 'investigation')

    def send_user_email(self):
        template = get_template("invitation_email.txt")
        message = template.render({"investigation": self.investigation})
        subject = _("You have been invited to join the {} investigation".format(
            self.investigation.name))
        send_mail(subject=subject,
                  message=message,
                  from_email=settings.DEFAULT_FROM_EMAIL,
                  recipient_list=[self.user.email])


@receiver(models.signals.post_save, sender=Invitation)
def add_user_to_investigation(sender, instance, created, *args, **kwargs):
    invitation = instance
    if invitation.accepted:
        invitation.investigation.add_user(invitation.user, "V")
        invitation.delete()


class FormInstanceTemplate(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    form_json = JSONField()
    ui_schema_json = JSONField(default=dict, blank=True)
    priority_fields = JSONField(default=list, blank=True)
    email_template = models.TextField(
        default=_("Thank you for participating in a crowdnewsroom investigation!"))
    email_template_html = models.TextField(
        default=_("Thank you for participating in a crowdnewsroom investigation!"))
    redirect_url_template = models.TextField(
        default="https://forms.crowdnewsroom.org")
    is_simple = models.BooleanField(default=False)  # if `True`, this form is editable via the frontend form builder

    def __str__(self):
        return self.name
