import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from guardian.shortcuts import get_objects_for_user
from rest_framework import generics, serializers
from rest_framework.serializers import ModelSerializer

from .models import FormResponse, FormInstance, Investigation


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
        return FormInstance.get_latest_for_form(form_slug)


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


class ApiFormResponseDetail(generics.UpdateAPIView):
    queryset = FormResponse
    serializer_class = FormResponseSerializer
    lookup_field = "id"


class FormResponseListCreate(generics.ListCreateAPIView):
    queryset = FormResponse
    serializer_class = FormResponseSerializer

    def get_queryset(self):
        responses = get_objects_for_user(self.request.user, "edit_response", FormResponse)
        responses = responses.filter(form_instance__form_slug=self.kwargs["form_slug"])
        return responses

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def check_object_permissions(self, request, obj):
        has_permission = request.user.has_perm("edit_response", obj)
        if not has_permission:
            self.permission_denied(
                request, message='NOT allowed!'
            )


def user_detail_view(*args, **kwargs):
    try:
        UserModel = get_user_model()
        UserModel.objects.get(email=kwargs.get("email"))
        return JsonResponse({"exists": True})
    except ObjectDoesNotExist:
        return JsonResponse({"exists": False}, status=404)
