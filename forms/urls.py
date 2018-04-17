from django.urls import path

from forms.admin_views import InvestigationListView, FormResponseListView, FormResponseDetailView, CommentAddView, \
    FormResponseStatusView, form_response_csv_view, FormListView, form_response_file_view, FormResponseTagsView
from forms.views import FormInstanceDetail, FormResponseListCreate, InvestigationDetail

urlpatterns = [
    path('investigations/<slug:investigation_slug>', InvestigationDetail.as_view(), name="investigation"),
    path('investigations/<slug:investigation_slug>/forms/<slug:form_slug>', FormInstanceDetail.as_view(), name="form"),
    path('investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses', FormResponseListCreate.as_view(), name="form_response"),

    path('admin/investigations', InvestigationListView.as_view(), name="investigation_list"),
    path('admin/investigations/<slug:investigation_slug>/forms', FormListView.as_view(), name="form_list"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses', FormResponseListView.as_view(), name="form_responses"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses.csv', form_response_csv_view, name="form_responses_csv"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>', FormResponseDetailView.as_view(), name="response_details"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>/comments', CommentAddView.as_view(), name="response_details_comments"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>/tags',
         FormResponseTagsView.as_view(), name="response_details_tags"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>/status', FormResponseStatusView.as_view(), name="response_details_status"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>/files/<file_field>', form_response_file_view, name="response_file"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>/files/<file_field>', form_response_file_view, name="response_file"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>/files/<file_field>/<int:file_index>', form_response_file_view, name="response_file_array"),
]
