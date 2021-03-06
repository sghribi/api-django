from urllib.parse import urlencode

from django import forms
from django.db.models import Count
from django.shortcuts import reverse
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.html import escape, format_html
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin.utils import display_for_value
from api.admin import admin_site
from admin_steroids.filters import AjaxFieldFilter

from .models import Person, PersonTag, PersonEmail, PersonForm
from authentication.models import Role
from events.models import RSVP
from groups.models import Membership

from front.utils import front_url, generate_token_params
from lib.search import PrefixSearchQuery
from lib.form_fields import AdminRichEditorWidget


class RSVPInline(admin.TabularInline):
    model = RSVP
    can_add = False
    fields = ('event_link',)
    readonly_fields = ('event_link',)

    def event_link(self, obj):
        return mark_safe('<a href="%s">%s</a>' % (
            reverse('admin:events_event_change', args=(obj.event.id,)),
            escape(obj.event.name)
        ))

    def has_add_permission(self, request):
        return False


class MembershipInline(admin.TabularInline):
    model = Membership
    can_add = False
    fields = ('supportgroup_link', 'is_referent', 'is_manager')
    readonly_fields = ('supportgroup_link',)

    def supportgroup_link(self, obj):
        return mark_safe('<a href="%s">%s</a>' % (
            reverse('admin:groups_supportgroup_change', args=(obj.supportgroup.id,)),
            escape(obj.supportgroup.name)
        ))

    def has_add_permission(self, request):
        return False


class EmailInline(admin.TabularInline):
    model = PersonEmail
    readonly_fields = ('address',)
    extra = 0
    fields = ('address', '_bounced', 'bounced_date')


@admin.register(Person, site=admin_site)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'contact_phone', 'subscribed', 'role_link', 'created')
    list_display_links = ('email',)

    fieldsets = (
        (None, {
            'fields': ('first_name', 'last_name', 'connection_params', 'role_link')
        }),
        (_('Dates'), {
            'fields': ('created', 'modified', 'last_login')
        }),
        (_('Paramètres mails'), {
            'fields': ('subscribed', 'event_notifications', 'group_notifications')
        }),
        (_('Paramètres de participation'), {
            'fields': ('draw_participation', )
        }),
        (_('Profil'), {
            'fields': ('gender', 'date_of_birth', 'tags')
        }),
        (_('Contact'), {
            'fields': (
                'contact_phone',
                'location_name',
                'location_address',
                'location_address1',
                'location_address2',
                'location_city',
                'location_zip',
                'location_state',
                'location_country',
            )
        }),
        (_('Meta'), {
            'fields': ('meta',)
        })
    )

    readonly_fields = ('connection_params', 'created', 'modified', 'last_login', 'role_link', 'supportgroups', 'events')

    search_fields = ('emails__address', 'first_name', 'last_name', 'location_zip')

    list_filter = (
        ('location_city', AjaxFieldFilter),
        ('location_zip', AjaxFieldFilter),
        ('tags'),
        ('subscribed', admin.BooleanFieldListFilter),
        ('draw_participation', admin.BooleanFieldListFilter),
        ('gender'),
    )

    inlines = (RSVPInline, MembershipInline, EmailInline)

    def get_search_results(self, request, queryset, search_term):
        if search_term:
            filter = PrefixSearchQuery(search_term, config='simple_unaccented')
            queryset = queryset.filter(search=filter)

        use_distinct = False

        return queryset, use_distinct

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('emails')

    def role_link(self, obj):
        return '<a href="%s">%s</a>' % (
            reverse('admin:authentication_role_change', args=[obj.role_id]),
            _('Voir le rôle')
        )
    role_link.allow_tags = True
    role_link.short_description = _('Lien vers le rôle')

    def connection_params(self, obj):
        if obj.pk:
            return urlencode(generate_token_params(obj))
        else:
            return '-'
    connection_params.short_description = _("Paramètres de connexion")
    connection_params.help_text = _("A copier/coller à la fin d'une url agir pour obtenir un lien qui connecte automatiquement.")

    def last_login(self, obj):

        if obj.role_id:
            return display_for_value(obj.role.last_login, '-')
        else:
            return '-'
    last_login.short_description = Role._meta.get_field('last_login').verbose_name


@admin.register(PersonTag, site=admin_site)
class PersonTagAdmin(admin.ModelAdmin):
    list_display = ('label', 'exported')

    actions = ('set_as_exported', 'set_as_not_exported')

    def set_as_exported(self, request, queryset):
        queryset.update(exported=True)
    set_as_exported.short_description = _('Exporter ces tags')

    def set_as_not_exported(self, request, queryset):
        queryset.update(exported=False)
    set_as_not_exported.short_description = _('Ne plus exporter')


class PersonFormForm(forms.ModelForm):
    class Meta:
        fields = '__all__'
        widgets = {'description': AdminRichEditorWidget(), 'confirmation_note': AdminRichEditorWidget()}


@admin.register(PersonForm, site=admin_site)
class PersonFormAdmin(admin.ModelAdmin):
    form = PersonFormForm
    list_display = ('title', 'slug_link', 'published',)

    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'published', 'submissions_number', 'simple_link')
        }),
        (_('Champs'), {
            'fields': ('main_question', 'tags', 'personal_information', 'additional_fields')
        }),
        (_('Textes'), {
            'fields': ('description', 'confirmation_note')
         }),
    )

    readonly_fields = ('submissions_number', 'simple_link')

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        return qs.annotate(submissions_number=Count('submissions'))

    def slug_link(self, object):
        if object.slug:
            return format_html('<a href="{}">{}</a>', front_url('view_person_form', args=(object.slug,)), object.slug)
        else:
            return '-'
    slug_link.short_description = 'Slug'

    def simple_link(self, object):
        if object.slug:
            return format_html('<a href="{0}">{0}</a>', front_url('view_person_form', args=(object.slug,)))
        else:
            return '-'
    simple_link.short_description = 'Lien vers le formulaire'

    def submissions_number(self, object):
        return object.submissions_number
    submissions_number.short_description = 'Nombre de soumissions'
