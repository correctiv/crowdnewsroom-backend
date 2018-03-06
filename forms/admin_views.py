import csv

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic.detail import SingleObjectMixin
from guardian.decorators import permission_required
from guardian.mixins import PermissionRequiredMixin
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from guardian.shortcuts import get_objects_for_user
from django.utils.translation import gettext as _

from forms.forms import CommentForm, FormResponseStatusForm
from forms.models import FormResponse, Investigation, Comment, FormInstance, Form


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


@login_required(login_url="/admin/login")
@permission_required('forms.view_investigation', (Investigation, 'id', 'investigation_id'), return_403=True)
def form_response_csv_view(request, *args, **kwargs):
    form_id = kwargs.get("form_id")
    investigation_id = kwargs.get("investigation_id")

    form = get_object_or_404(Form, id=form_id)
    if form.investigation_id != investigation_id:
        raise HttpResponse(status_code=403)

    response = HttpResponse(content_type='text/csv')
    filename = 'crowdnewsroom_download_{}_{}.csv'.format(investigation_id, form_id)
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)

    create_form_csv(form_id, investigation_id, request, response)

    return response


def create_form_csv(form_id, investigation_id, request, io_object):
    form_instances = FormInstance.objects.filter(form_id=form_id)
    responses = FormResponse.objects.filter(form_instance__form_id=form_id).all()

    fields = []
    for instance in form_instances:
        fields += get_keys(instance)

    writer = csv.DictWriter(io_object, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    for form_response in responses:
        try:
            row = form_response.json["formData"]
            path = reverse("response_details", kwargs={"investigation_id": investigation_id,
                                                       "response_id": form_response.id})
            url = request.build_absolute_uri(path)
            meta_data = {"meta_version": form_response.form_instance.version,
                         "meta_url": url,
                         "meta_status": form_response.get_status_display(),
                         "meta_email": form_response.email,
                         "meta_submission_date": form_response.submission_date}
            row.update(meta_data)
            writer.writerow(row)

        except TypeError:
            print("Skipping row")
        except KeyError:
            print("Skipping row")


def get_keys(form_instance):
    keys = set(form_instance.form_json["properties"].keys())
    file_keys = _get_file_keys(form_instance)
    non_file_fields = list(keys - file_keys)
    extra_fields = ["url", "version", "status", "email", "submission_date"]
    fields = non_file_fields + ["meta_{}".format(field) for field in extra_fields]
    return fields


def _get_file_keys(form_instance):
    file_widgets = ['signatureWidget', 'fileWidget']
    non_property_keys = ["ui:order"]
    return {key for (key, value)
            in form_instance.ui_schema_json.items()
            if key not in non_property_keys
            and value.get("ui:widget") in file_widgets}
