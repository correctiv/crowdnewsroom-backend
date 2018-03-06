import csv

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.utils.functional import cached_property
from guardian.decorators import permission_required
from guardian.mixins import PermissionRequiredMixin
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from guardian.shortcuts import get_objects_for_user
from django.utils.translation import gettext as _

from forms.forms import CommentForm, FormResponseStatusForm
from forms.models import FormResponse, Investigation, Comment, FormInstance, Form
from forms.utils import create_form_csv


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


class FormListView(PermissionRequiredMixin, LoginRequiredMixin, BreadCrumbMixin, ListView):
    permission_required = 'forms.view_investigation'
    return_403 = True

    @cached_property
    def investigation(self):
        return get_object_or_404(Investigation, id=self.kwargs.get("investigation_id"))

    def get_breadcrumbs(self):
        return [
            (_("Investigations"), reverse("investigation_list")),
            (self.investigation.name, reverse("form_list", kwargs={"investigation_id": self.investigation.id})),
        ]

    def get_permission_object(self):
        return self.investigation

    def get_queryset(self):
        return Form.get_all_for_investigation(self.kwargs.get("investigation_id"))

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['investigation'] = self.investigation
        return context


class FormResponseListView(PermissionRequiredMixin, LoginRequiredMixin, BreadCrumbMixin, ListView):
    permission_required = 'forms.view_investigation'
    return_403 = True

    @cached_property
    def investigation(self):
        return get_object_or_404(Investigation, id=self.kwargs.get("investigation_id"))

    @cached_property
    def form(self):
        return get_object_or_404(Form, id=self.kwargs.get("form_id"))

    def get_breadcrumbs(self):
        return [
            (_("Investigations"), reverse("investigation_list")),
            (self.investigation.name, reverse("form_list", kwargs={"investigation_id": self.investigation.id})),
            (self.form.name, reverse("form_responses", kwargs={"investigation_id": self.investigation.id,
                                                               "form_id": self.form.id})),
        ]

    def get_permission_object(self):
        return self.investigation

    def get_queryset(self):
        return FormResponse.get_all_for_investigation(self.kwargs.get("investigation_id"))

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['investigation'] = self.investigation
        context['form'] = self.form
        return context


class FormResponseDetailView(PermissionRequiredMixin, LoginRequiredMixin, BreadCrumbMixin, DetailView):
    permission_required = 'forms.view_investigation'
    return_403 = True
    model = FormResponse
    pk_url_kwarg = "response_id"

    @cached_property
    def investigation(self):
        return get_object_or_404(Investigation, id=self.kwargs.get("investigation_id"))

    @cached_property
    def form(self):
        return get_object_or_404(Form, id=self.kwargs.get("form_id"))

    def get_permission_object(self):
        return self.investigation

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
        return [
            (_("Investigations"), reverse("investigation_list")),
            (self.investigation.name, reverse("form_list", kwargs={"investigation_id": self.investigation.id})),
            (self.form.name, reverse("form_responses", kwargs={"investigation_id": self.investigation.id,
                                                               "form_id": self.form.id})),
            (_("This response"), reverse("response_details", kwargs={"investigation_id": self.investigation.id,
                                                                     "form_id": self.form.id,
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



