from django.forms import ModelForm, Textarea
from django.utils import timezone

from forms.models import Comment
from django.utils.translation import ugettext_lazy as _


class CommentForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].widget = Textarea(attrs={'rows': 2,
                                                     'class': 'bx--text-area bx--text-area--v2',
                                                     'placeholder': _('Add a comment')})

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
