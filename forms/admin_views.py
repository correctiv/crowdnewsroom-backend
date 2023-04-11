import base64
import re
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import (Http404, HttpResponse, HttpResponseForbidden,
                         HttpResponseRedirect)
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  TemplateView, UpdateView)
from django.views.generic.base import ContextMixin
from guardian.decorators import permission_required
from guardian.mixins import PermissionRequiredMixin
from guardian.shortcuts import get_objects_for_user
from jsonschema import FormatChecker, ValidationError, validate
from datetime import timedelta
from forms.forms import CommentDeleteForm, CommentForm
from forms.models import Comment, Form, FormResponse, Investigation, Tag, User
from forms.utils import create_form_csv
from minio import Minio


def _get_filter_params(kwargs, get_params):
    bucket = kwargs.get("bucket")
    has_filter = get_params.get("has")
    tag_filter = get_params.get("tag")
    email_filter = get_params.get("email")
    answer_filter = get_params.get("answer")
    assignee_filter = get_params.get("assignee")
    mapping = {
        "inbox": "S",
        "trash": "I",
        "verified": "V"
    }

    filter_params = {}

    if has_filter:
        filter_params["json__has_key"] = has_filter

    if tag_filter:
        filter_params["tags__id"] = tag_filter

    if email_filter:
        filter_params["json__email__icontains"] = email_filter

    if assignee_filter:
        filter_params["assignees__email"] = assignee_filter

    if answer_filter:
        filter_params["json__icontains"] = answer_filter

    filter_params["status"] = mapping.get(bucket, "S")
    return filter_params


class BreadCrumbMixin(ContextMixin):
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
    permission_required = 'view_investigation'
    return_403 = False

    def get_permission_object(self):
        return get_object_or_404(Investigation, slug=self.kwargs.get("investigation_slug"))


