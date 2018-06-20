import datetime

from django.http import Http404
from django.utils import timezone
from rest_framework import generics, permissions, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import DjangoObjectPermissions
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import ModelSerializer

from .models import FormResponse, FormInstance, Investigation, Tag, User


class InvestigationSerializer(ModelSerializer):
    class Meta:
        model = Investigation
        fields = "__all__"


class InvestigationDetail(generics.RetrieveAPIView):
    # TODO: This should filter to make sure to only return
    # Investigations that are published and not in draft or unlisted state
    queryset = Investigation
    serializer_class = InvestigationSerializer
    lookup_url_kwarg = "investigation_slug"
    lookup_field = "slug"


class FormSerializer(ModelSerializer):
    class Meta:
        model = FormInstance
        fields = "__all__"


class FormInstanceDetail(generics.RetrieveAPIView):
    serializer_class = FormSerializer
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
    if isinstance(instance, FormResponse):
        return instance.form_instance.form.investigation


class CanEditInvestigation(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        investigation = get_investigation(obj)
        return request.user.has_perm("manage_investigation", investigation)


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


class InvestigationListAPIView(generics.ListAPIView):
    def list(self, request, *args, **kwargs):
        investigation = Investigation.objects.get(slug=self.kwargs.get("investigation_slug"))
        if not request.user.has_perm("view_investigation", investigation):
            raise PermissionDenied(detail="not allowed!")
        return super().list(request, *args, **kwargs)


class TagSerializer(ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"


class TagList(InvestigationListAPIView):
    serializer_class = TagSerializer

    def get_queryset(self):
        investigation = Investigation.objects.get(slug=self.kwargs.get("investigation_slug"))
        return Tag.objects.filter(investigation=investigation).all()


class AssigneeSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "id")


class AssigneeList(InvestigationListAPIView):
    serializer_class = AssigneeSerializer

    def get_queryset(self):
        investigation = Investigation.objects.get(slug=self.kwargs.get("investigation_slug"))
        investigation_users = investigation.manager_users
        # We already have a list of all the users here but Django expects us to pass
        # a queryset to the form, not a list of objects so we manually create
        # that query here.
        return User.objects.filter(id__in=[user.id for user in investigation_users])


class FormResponseCreate(generics.CreateAPIView):
    queryset = FormResponse
    serializer_class = FormResponseSerializer
