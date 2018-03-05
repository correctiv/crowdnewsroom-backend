import csv

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic.detail import SingleObjectMixin
from guardian.mixins import PermissionRequiredMixin
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from guardian.shortcuts import get_objects_for_user
from django.utils.translation import gettext as _


from forms.forms import CommentForm, FormResponseStatusForm
from forms.models import FormResponse, Investigation, Comment, FormInstance


class BreadCrumbMixin(object):
    def get_breadcrumbs(self):
        return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = self.get_breadcrumbs()
        return context


class InvestigationListView(ListView, LoginRequiredMixin):
    def get_queryset(self):
        return get_objects_for_user(self.request.user, 'view_investigation', Investigation)


class FormResponseListView(PermissionRequiredMixin, LoginRequiredMixin, BreadCrumbMixin, ListView):
    permission_required = 'forms.view_investigation'
    return_403 = True

    def get_breadcrumbs(self):
        investigation = self.get_permission_object()
        return [
            (_("Investigations"), reverse("investigation_list")),
            (investigation.name, reverse("investigation_responses", kwargs={"investigation_id": investigation.id})),
        ]

    def get_permission_object(self):
        return Investigation.objects.get(id=self.kwargs.get("investigation_id"))

    def get_queryset(self):
        return FormResponse.get_all_for_investigation(self.kwargs.get("investigation_id"))

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        investigation = get_object_or_404(Investigation, id=self.kwargs.get("investigation_id"))
        context['investigation'] = investigation
        return context


class FormResponseDetailView(PermissionRequiredMixin, LoginRequiredMixin, BreadCrumbMixin, DetailView):
    permission_required = 'forms.view_investigation'
    return_403 = True
    model = FormResponse
    pk_url_kwarg = "response_id"

    def get_permission_object(self):
        return Investigation.objects.get(id=self.kwargs.get("investigation_id"))

    def dispatch(self, request, *args, **kwargs):
        form_response_id = self.kwargs[self.pk_url_kwarg]
        investigation_id = self.kwargs["investigation_id"]
        if not FormResponse.belongs_to_investigation(form_response_id, investigation_id):
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment_form'] = CommentForm()
        context['status_form'] = FormResponseStatusForm(instance=self.object)
        return context

    def get_breadcrumbs(self):
        investigation = Investigation.objects.get(id=self.kwargs.get("investigation_id"))
        return [
            (_("Investigations"), reverse("investigation_list")),
            (investigation.name, reverse("investigation_responses", kwargs={"investigation_id": investigation.id})),
            (_("This response"), reverse("response_details", kwargs={"investigation_id": investigation.id,
                                                                     "response_id": self.object.id})),
        ]


class CommentAddView(PermissionRequiredMixin, LoginRequiredMixin, CreateView):
    permission_required = 'forms.view_investigation'
    return_403 = True
    model = Comment
    form_class = CommentForm

    def get_success_url(self):
        return reverse("response_details", kwargs=self.kwargs)

    def get_permission_object(self):
        return Investigation.objects.get(id=self.kwargs.get("investigation_id"))

    def form_valid(self, form):
        response = FormResponse.objects.get(id=self.kwargs.get("response_id"))
        form.save_with_extra_props(form_response=response, author=self.request.user)
        return super().form_valid(form)


class FormResponseStatusView(PermissionRequiredMixin, LoginRequiredMixin, UpdateView):
    permission_required = 'forms.manage_investigation'
    return_403 = True
    model = FormResponse
    form_class = FormResponseStatusForm
    pk_url_kwarg = "response_id"

    def get_success_url(self):
        return reverse("response_details", kwargs=self.kwargs)

    def get_permission_object(self):
        return Investigation.objects.get(id=self.kwargs.get("investigation_id"))


def form_response_csv_view(request, *args, **kwargs):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="somefilename.csv"'

    form_instance = FormInstance.get_latest_for_form(kwargs.get("form_id"))
    form_instance = FormInstance.objects.get(id=1)
    responses = FormResponse.objects.filter(form_instance=form_instance).all()

    keys = set(form_instance.form_json["properties"].keys())
    file_keys = {key for (key, value)
                 in form_instance.ui_schema_json.items()
                 if key != "ui:order" and value.get("ui:widget") in ['signatureWidget', 'fileWidget']}
    writer = csv.DictWriter(response, fieldnames=keys-file_keys, extrasaction='ignore')
    for form_response in responses:
        try:
            writer.writerow(form_response.json["formData"])
        except TypeError:
            print("Skipping row")
        except KeyError:
            print("Skipping row")

    return response