class FormListView(InvestigationAuthMixin, BreadCrumbMixin, ListView):
    @cached_property
    def investigation(self):
        return get_object_or_404(Investigation, slug=self.kwargs.get("investigation_slug"))

    def get_breadcrumbs(self):
        return [
            (_("Investigations"), reverse("investigation_list")),
            (self.investigation.name, reverse("form_list", kwargs={
             "investigation_slug": self.investigation.slug})),
        ]

    def get_permission_object(self):
        return self.investigation

    def get_queryset(self):
        return Form.get_all_for_investigation(self.kwargs.get("investigation_slug"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['investigation'] = self.investigation
        context['user_can_manage_investigation'] = self.request.user.has_perm("manage_investigation",
                                                                              self.investigation)
        context['user_can_admin_investigation'] = self.request.user.has_perm("admin_investigation",
                                                                             self.investigation)
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
            (self.investigation.name, reverse("form_list", kwargs={
             "investigation_slug": self.investigation.slug})),
            (self.form.name, reverse("form_responses", kwargs={"investigation_slug": self.investigation.slug,
                                                               "form_slug": self.form.slug,
                                                               "bucket": "inbox"})),
        ]

    def dispatch(self, request, *args, **kwargs):
        if not self.form.investigation == self.investigation:
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get_permission_object(self):
        return self.investigation

    def get_queryset(self):
        investigation_responses = FormResponse.get_all_for_form(self.form)
        filter_params = _get_filter_params(self.kwargs, self.request.GET)
        investigation_responses = investigation_responses.filter(
            **filter_params)
        investigation_responses = investigation_responses \
            .prefetch_related("tags") \
            .prefetch_related("assignees")
        return investigation_responses

    def _get_message(self):
        if sum(self.form.count_by_bucket().values()) == 0:
            return _("No one contributed to your investigation yet. Time to advertise!")

        active_filters = [key for key,
                          value in self.request.GET.items() if value]
        is_filtered = {'has', 'tag', 'email',
                       'assignee'}.intersection(active_filters)

        if is_filtered:
            return _("There are no results using your current filters. Maybe try something else?")

        if not self.kwargs.get("bucket") == "inbox":
            return _("There are no results in this bucket yet. Start moving some from the inbox.")

        else:
            return _("Looks like you verified or deleted all contributions. Good work!")

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['investigation'] = self.investigation
        context['form'] = self.form

        allowed_params = ['has', 'tag', 'email', 'assignee', 'answer']

        context['query_params'] = '&'.join(['{}={}'.format(k, v)
                                            for k, v
                                            in self.request.GET.items()
                                            if k in allowed_params])
        for param in allowed_params:
            value = self.request.GET.get(param)
            context['{}_param'.format(param)] = value
            if value:
                context['has_filters'] = True

        context['empty_message'] = self._get_message()

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
        context['investigation'] = self.investigation
        return context

    def get_breadcrumbs(self):
        return [
            (_("Investigations"), reverse("investigation_list")),
            (self.investigation.name, reverse("form_list", kwargs={
             "investigation_slug": self.investigation.slug})),
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
        form.save_with_extra_props(
            form_response=response, author=self.request.user)
        return super().form_valid(form)


class CommentDeleteView(InvestigationAuthMixin, UpdateView):
    model = Comment
    form_class = CommentDeleteForm
    pk_url_kwarg = "comment_id"

    def get_success_url(self):
        self.kwargs.pop("comment_id")
        return reverse("response_details", kwargs=self.kwargs)

    def form_invalid(self, form):
        self.kwargs.pop("comment_id")
        return HttpResponseRedirect(reverse("response_details", kwargs=self.kwargs))

    def get_permission_object(self):
        return Investigation.objects.get(slug=self.kwargs.get("investigation_slug"))

    def check_permissions(self, request):
        comment = self.get_object()
        if comment.author != request.user:
            raise PermissionDenied()
        return super().check_permissions(request)


@login_required(login_url="/admin/login")
@permission_required('manage_investigation', (Investigation, 'slug', 'investigation_slug'), return_403=True)
def form_response_batch_edit(request, *args, **kwargs):
    action = request.POST.get("action")
    ids = [int(id) for id in request.POST.getlist("selected_responses", [])]
    referer = request.META.get("HTTP_REFERER", "/")
    box = referer.split("/")[-1].replace("?", "")
    return_bucket = "inbox"

    if box in ["inbox", "verified", "trash"]:
        return_bucket = box

    # need to also filter for investigation to
    # make sure that we only edit responses that user is allowed to edit
    investigation = Investigation.objects.get(
        slug=kwargs["investigation_slug"])
    form_responses = FormResponse.objects.filter(id__in=ids,
                                                 form_instance__form__investigation=investigation)

    # update tags for all selected form responses
    try:
        tag_id = request.POST.get("tag")
        if tag_id == "clear_tags":
            for form_response in form_responses:
                form_response.tags.clear()
        elif tag_id:
            tag = Tag.objects.filter(
                investigation=investigation).get(id=tag_id)
            for form_response in form_responses:
                form_response.tags.add(tag)
        else:
            pass
    except ObjectDoesNotExist:
        pass

    try:
        email = request.POST.get("assignee_email")
        if email == "clear_assignees":
            for form_response in form_responses:
                form_response.assignees.clear()
        elif email != '':
            user = User.objects.get(email=email)
            if user.has_perm("manage_investigation", investigation):
                for form_response in form_responses:
                    form_response.assignees.add(user)
    except ObjectDoesNotExist:
        pass

    # update status for all selected form responses
    if action == "mark_invalid":
        form_responses.update(status="I")
        form_responses.update(last_status_changed_date=timezone.now())
    elif action == "mark_submitted":
        form_responses.update(status="S")
        form_responses.update(last_status_changed_date=timezone.now())
    elif action == "mark_verified":
        form_responses.update(status="V")
        form_responses.update(last_status_changed_date=timezone.now())

    return HttpResponseRedirect(reverse("form_responses", kwargs={"investigation_slug": kwargs["investigation_slug"],
                                                                  "form_slug": kwargs["form_slug"],
                                                                  "bucket": return_bucket}))


@login_required(login_url="/admin/login")
@permission_required('manage_investigation', (Investigation, 'slug', 'investigation_slug'), return_403=True)
def form_response_csv_view(request, *args, **kwargs):
    form_slug = kwargs.get("form_slug")
    investigation_slug = kwargs.get("investigation_slug")

    form = get_object_or_404(Form, slug=form_slug)
    if form.investigation.slug != investigation_slug:
        return HttpResponseForbidden()

    filter_params = _get_filter_params(kwargs, request.GET)

    response = HttpResponse(content_type='text/csv')
    filename = 'crowdnewsroom_download_{}_{}.csv'.format(
        investigation_slug, form_slug)
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(
        filename)

    create_form_csv(form, investigation_slug,
                    request.build_absolute_uri, response, filter_params)

    return response


def _get_file_data(file):
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
    except ValueError:
        raise Http404()

    file_type = file_type.replace("data:", "")

    file_content = base64.b64decode(content)
    return filename, file_type, file_content


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
        return HttpResponseForbidden()

    file = form_response.json.get(file_field)
    if not file:
        raise Http404()

    if file_index is not None:
        if file_index >= len(file):
            raise Http404
        file = file[file_index]

    if 'video' in file_field:
        client = Minio(
            settings.MINIO_ASSETS_URL,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY
        )
        url = client.get_presigned_url(
            "GET",
            settings.MINIO_ASSETS_BUCKET,
            file,
            expires=timedelta(hours=2),
        )

        return HttpResponseRedirect(url)

    # return url
    filename, file_type, file_content = _get_file_data(file)

    prefixed_filename = "{}-{}".format(form_response.id, filename)
    response = HttpResponse(content_type=file_type)
    response.write(file_content)
    response['Content-Disposition'] = 'inline; filename="{}"'.format(
        prefixed_filename)
    return response


@login_required(login_url="/admin/login")
@permission_required('admin_investigation', (Investigation, 'slug', 'investigation_slug'), return_403=True)
def form_response_json_edit_view(request, *args, **kwargs):
    form_slug = kwargs.get("form_slug")
    investigation_slug = kwargs.get("investigation_slug")
    response_id = kwargs.get("response_id")

    form = get_object_or_404(Form, slug=form_slug)
    if form.investigation.slug != investigation_slug:
        raise HttpResponse(status_code=403)

    pattern = re.compile("json__([\w_]+)")
    form_response = get_object_or_404(FormResponse, id=response_id)
    for key, value in request.POST.items():
        match = pattern.match(key)
        if match:
            json_key = match.group(1)
            original = form_response.json
            if json_key not in form_response.valid_keys:
                return HttpResponse(status=400)
            try:
                validate({json_key: value},
                         form_response.form_instance.flat_schema,
                         format_checker=FormatChecker())
            except ValidationError as e:
                return HttpResponse(e.message, status=400)

            original.update({json_key: value})
            form_response.json = original
            form_response.save()

    return HttpResponseRedirect(reverse("response_details", kwargs=kwargs))


class UserSettingsView(LoginRequiredMixin, BreadCrumbMixin, TemplateView):
    template_name = "forms/user_settings.html"


class InvestigationView(InvestigationAuthMixin, TemplateView, BreadCrumbMixin):
    template_name = "forms/investigation_details.html"
    permission_required = "manage_investigation"

    def get_breadcrumbs(self):
        investigation = get_object_or_404(
            Investigation, slug=self.kwargs.get("investigation_slug"))

        return [
            (_("Investigations"), reverse("investigation_list")),
            (investigation.name,
             reverse("form_list",
                     kwargs={"investigation_slug": investigation.slug})),

        ]


class InvestigationCreateView(TemplateView, BreadCrumbMixin):
    template_name = "forms/investigation_details.html"

    def get_breadcrumbs(self):
        return [
            (_("Investigations"), reverse("investigation_list")),
            (_("New Investigation"), "#"),
        ]


class InterviewerView(InvestigationAuthMixin, TemplateView, BreadCrumbMixin):
    template_name = "forms/interviewer_new.html"
    permission_required = "admin_investigation"

    def get_breadcrumbs(self):
        investigation = get_object_or_404(
            Investigation, slug=self.kwargs.get("investigation_slug"))

        form_name = _("New Form")
        form_slug = self.kwargs.get("form_slug")
        if form_slug:
            form = get_object_or_404(Form, slug=form_slug)
            form_name = form.name

        return [
            (_("Investigations"), reverse("investigation_list")),
            (investigation.name,
             reverse("form_list",
                     kwargs={"investigation_slug": investigation.slug})),
            (form_name, "#")
        ]


class InterviewerEditorView(InterviewerView):
    template_name = "forms/interviewer_new_editor.html"
    permission_required = "admin_investigation"
