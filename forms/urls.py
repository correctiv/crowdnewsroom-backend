from django.urls import path

from forms.admin_views import InvestigationListView, FormResponseListView, FormResponseDetailView, CommentAddView, \
    FormResponseStatusView, form_response_csv_view
from forms.views import FormInstanceDetail, ApiFormResponseDetail, FormResponseCreate

urlpatterns = [
    path('investigations/<int:investigation_id>/forms/<int:form_id>', FormInstanceDetail.as_view(), name="form"),
    path('investigations/<int:investigation_id>/forms/<int:form_instance_id>/responses', FormResponseCreate.as_view(), name="form_response"),
    path('form_instances/<pk>', FormInstanceDetail.as_view()),
    path('responses/<token>', ApiFormResponseDetail.as_view()),

    path('admin/investigations', InvestigationListView.as_view(), name="investigation_list"),
    path('admin/investigations/<int:investigation_id>/responses', FormResponseListView.as_view(), name="investigation_responses"),
    path('admin/investigations/<int:investigation_id>/responses/<int:response_id>', FormResponseDetailView.as_view(), name="response_details"),
    path('admin/investigations/<int:investigation_id>/responses/<int:response_id>/comments', CommentAddView.as_view(), name="response_details_comments"),
    path('admin/investigations/<int:investigation_id>/responses/<int:response_id>/status', FormResponseStatusView.as_view(), name="response_details_status"),
    path('admin/investigations/<int:investigation_id>/forms/<int:form_id>/responses.csv', form_response_csv_view, name="form_response_csv"),
]
