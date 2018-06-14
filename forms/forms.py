from django.forms import ModelForm, CheckboxSelectMultiple, Textarea
from django.utils import timezone

from forms.models import Comment, FormResponse, User


class CommentForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].widget = Textarea(attrs={'rows': 2, 'class': 'w-100'})

    class Meta:
        model = Comment
        fields = ["text"]

    def save_with_extra_props(self, **kwargs):
        # TODO: Extract this to a mixin
        comment = self.save(commit=False)
        comment.date = timezone.now()
        for (key, value) in kwargs.items():
            comment.__setattr__(key, value)
        comment.save()


class CommentDeleteForm(ModelForm):
    class Meta:
        model = Comment
        fields = ["archived", "text"]


class FormResponseStatusForm(ModelForm):
    class Meta:
        model = FormResponse
        fields = ["status"]

    def save_with_extra_props(self, **kwargs):
        form_response_status = self.save(commit=False)
        form_response_status.last_status_changed_date = timezone.now()
        for (key, value) in kwargs.items():
            form_response_status.__setattr__(key, value)
        form_response_status.save()


class FormResponseTagsForm(ModelForm):

    class Meta:
        model = FormResponse
        fields = ["tags"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tags'].widget = CheckboxSelectMultiple()
        self.fields['tags'].queryset = self.instance.taglist


class FormResponseAssigneesForm(ModelForm):
    class Meta:
        model = FormResponse
        fields = ["assignees"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assignees'].widget = CheckboxSelectMultiple()

        form_response = self.instance  # type: FormResponse
        investigation_users = form_response.form_instance.form.investigation.manager_users
        # We already have a list of all the users here but Django expects us to pass
        # a queryset to the form, not a list of objects so we manually create
        # that query here.
        self.fields['assignees'].queryset = User.objects.filter(id__in=[user.id for user in investigation_users])
