from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html, escape
from django.utils.safestring import mark_safe
from django.shortcuts import reverse
from django.db.models import Count
from api.admin import admin_site
from admin_steroids.filters import AjaxFieldFilter
from admin_steroids.options import CSVModelAdminMixin

from lib.admin import CenterOnFranceMixin
from front.utils import front_url
from . import models


class MembershipInline(admin.TabularInline):
    model = models.Membership
    can_add = False
    fields = ('person_link', 'is_referent', 'is_manager')
    readonly_fields = ('person_link',)

    def person_link(self, obj):
        return mark_safe('<a href="%s">%s</a>' % (
            reverse('admin:people_person_change', args=(obj.person.id,)),
            escape(obj.person.email)
        ))

    def has_add_permission(self, request):
        return False


@admin.register(models.SupportGroup, site=admin_site)
class SupportGroupAdmin(CSVModelAdminMixin, CenterOnFranceMixin, OSMGeoAdmin):

    # CSVModelAdminMixin get_actions is buggy, overwritten here
    def get_actions(self, request):
        if hasattr(self, 'actions') and isinstance(self.actions, list):
            self.actions.append('csv_export')
        return super(OSMGeoAdmin, self).get_actions(request)

    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'link', 'created', 'modified')
        }),
        (_('Informations'), {
            'fields': ('description', 'tags', 'published')
        }),
        (_('Lieu'), {
            'fields': ('location_name', 'location_address1', 'location_address2', 'location_city', 'location_zip',
                       'location_state', 'location_country', 'coordinates', 'coordinates_type')
        }),
        (_('Contact'), {
            'fields': ('contact_name', 'contact_email', 'contact_phone')
        }),
        (_('NationBuilder'), {
            'fields': ('nb_id', 'nb_path',)
        }),
    )
    inlines = (MembershipInline,)
    readonly_fields = ('id', 'link', 'created', 'modified', 'coordinates_type')
    date_hierarchy = 'created'

    list_display = ('name', 'published', 'location_short', 'membership_count', 'created', 'referent')
    list_filter = (
        ('location_city', AjaxFieldFilter),
        ('location_zip', AjaxFieldFilter),
        'published',
    )

    search_fields = ('name', 'description', 'location_city', 'location_country')

    def referent(self, object):
        referent = object.memberships.filter(is_referent=True).first()
        if (referent):
            return referent.person.email

        return ''
    referent.short_description = _('Animateurice')

    def location_short(self, object):
        return _('{zip} {city}, {country}').format(
            zip=object.location_zip,
            city=object.location_city,
            country=object.location_country.name
        )
    location_short.short_description = _("Lieu")
    location_short.admin_order_field = 'location_zip'

    def membership_count(self, object):
        return object.membership_count
    membership_count.short_description = _("Nombre de membres")
    membership_count.admin_order_field = 'membership_count'

    def link(self, object):
        return format_html('<a href="{0}">{0}</a>', front_url('view_group', kwargs={'pk': object.pk}))
    link.short_description = _("Page sur le site")

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        return qs.annotate(membership_count=Count('memberships'))


@admin.register(models.SupportGroupTag, site=admin_site)
class SupportGroupTagAdmin(admin.ModelAdmin):
    pass
