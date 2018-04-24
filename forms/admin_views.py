import base64
import re

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.utils.functional import cached_property
from guardian.decorators import permission_required
from guardian.mixins import PermissionRequiredMixin
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from guardian.shortcuts import get_objects_for_user
from django.utils.translation import gettext as _

from forms.forms import CommentForm, FormResponseStatusForm
from forms.models import FormResponse, Investigation, Comment, Form
from forms.utils import create_form_csv


def _get_filter_params(kwargs, get_params):
    bucket = kwargs.get("bucket") or get_params.get("bucket")
    has_filter = get_params.get("has")
    mapping = {
        "inbox": "S",
        "trash": "I",
        "verified": "V"
    }

    filter_params = {}

    if has_filter:
        key = "json__{}__isnull".format(has_filter)
        filter_params[key] = False

    filter_params["status"] = mapping.get(bucket, "S")
    return filter_params


class BreadCrumbMixin(object):
    def get_breadcrumbs(self):
        return []

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['breadcrumbs'] = self.get_breadcrumbs()
        return context


class InvestigationListView(LoginRequiredMixin, BreadCrumbMixin, ListView):
    def get_breadcrumbs(self):
        return [
            (_("Investigations"), reverse("investigation_list")),
        ]

    def get_queryset(self):
        return get_objects_for_user(self.request.user, 'view_investigation', Investigation)


class InvestigationAuthMixin(PermissionRequiredMixin, LoginRequiredMixin):
    permission_required = 'forms.view_investigation'
    return_403 = True


class FormListView(InvestigationAuthMixin, BreadCrumbMixin, ListView):
    @cached_property
    def investigation(self):
        return get_object_or_404(Investigation, slug=self.kwargs.get("investigation_slug"))

    def get_breadcrumbs(self):
        return [
            (_("Investigations"), reverse("investigation_list")),
            (self.investigation.name, reverse("form_list", kwargs={"investigation_slug": self.investigation.slug})),
        ]

    def get_permission_object(self):
        return self.investigation

    def get_queryset(self):
        return Form.get_all_for_investigation(self.kwargs.get("investigation_slug"))

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['investigation'] = self.investigation
        return context


class FormResponseListView(InvestigationAuthMixin, BreadCrumbMixin, ListView):
    paginate_by = 25

    @cached_property
    def investigation(self):
        return get_object_or_404(Investigation, slug=self.kwargs.get("investigation_slug"))

    @cached_property
    def form(self):
        return get_object_or_404(Form, slug=self.kwargs.get("form_slug"))

    def get_breadcrumbs(self):
        return [
            (_("Investigations"), reverse("investigation_list")),
            (self.investigation.name, reverse("form_list", kwargs={"investigation_slug": self.investigation.slug})),
            (self.form.name, reverse("form_responses", kwargs={"investigation_slug": self.investigation.slug,
                                                               "form_slug": self.form.slug,
                                                               "bucket": "inbox"})),
        ]

    def get_permission_object(self):
        return self.investigation

    def get_queryset(self):
        investigation_responses = FormResponse.get_all_for_investigation(self.kwargs.get("investigation_slug"))
        filter_params = _get_filter_params(self.kwargs, self.request.GET)
        investigation_responses = investigation_responses.filter(**filter_params)
        return investigation_responses

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['investigation'] = self.investigation
        context['form'] = self.form

        allowed_params = ['has']

        context['query_params'] = '&'.join(['{}={}'.format(k, v)
                                            for k, v
                                            in self.request.GET.items()
                                            if k in allowed_params])
        context['has_param'] = self.request.GET.get('has')

        csv_base = reverse("form_responses_csv", kwargs={
            "investigation_slug": self.investigation.slug,
            "form_slug": self.form.slug,
            "bucket": self.kwargs.get("bucket")
        })

        context['csv_url'] = "{}?{}".format(csv_base, context['query_params'])
        return context


class FormResponseDetailView(InvestigationAuthMixin, BreadCrumbMixin, DetailView):
    model = FormResponse
    pk_url_kwarg = "response_id"

    @cached_property
    def investigation(self):
        return get_object_or_404(Investigation, slug=self.kwargs.get("investigation_slug"))

    @cached_property
    def form(self):
        return get_object_or_404(Form, slug=self.kwargs.get("form_slug"))

    def get_permission_object(self):
        return self.investigation

    def dispatch(self, request, *args, **kwargs):
        form_response_id = self.kwargs[self.pk_url_kwarg]
        investigation_slug = self.kwargs["investigation_slug"]
        form_response = get_object_or_404(FormResponse, id=form_response_id)
        if not form_response.belongs_to_investigation(investigation_slug):
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment_form'] = CommentForm()
        context['status_form'] = FormResponseStatusForm(instance=self.object)
        context['investigation'] = self.investigation
        return context

    def get_breadcrumbs(self):
        return [
            (_("Investigations"), reverse("investigation_list")),
            (self.investigation.name, reverse("form_list", kwargs={"investigation_slug": self.investigation.slug})),
            (self.form.name, reverse("form_responses", kwargs={"investigation_slug": self.investigation.slug,
                                                               "form_slug": self.form.slug,
                                                               "bucket": "inbox"})),
            (self.object.json_email, reverse("response_details", kwargs={"investigation_slug": self.investigation.slug,
                                                                         "form_slug": self.form.slug,
                                                                         "response_id": self.object.id})),
        ]


