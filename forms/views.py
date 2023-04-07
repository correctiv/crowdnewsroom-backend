import datetime
import uuid

from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError
from django.http import (Http404, HttpResponse, HttpResponseRedirect)
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from datetime import timedelta
from minio import Minio
from rest_framework import generics, permissions, serializers, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import DjangoObjectPermissions, IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer

from .fields import Base64ImageField
from .models import (INVESTIGATION_ROLES, Form, FormInstance,
                     FormInstanceTemplate, FormResponse, Investigation,
                     Invitation, Tag, User, UserGroup)


class InvestigationSerializer(ModelSerializer):
    logo = Base64ImageField(required=False)

    class Meta:
        model = Investigation
        fields = "__all__"


class InvestigationPermissions(DjangoObjectPermissions):
    perms_map = {
        'GET': [],
        'OPTIONS': [],
        'HEAD': [],
        'POST': [],
        'PUT': ['manage_investigation'],
        'PATCH': ['manage_investigation'],
        'DELETE': ['master_investigation'],
    }

    def has_permission(self, request, view):
        # We never want to check model-based permissions, only
        # object-based permissions. This is why we override
        # this method and rely on `has_object_permission` alone
        return True


class InvestigationDetail(generics.RetrieveUpdateDestroyAPIView):
    # TODO: This should filter to make sure to only return
    # Investigations that are published and not in draft or unlisted state
    queryset = Investigation.objects.all()
    serializer_class = InvestigationSerializer
    lookup_url_kwarg = "investigation_slug"
    lookup_field = "slug"
    permission_classes = (InvestigationPermissions, )


class FormInstanceSerializer(ModelSerializer):
    class Meta:
        model = FormInstance
        fields = (
            "id",
            "form_json",
            "ui_schema_json",
            "version",
            "form",
            "form_status",
            "priority_fields",
            "email_template",
            "email_template_html",
            "is_simple",
            "language",
            "language_choices",
            "redirect_url_template"
        )
        read_only_fields = ("form", "version",)

    def create(self, validated_data, *args, **kwargs):
        view = self.context.get("view")

        form = get_object_or_404(Form, id=view.kwargs.get("form_id"))
        form.is_simple = view.request.data.get('is_simple', True)
        form.save()

        latest_form_instance = FormInstance.get_latest_for_form(form.slug)
        next_version = 1 if not latest_form_instance else latest_form_instance.version + 1
        form_instance = FormInstance(**validated_data)
        form_instance.form = form
        form_instance.version = next_version

        if not 'email_template' in validated_data:
            form_instance.email_template = latest_form_instance.email_template

        if not 'email_template_html' in validated_data:
            form_instance.email_template_html = latest_form_instance.email_template_html

        if not 'redirect_url_template' in validated_data:
            form_instance.redirect_url_template = latest_form_instance.redirect_url_template

        form_instance.save()

        return form_instance

    def save(self, *args, **kwargs):
        view = self.context['view']
        data = self.context['request'].data
        form = get_object_or_404(Form, id=view.kwargs.get("form_id"))
        if 'language' in data:
            form.language = data['language']
            form.save()
        return super().save(*args, **kwargs)


class FormInstanceDetail(generics.RetrieveAPIView):
    serializer_class = FormInstanceSerializer
    lookup_url_kwarg = "form_slug"

    def get_object(self, *args, **kwargs):
        form_slug = self.kwargs.get("form_slug")
        form_instance = FormInstance.get_latest_for_form(form_slug)
        if form_instance is None:
            raise Http404
        return form_instance


class FormResponseSerializer(ModelSerializer):
    class Meta:
        model = FormResponse
        read_only_fields = ("submission_date", "id", "status", "redirect_url")
        fields = ("json", "form_instance") + read_only_fields

    def create(self, validated_data, *args, **kwargs):
        fr = FormResponse(**validated_data)
        fr.submission_date = datetime.datetime.now()
        fr.save()
        return fr


class TagField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        form_response = self.context['view'].get_object()
        return form_response.taglist


