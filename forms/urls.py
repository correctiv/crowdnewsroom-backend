from django.http import HttpResponseRedirect
from django.urls import path, register_converter

from forms.admin_views import (CommentAddView, CommentDeleteView, FormListView,
                               FormResponseDetailView, FormResponseListView,
                               InterviewerView, InterviewerEditorView,
                               InvestigationCreateView,
                               InvestigationListView, InvestigationView,
                               UserSettingsView, form_response_batch_edit,
                               form_response_csv_view, form_response_file_view,
                               form_response_json_edit_view)
from forms.views import (AssigneeList, FormCreate, FormDetails,
                         FormInstanceDetail, FormInstanceListCreate,
                         FormInstanceTemplateDetails, FormInstanceTemplateList,
                         FormResponseCreate, FormResponseDetail,
                         FormResponseList, InvestigationCreate,
                         InvestigationDetail, InvitationDetails,
                         InvitationList, TagEditDelete, TagList,
                         UserGroupMembershipDelete, UserGroupUserList,
                         UserInvitationList, UserList)


class BucketConverter:
    regex = "(inbox|trash|verified)"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(BucketConverter, 'bucket')

urlpatterns = [
    path('investigations', InvestigationCreate.as_view(), name="investigations"),
    path('investigations/<slug:investigation_slug>',
         InvestigationDetail.as_view(), name="investigation"),
    path('investigations/<slug:investigation_slug>/forms/<slug:form_slug>',
         FormInstanceDetail.as_view(), name="form"),
    path('investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses',
         FormResponseCreate.as_view(), name="form_response"),
    path('responses/<int:response_id>',
         FormResponseDetail.as_view(), name="form_response_edit"),
    path('investigations/<slug:investigation_slug>/tags',
         TagList.as_view(), name="investigation_tags"),
    path('investigations/<slug:investigation_slug>/assignees',
         AssigneeList.as_view(), name="investigation_assignees"),
    path('investigations/<slug:investigation_slug>/users',
         UserList.as_view(), name="investigation_users"),
    path('investigations/<slug:investigation_slug>/groups/<role>/users',
         UserGroupUserList.as_view(), name="user_groups"),
    path('investigations/<slug:investigation_slug>/groups/<role>/users/<int:user_id>',
         UserGroupMembershipDelete.as_view(), name="user_group_membership"),
    path('investigations/<slug:investigation_slug>/invitations',
         InvitationList.as_view(), name="invitations"),
    path('investigations/<slug:investigation_slug>/forms',
         FormCreate.as_view(), name="interviewers"),
    path('invitations/<int:invitation_id>',
         InvitationDetails.as_view(), name="invitation"),
    path('invitations', UserInvitationList.as_view(), name="user_invitations"),
    path('templates', FormInstanceTemplateList.as_view(), name="template_list"),
    path('templates/<int:pk>', FormInstanceTemplateDetails.as_view(), name="template"),
    path('tags/<int:pk>', TagEditDelete.as_view(), name="tag_details"),
    path('forms/<slug:form_slug>', FormDetails.as_view(), name="form_details"),
    path('forms/<slug:form_slug>/responses',
         FormResponseList.as_view(), name="responses"),
    path('forms/<int:form_id>/form_instances',
         FormInstanceListCreate.as_view(), name="form_forminstances"),

    path('admin/investigations', InvestigationListView.as_view(),
         name="investigation_list"),
    path('admin/user_settings', UserSettingsView.as_view(), name="user_settings"),
    path('admin/investigations/', InvestigationCreateView.as_view(),
         name="admin_investigation_new"),
    path('admin/investigations/<slug:investigation_slug>',
         InvestigationView.as_view(), name="admin_investigation"),
    path('admin/investigations/<slug:investigation_slug>/forms',
         FormListView.as_view(), name="form_list"),

    path('admin/investigations/<slug:investigation_slug>/interviewers',
         InterviewerView.as_view(), name="admin_interviewer_new"),
    path('admin/investigations/<slug:investigation_slug>/interviewers/<slug:form_slug>',
         InterviewerView.as_view(), name="admin_interviewer_edit"),
    path('admin/investigations/<slug:investigation_slug>/interviewers/<slug:form_slug>/editor',
         InterviewerEditorView.as_view(), name="admin_interviewer_edit_neweditor"),

    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/batch_edit',
         form_response_batch_edit, name="form_responses_edit"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses',
         lambda r, **kwargs: HttpResponseRedirect('./responses/inbox'),
         ),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<bucket:bucket>',
         FormResponseListView.as_view(), name="form_responses"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<bucket:bucket>/responses.csv',
         form_response_csv_view, name="form_responses_csv"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>',
         FormResponseDetailView.as_view(), name="response_details"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>/edit',
         form_response_json_edit_view, name="response_json_edit"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>/comments',
         CommentAddView.as_view(), name="response_details_comments"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>/comments/<int:comment_id>',
         CommentDeleteView.as_view(), name="comment_delete"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>/files/<file_field>',
         form_response_file_view, name="response_file"),
    path('admin/investigations/<slug:investigation_slug>/forms/<slug:form_slug>/responses/<int:response_id>/files/<file_field>/<int:file_index>',
         form_response_file_view, name="response_file_array"),
]
