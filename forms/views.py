import datetime

from rest_framework import generics, mixins
from rest_framework.serializers import ModelSerializer

from .models import FormResponse, FormInstance


class FormSerializer(ModelSerializer):
    class Meta:
        model = FormInstance
        fields = "__all__"


class FormInstanceDetail(generics.RetrieveAPIView):
    serializer_class = FormSerializer
    lookup_url_kwarg = "form_id"

    def get_object(self, *args, **kwargs):
        form_id = self.kwargs.get("form_id")
        return FormInstance.get_latest_for_form(form_id)


class FormResponseSerializer(ModelSerializer):
    class Meta:
        model = FormResponse
        fields = "__all__"
        read_only_fields = ("submission_date", "form_instance")


class FormResponseCreateSerializer(ModelSerializer):
    class Meta:
        model = FormResponse
        fields = ("json", "email")

    def create(self, validated_data, *args, **kwargs):
        fr = FormResponse(**validated_data)
        fr.submission_date = datetime.datetime.now()
        # TODO: There must be a better way to do this than the following line
        fr.form_instance_id = self.context['request'].parser_context["kwargs"]["form_instance_id"]
        fr.save()
        return fr


class ApiFormResponseDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = FormResponse
    serializer_class = FormResponseSerializer
    lookup_field = "token"


class FormResponseCreate(mixins.CreateModelMixin, generics.GenericAPIView):
    queryset = FormResponse
    serializer_class = FormResponseCreateSerializer

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)
