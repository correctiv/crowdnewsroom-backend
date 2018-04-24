from django.forms import ModelForm, MultipleChoiceField, CheckboxSelectMultiple
from django.utils import timezone

from forms.models import Comment, FormResponse


class CommentForm(ModelForm):
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


class FormResponseStatusForm(ModelForm):
    class Meta:
        model = FormResponse
        fields = ["status"]


class FormResponseTagsForm(ModelForm):

    class Meta:
        model = FormResponse
        fields = ["tags"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tags'].widget = CheckboxSelectMultiple()
        self.fields['tags'].queryset = self.instance.taglist