class CommentAddView(InvestigationAuthMixin, CreateView):
    model = Comment
    form_class = CommentForm

    def get_success_url(self):
        return reverse("response_details", kwargs=self.kwargs)

    def get_permission_object(self):
        return Investigation.objects.get(slug=self.kwargs.get("investigation_slug"))

    def form_valid(self, form):
        response = FormResponse.objects.get(id=self.kwargs.get("response_id"))
        form.save_with_extra_props(form_response=response, author=self.request.user)
        return super().form_valid(form)


@login_required(login_url="/admin/login")
@permission_required('forms.view_investigation', (Investigation, 'slug', 'investigation_slug'), return_403=True)
def form_response_batch_edit(request, *args, **kwargs):
    action = request.POST.get("action")
    ids = [int(id) for id in request.POST.getlist("selected_responses", [])]
    referer = request.META.get("HTTP_REFERER", "/")
    box = referer.split("/")[-1]
    return_bucket = "inbox"
    if box in ["inbox", "verified", "trash"]:
        return_bucket = box
    investigation = Investigation.objects.get(slug=kwargs["investigation_slug"])

    # need to also filter for investigation to
    # make sure that we only edit responses that user is allowed to edit
    form_responses = FormResponse.objects.filter(id__in=ids,
                                                 form_instance__form__investigation=investigation)
    if action == "mark_invalid":
        form_responses.update(status="I")
    elif action == "mark_submitted":
        form_responses.update(status="S")
    elif action == "mark_verified":
        form_responses.update(status="V")
    return HttpResponseRedirect(reverse("form_responses", kwargs={"investigation_slug": kwargs["investigation_slug"],
                                                                  "form_slug": kwargs["form_slug"],
                                                                  "bucket": return_bucket}))


class FormResponseStatusView(InvestigationAuthMixin, UpdateView):
    model = FormResponse
    form_class = FormResponseStatusForm
    pk_url_kwarg = "response_id"

    def get_success_url(self):
        self.kwargs.update(bucket="inbox")
        kwargs = self.kwargs
        kwargs.pop("response_id")
        return reverse("form_responses", kwargs=kwargs)

    def get_permission_object(self):
        return Investigation.objects.get(slug=self.kwargs.get("investigation_slug"))


@login_required(login_url="/admin/login")
@permission_required('forms.view_investigation', (Investigation, 'slug', 'investigation_slug'), return_403=True)
def form_response_csv_view(request, *args, **kwargs):
    form_slug = kwargs.get("form_slug")
    investigation_slug = kwargs.get("investigation_slug")

    form = get_object_or_404(Form, slug=form_slug)
    if form.investigation.slug != investigation_slug:
        raise HttpResponse(status_code=403)

    filter_params = _get_filter_params(kwargs, request.GET)

    response = HttpResponse(content_type='text/csv')
    filename = 'crowdnewsroom_download_{}_{}.csv'.format(investigation_slug, form_slug)
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)

    create_form_csv(form, investigation_slug, request.build_absolute_uri, response, filter_params)

    return response


@login_required(login_url="/admin/login")
@permission_required('forms.view_investigation', (Investigation, 'slug', 'investigation_slug'), return_403=True)
def form_response_file_view(request, *args, **kwargs):
    form_slug = kwargs.get("form_slug")
    investigation_slug = kwargs.get("investigation_slug")
    response_id = kwargs.get("response_id")
    file_field = kwargs.get("file_field")
    file_index = kwargs.get("file_index")

    form = get_object_or_404(Form, slug=form_slug)
    form_response = get_object_or_404(FormResponse, id=response_id)
    if form.investigation.slug != investigation_slug or form_response.form_instance.form != form:
        raise HttpResponse(status_code=403)

    file = form_response.json.get(file_field)
    if not file:
        raise Http404()

    if file_index is not None:
        if file_index >= len(file):
            raise Http404
        file = file[file_index]

    try:
        header, content = file.split(";base64,")
        if ";name=" in header:
            file_type, filename = header.split(";name=")
        # TODO: It is probably not safe here to assume that this is
        # always going to be a signature. Maybe check the uiSchema
        # to make sure.
        else:
            file_type = header
            filename = "signature.png"
    except AttributeError:
        raise Http404()

    response = HttpResponse(content_type=file_type)
    response.write(base64.b64decode(content))
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    return response