class AssigneeField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        form_response = self.context['view'].get_object()  # type: FormResponse
        investigation_users = form_response.form_instance.form.investigation.manager_users
        # We already have a list of all the users here but Django expects us to pass
        # a queryset to the form, not a list of objects so we manually create
        # that query here.
        return User.objects.filter(id__in=[user.id for user in investigation_users])


class FormResponseMetaSerializer(ModelSerializer):
    """ contains all information about the response that is not the submission itself"""
    tags = TagField(many=True, required=False)
    assignees = AssigneeField(many=True, required=False)

    class Meta:
        model = FormResponse
        exclude = ("json",)


def get_investigation(instance):
    """ returns this objects related investigation (used for authentication)"""
    if isinstance(instance, FormResponse):
        return instance.form_instance.form.investigation
    if isinstance(instance, Tag):
        return instance.investigation
    if isinstance(instance, Form):
        return instance.investigation


class CanEditInvestigation(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        investigation = get_investigation(obj)
        return request.user.has_perm("admin_investigation", investigation)


class FormResponseDetail(generics.RetrieveUpdateAPIView):
    lookup_url_kwarg = "response_id"
    serializer_class = FormResponseMetaSerializer
    queryset = FormResponse
    permission_classes = [CanEditInvestigation]

    def perform_update(self, serializer):
        old_obj = self.get_object()
        status = serializer.validated_data.get("status")

        if status and old_obj.status != status:
            serializer.save(last_status_changed_date=timezone.now())
        else:
            serializer.save()


class TagSerializer(ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"
        read_only_fields = ("investigation",)

    def create(self, validated_data, *args, **kwargs):
        view = self.context.get("view")
        investigation_slug = view.kwargs.get("investigation_slug")
        investigation = get_object_or_404(
            Investigation, slug=investigation_slug)

        tag = Tag(**validated_data)
        tag.investigation = investigation
        tag.save()
        return tag


class InvestigationObjectPermissions(DjangoObjectPermissions):
    permission = "manage_investigation"

    def has_permission(self, request, view):
        investigation = Investigation.objects.get(
            slug=request.parser_context["kwargs"].get("investigation_slug"))
        return request.user.has_perm(self.permission, investigation)


class InvestigationObjectViewPermissions(InvestigationObjectPermissions):
    permission = "view_investigation"


class InvestigationObjectManagePermissions(InvestigationObjectPermissions):
    permission = "admin_investigation"


class TagList(generics.ListCreateAPIView):
    serializer_class = TagSerializer
    permission_classes = (InvestigationObjectViewPermissions,)

    def get_queryset(self):
        investigation = Investigation.objects.get(
            slug=self.kwargs.get("investigation_slug"))
        return Tag.objects.filter(investigation=investigation).all()


class AssigneeSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "id")


class AssigneeList(generics.ListAPIView):
    serializer_class = AssigneeSerializer
    permission_classes = (InvestigationObjectViewPermissions,)

    def get_queryset(self):
        investigation = Investigation.objects.get(
            slug=self.kwargs.get("investigation_slug"))
        investigation_users = investigation.manager_users
        # We already have a list of all the users here but Django expects us to pass
        # a queryset to the form, not a list of objects so we manually create
        # that query here.
        return User.objects.filter(id__in=[user.id for user in investigation_users])


class InvestigationUsersSerializer(serializers.ModelSerializer):
    users = serializers.SerializerMethodField()

    def get_users(self, investigation):
        user_groups = UserGroup.objects.filter(
            investigation=investigation).all()

        for user_group in user_groups:
            for user in user_group.group.user_set.all():
                yield {"first_name": user.first_name,
                       "last_name": user.last_name,
                       "email": user.email,
                       "role": user_group.role,
                       "id": user.id,
                       "is_requester": self.context["request"].user == user
                       }

    class Meta:
        model = Investigation
        fields = ("users",)


class UserList(generics.RetrieveAPIView):
    serializer_class = InvestigationUsersSerializer
    lookup_url_kwarg = "investigation_slug"
    queryset = Investigation
    lookup_field = "slug"


class UserGroupUserList(generics.ListCreateAPIView):
    serializer_class = AssigneeSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user_group = UserGroup.objects.get(investigation__slug=self.kwargs.get("investigation_slug"),
                                           role=self.kwargs.get("role"))
        return User.objects.filter(groups=user_group.group)

    def create(self, request, *args, **kwargs):
        user_group = UserGroup.objects.get(investigation__slug=self.kwargs.get("investigation_slug"),
                                           role=self.kwargs.get("role"))
        user = User.objects.get(id=request.data.get("id"))
        user_group.add_user(user)
        return self.get(request, *args, **kwargs)

    def check_permissions(self, request):
        super().check_permissions(request)

        investigation = Investigation.objects.get(
            slug=self.kwargs.get("investigation_slug"))
        if not request.user.has_perm("admin_investigation", investigation):
            raise PermissionDenied(detail="not allowed!")

        role = self.kwargs.get("role")
        if role == INVESTIGATION_ROLES.OWNER and not request.user.has_perm("master_investigation", investigation):
            raise PermissionDenied(detail="not allowed!")


class UserGroupMembershipDelete(generics.DestroyAPIView):
    permission_classes = (IsAuthenticated,)

    def delete(self, request, investigation_slug, role, user_id):
        user_group = UserGroup.objects.get(
            investigation__slug=investigation_slug, role=role)
        user = User.objects.get(id=user_id)
        user_group.group.user_set.remove(user)
        return HttpResponse(200)

    def check_permissions(self, request):
        super().check_permissions(request)

        user_id = self.kwargs.get("user_id")
        user = get_object_or_404(User, id=user_id)
        if request.user == user:
            # users can always remove themselves
            return True

        investigation = Investigation.objects.get(
            slug=self.kwargs.get("investigation_slug"))
        if not request.user.has_perm("admin_investigation", investigation):
            raise PermissionDenied(detail="not allowed!")

        role = self.kwargs.get("role")
        if role == INVESTIGATION_ROLES.OWNER and not request.user.has_perm("master_investigation", investigation):
            raise PermissionDenied(detail="not allowed!")


class FormResponseCreate(generics.CreateAPIView):
    queryset = FormResponse
    serializer_class = FormResponseSerializer


class InvitationSerializer(ModelSerializer):
    email = serializers.SerializerMethodField()

    def get_email(self, invitation):
        return invitation.user.email

    class Meta:
        model = Invitation
        fields = ("email", "id", "accepted")


class InvestigationInvitationPermissions(DjangoObjectPermissions):
    def has_permission(self, request, view):
        investigation = Investigation.objects.get(
            slug=view.kwargs.get("investigation_slug"))
        if not request.user.has_perm("admin_investigation", investigation):
            return False
        return True


def create_and_invite_user(email, request):
    form = PasswordResetForm(data={"email": email})
    if form.errors:
        raise ValidationError(form.errors)

    user = User.objects.create(email=email, is_active=True)
    user.set_password(uuid.uuid4())
    user.save()
    form.save(request=request,
              from_email=settings.DEFAULT_FROM_EMAIL,
              subject_template_name="registration/set_initial_password_subject.txt",
              email_template_name="registration/set_initial_password_email.html")
    return user


class InvitationList(generics.ListCreateAPIView):
    serializer_class = InvitationSerializer
    permission_classes = (InvestigationInvitationPermissions, )

    def get_queryset(self):
        investigation = get_object_or_404(
            Investigation, slug=self.kwargs.get("investigation_slug"))
        return Invitation.objects.filter(investigation=investigation).all()

    def create(self, request, investigation_slug):
        investigation = get_object_or_404(
            Investigation, slug=investigation_slug)
        email = request.data.get("email")
        new_user = False
        try:
            user = User.objects.get(email=email)
        except ObjectDoesNotExist:
            try:
                user = create_and_invite_user(email, request)
                new_user = True
            except ValidationError as errors:
                return Response(errors.error_dict, status.HTTP_400_BAD_REQUEST)

        if user in investigation.all_users:
            return Response({"message": "user is  in investigation already"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            invitation = Invitation.objects.create(
                user=user, investigation=investigation)
        except IntegrityError:
            return Response({"message": "invitation already exists"}, status=status.HTTP_400_BAD_REQUEST)

        # if the user is new, they already got an e-mail which prompts them
        # to create an account. No need to send them another one here.
        if not new_user:
            invitation.send_user_email()

        serializer = self.get_serializer()
        serialized = serializer.to_representation(invitation)
        return Response(serialized, status=status.HTTP_201_CREATED)


class InvitationPermissions(DjangoObjectPermissions):
    def has_permission(self, request, view):
        # Since this only handles PATCH and DELETE we only care about
        # object permissions and not class permissions.
        # It is therefore save to return True here
        return True

    def has_object_permission(self, request, view, obj):
        invitation = obj
        if request.method == "PATCH":
            return invitation.user == request.user
        elif request.method == "DELETE":
            investigation = invitation.investigation
            return request.user.has_perm("admin_investigation", investigation)
        # "This should never happen"
        return False


class UserInvitationSerializer(ModelSerializer):
    investigation = InvestigationSerializer(read_only=True)

    class Meta:
        model = Invitation
        fields = ("investigation", "id", "accepted")


class InvitationDetails(generics.RetrieveUpdateDestroyAPIView):
    queryset = Invitation
    lookup_url_kwarg = "invitation_id"
    serializer_class = UserInvitationSerializer
    permission_classes = (InvitationPermissions, )


class UserInvitationList(generics.ListAPIView):
    serializer_class = UserInvitationSerializer
    permission_classes = (IsAuthenticated, )

    def get_queryset(self):
        return Invitation.objects.filter(user=self.request.user).all()


class InvestigationCreate(generics.CreateAPIView):
    queryset = Investigation
    serializer_class = InvestigationSerializer

    permission_classes = (IsAuthenticated, )

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        new_investigation = Investigation.objects.get(
            id=response.data.get('id'))
        new_investigation.add_user(request.user, "O")
        return response


class FormInstanceListTemplateSerializer(ModelSerializer):
    class Meta:
        model = FormInstanceTemplate
        fields = ("id", "name", "description")


class FormInstanceTemplateList(generics.ListAPIView):
    queryset = FormInstanceTemplate.objects.all()
    serializer_class = FormInstanceListTemplateSerializer
    permission_classes = (IsAuthenticated, )


class FormInstanceDetailsTemplateSerializer(ModelSerializer):
    class Meta:
        model = FormInstanceTemplate
        fields = "__all__"


class FormInstanceTemplateDetails(generics.RetrieveAPIView):
    queryset = FormInstanceTemplate.objects.all()
    serializer_class = FormInstanceDetailsTemplateSerializer
    permission_classes = (IsAuthenticated, )


class TagEditDelete(generics.RetrieveUpdateDestroyAPIView):
    queryset = Tag
    serializer_class = TagSerializer
    permission_classes = (IsAuthenticated, CanEditInvestigation)


class FormInstancePermissions(DjangoObjectPermissions):
    def has_permission(self, request, view):
        form_id = view.kwargs.get("form_id")
        form = get_object_or_404(Form, id=form_id)
        investigation = form.investigation
        return request.user.has_perm("admin_investigation", investigation)


class FormInstanceListCreate(generics.ListCreateAPIView):
    serializer_class = FormInstanceSerializer
    permission_classes = (IsAuthenticated, FormInstancePermissions)
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        return FormInstance.objects\
            .filter(form_id=self.kwargs.get("form_id"))\
            .order_by("-version") \
            .all()


class FormSerializer(ModelSerializer):
    frontend_url = serializers.SerializerMethodField()

    class Meta:
        model = Form
        fields = "__all__"
        read_only_fields = ("investigation", "frontend_url")

    def get_frontend_url(self, form):
        params = {
            "base_url": settings.FRONTEND_BASE_URL,
            "investigation_slug": form.investigation.slug,
            "form_slug": form.slug
        }

        return "{base_url}/{investigation_slug}/{form_slug}".format(**params)

    def create(self, validated_data, *args, **kwargs):
        investigation_slug = self.context['view'].kwargs.get(
            "investigation_slug")
        investigation = get_object_or_404(
            Investigation, slug=investigation_slug)
        form = Form(**validated_data)
        form.investigation = investigation
        form.save()
        return form


class FormCreate(generics.CreateAPIView):
    serializer_class = FormSerializer
    permission_classes = (
        IsAuthenticated, InvestigationObjectManagePermissions)


class FormDuplicate(generics.CreateAPIView):
    permission_classes = (
        IsAuthenticated, InvestigationObjectManagePermissions)

    def create(self, request, *args, **kwargs):
        investigation_slug = self.kwargs.get(
            "investigation_slug")
        form_slug = self.kwargs.get(
            "form_slug")
        
        investigation = get_object_or_404(
            Investigation, slug=investigation_slug)

        form = get_object_or_404(
            Form, slug=form_slug, investigation=investigation)

        form_instance = FormInstance.objects.filter(
            form = form).last()

        # copy form
        form.pk = None

        hash = str(uuid.uuid4())[:8]
        form.slug = form.slug + '-' + hash
        form.save()

        # copy form instance and set new form
        form_instance.pk = None
        form_instance.form = form
        form_instance.version = 1
        form_instance.save()

        return HttpResponseRedirect(reverse("form_list", kwargs={"investigation_slug": kwargs["investigation_slug"]}))


class FormChangeStatus(generics.CreateAPIView):
    permission_classes = (
        IsAuthenticated, InvestigationObjectManagePermissions)

    def create(self, request, *args, **kwargs):
        investigation_slug = self.kwargs.get(
            "investigation_slug")

        form_slug = self.kwargs.get(
            "form_slug")

        investigation = get_object_or_404(
            Investigation, slug=investigation_slug)

        form = get_object_or_404(
            Form, slug=form_slug, investigation=investigation)

        # change form status
        if form.status == 'P':
            form.status = 'A'
        elif form.status == 'A':
            form.status = 'P'

        form.save()

        return HttpResponseRedirect(reverse("form_list", kwargs={"investigation_slug": kwargs["investigation_slug"]}))

class FormDetails(generics.RetrieveUpdateAPIView):
    serializer_class = FormSerializer
    queryset = Form
    lookup_field = "slug"
    lookup_url_kwarg = "form_slug"
    permission_classes = (IsAuthenticated, CanEditInvestigation)


class ResponseListPermission(DjangoObjectPermissions):
    def has_permission(self, request, view):
        form_slug = view.kwargs.get("form_slug")
        form = get_object_or_404(Form, slug=form_slug)
        investigation = form.investigation
        return request.user.has_perm("manage_investigation", investigation)


class FormResponseListSerializer(ModelSerializer):
    json = serializers.SerializerMethodField()

    class Meta:
        model = FormResponse
        fields = "__all__"

    def get_json(self, form_response):
        return {field["json_name"]: field["value"] for field in form_response.rendered_fields()}


class FormResponseList(generics.ListAPIView):
    serializer_class = FormResponseListSerializer
    permission_classes = (IsAuthenticated, ResponseListPermission)

    def get_queryset(self):
        form_slug = self.kwargs.get("form_slug")
        queryset = FormResponse.objects.filter(
            form_instance__form__slug=form_slug)
        status = self.request.query_params.get('status', None)
        if status is not None:
            queryset = queryset.filter(status=status)
        return queryset


class PresignedUrl(generics.ListAPIView):
    def get(self, request):

        file_name = request.GET.get('name')
        if file_name:
            client = Minio(
                "assets.crowdnewsroom.org",
                access_key='Cha6xai6aicheengiengaeraecahbu2u',
                secret_key='Aadethe9chaeya0taevotha0iequ9cei'
            )

            url = client.get_presigned_url(
                "PUT",
                "videos",
                file_name,
                expires=timedelta(days=1),
                response_headers={"response-content-type": "application/json"},
            )

        return Response({"url" : url})