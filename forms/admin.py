from django.contrib import admin
from django.contrib.postgres import fields
from django_json_widget.widgets import JSONEditorWidget
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import ugettext_lazy as _

from .models import User, Investigation, Form, FormResponse, FormInstance, Partner, Tag, Comment


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Define admin model for custom User model with no email field."""

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)


class FormInstanceAdmin(admin.ModelAdmin):
    formfield_overrides = {
        fields.JSONField: {'widget': JSONEditorWidget}
    }


class TagInline(admin.StackedInline):
    model = Tag
    max_num = 3


class InvestigationAdmin(admin.ModelAdmin):
    list_select_related = True
    inlines = [
        TagInline,
    ]


admin.site.register(FormInstance, FormInstanceAdmin)
admin.site.register(Investigation, InvestigationAdmin)
admin.site.register(FormResponse)
admin.site.register(Partner)
admin.site.register(Form)
admin.site.register(Tag)
admin.site.register(Comment)
