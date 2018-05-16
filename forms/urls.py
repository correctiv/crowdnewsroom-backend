from django.http import HttpResponseRedirect
from django.urls import path, register_converter

from forms.admin_views import InvestigationListView, FormResponseListView, FormResponseDetailView, CommentAddView, \
    FormResponseStatusView, form_response_csv_view, FormListView, form_response_file_view, FormResponseTagsView, \
    form_response_batch_edit, form_response_json_edit_view, UserSettingsView, FormResponseAssigneesView
from forms.views import FormInstanceDetail, FormResponseCreate, InvestigationDetail


class BucketConverter:
    regex = "(inbox|trash|verified)"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(BucketConverter, 'bucket')

urlpatterns = [
    path('investigations/<slug:investigation_slug>', InvestigationDetail.as_view(), name="investigation"),
    path('investigations/<slug:investigation_slug>/forms/<slug:form_slug>', FormInstanceDetail.as_view(), name="form"),
    path('investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses', FormResponseCreate.as_view(), name="form_response"),

    path('admin/investigations', InvestigationListView.as_view(), name="investigation_list"),
    path('admin/user_settings', UserSettingsView.as_view(), name="user_settings"),
    path('admin/investigations/<slug:investigation_slug>/forms', FormListView.as_view(), name="form_list"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/batch_edit', form_response_batch_edit, name="form_responses_edit"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses',
         lambda r, **kwargs: HttpResponseRedirect('./responses/inbox'),
         ),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<bucket:bucket>', FormResponseListView.as_view(), name="form_responses"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<bucket:bucket>/responses.csv', form_response_csv_view, name="form_responses_csv"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>', FormResponseDetailView.as_view(), name="response_details"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>/edit', form_response_json_edit_view, name="response_json_edit"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>/comments', CommentAddView.as_view(), name="response_details_comments"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>/tags',
         FormResponseTagsView.as_view(), name="response_details_tags"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>/assignees',
         FormResponseAssigneesView.as_view(), name="response_details_assignees"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>/status', FormResponseStatusView.as_view(), name="response_details_status"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>/files/<file_field>', form_response_file_view, name="response_file"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>/files/<file_field>/<int:file_index>', form_response_file_view, name="response_file_array"),
]
