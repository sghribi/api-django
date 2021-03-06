from django import forms
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from crispy_forms.helper import FormHelper

from groups.models import SupportGroup
from ..form_components import *
from ..form_mixins import LocationFormMixin, ContactFormMixin, GeocodingBaseForm

from events.models import Event, OrganizerConfig, Calendar, RSVP, EventImage
from events.tasks import send_event_creation_notification, send_event_changed_notification
from lib.tasks import geocode_event
from lib.form_fields import AcceptCreativeCommonsLicenceField

__all__ = ['EventForm', 'AddOrganizerForm', 'EventGeocodingForm', 'EventReportForm', 'UploadEventImageForm']


class AgendaChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.name


class EventForm(LocationFormMixin, ContactFormMixin, forms.ModelForm):
    CHANGES = {
        'name': "information",
        'start_time': "timing",
        'end_time': "timing",
        'contact_name': "contact",
        'contact_email': "contact",
        'contact_phone': "contact",
        'location_name': "location",
        'location_address1': "location",
        'location_address2': "location",
        'location_city': "location",
        'location_zip': "location",
        'location_country': "location",
        'description': "information"
    }

    image_accept_license = AcceptCreativeCommonsLicenceField()

    def __init__(self, *args, person, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)

        self.person = person

        calendar_field = []

        self.fields['image'].help_text = _("""
        Vous pouvez ajouter une image de bannière à votre événement : elle apparaîtra alors sur la page de votre
        événement, et comme illustration si vous le partagez sur les réseaux sociaux. Pour cela, choisissez une image
        à peu près deux fois plus large que haute, et de dimensions supérieures à 1200 par 630 pixels.
        """)

        self.fields['description'].help_text = _("""
        Cette description doit permettre de comprendre rapidement sur quoi porte et comment se passera votre événement.
        Incluez toutes les informations pratiques qui pourraient être utiles aux insoumis⋅es qui souhaiteraient
        participer (matériel à amener, précisions sur le lieu ou contraintes particulières, par exemple).
        """)

        if not hasattr(self.instance, 'calendar') or self.instance.calendar.user_contributed:
            self.fields['calendar'] = AgendaChoiceField(
                Calendar.objects.filter(user_contributed=True),
                empty_label=None,
                label=_("Type d'événement"),
                required=True,
                widget=forms.RadioSelect()
            )

            calendar_field = [Row(FullCol('calendar'))]

        self.fields['as_group'] = forms.ModelChoiceField(
            queryset=SupportGroup.objects.filter(memberships__person=person, memberships__is_manager=True),
            empty_label="Ne pas créer au nom d'un groupe",
            label=_("Créer l'événement au nom d'un groupe d'action"),
            required=False,
        )

        self.fields['name'].label = "Nom de l'événement"
        self.fields['name'].help_text = None

        self.is_creation = self.instance._state.adding

        if not self.is_creation:
            self.fields['notify'] = forms.BooleanField(
                required=False,
                initial=False,
                label=_("Signalez ces changements aux participants à l'événement"),
                help_text=_("Un email sera envoyé à la validation de ce formulaire. Merci de ne pas abuser de cette"
                            " fonctionnalité.")
            )
            notify_field = [Row(
                FullCol('notify')
            )]
            self.organizer_config = OrganizerConfig.objects.get(person=self.person, event=self.instance)
            self.fields['as_group'].initial = self.organizer_config.as_group
        else:
            notify_field = []

        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.add_input(Submit('submit', 'Sauvegarder et publier'))

        self.helper.layout = Layout(
            Row(
                FullCol('name'),
            ),
            Row(
                FullCol('image'),
            ),
            Row(
                FullCol('image_accept_license')
            ),
            *calendar_field,
            Row(
                HalfCol('start_time'),
                HalfCol('end_time'),
            ),
            Row(
                HalfCol('as_group')
            ),
            Section(
                _('Informations de contact'),
                Row(
                    FullCol('contact_name'),
                ),
                Row(
                    HalfCol('contact_email'),
                    HalfCol('contact_phone', 'contact_hide_phone'),
                ),
            ),
            Section(
                _('Lieu'),
                Row(
                    FullCol(
                        HTML(
                            "<p><b>Merci d'indiquer une adresse précise avec numéro de rue, sans quoi l'événement n'apparaîtra"
                            " pas sur la carte.</b>"
                            " Si les réunions se déroulent chez vous et que vous ne souhaitez pas rendre cette adresse"
                            " publique, vous pouvez indiquer un endroit à proximité, comme un café, ou votre mairie.",
                        ),
                    )
                ),
                Row(
                    FullCol('location_name', css_class='col-md-12'),
                ),
                Row(
                    FullCol(
                        Field('location_address1', placeholder=_('1ère ligne')),
                        Field('location_address2', placeholder=_('2ème ligne'))
                    )
                ),
                Row(
                    Div('location_zip', css_class='col-md-4'),
                    Div('location_city', css_class='col-md-8'),
                ),
                Row(
                    Div('location_country', css_class='col-md-12'),
                ),  
            ),
            Row(FullCol('description')),
            *notify_field,
        )

    def clean_start_time(self):
        start_time = self.cleaned_data['start_time']

        if start_time < timezone.now():
            raise forms.ValidationError(
                _("Vos événements feraient mieux de se passer dans le futur ! Ce serait plus efficace…")
            )

        return start_time

    def clean(self):
        cleaned_data = super().clean()

        image = cleaned_data['image']
        image_accept_license = cleaned_data['image_accept_license']

        if not image:
            cleaned_data['image_accept_license'] = False
        elif not image_accept_license:
            self.add_error('image_accept_license', self.fields['image_accept_license'].error_messages['required'])

        return cleaned_data

    def save(self, commit=True):
        res = super().save(commit)

        if commit:
            self.schedule_tasks()

        return res

    def _save_m2m(self):
        if self.is_creation:
            self.organizer_config = OrganizerConfig.objects.create(
                person=self.person,
                event=self.instance,
                as_group=self.cleaned_data['as_group'],
            )
            RSVP.objects.create(
                person=self.person,
                event=self.instance
            )
        elif self.organizer_config.as_group != self.cleaned_data['as_group']:
            self.organizer_config.as_group = self.cleaned_data['as_group']
            self.organizer_config.save()

    def schedule_tasks(self):
        # create set so that values are unique, but turns to list because set are not JSON-serializable
        changes = list({self.CHANGES[field] for field in self.changed_data if field in self.CHANGES})
        address_changed = any(f in self.instance.GEOCODING_FIELDS for f in self.changed_data)

        # if it's a new group creation, send the confirmation notification and geolocate it
        if self.is_creation:
            # membership attribute created by _save_m2m
            send_event_creation_notification.delay(self.organizer_config.pk)
            geocode_event.delay(self.instance.pk)
        else:
            # send changes notification if the notify checkbox was checked
            if changes and self.cleaned_data.get('notify'):
                send_event_changed_notification.delay(self.instance.pk, changes)
            # also geocode again if location has changed
            if address_changed and self.instance.should_relocate_when_address_changed():
                geocode_event.delay(self.instance.pk)

    class Meta:
        model = Event
        fields = (
            'name', 'image', 'start_time', 'end_time', 'calendar',
            'contact_name', 'contact_email', 'contact_phone', 'contact_hide_phone',
            'location_name', 'location_address1', 'location_address2', 'location_city', 'location_zip',
            'location_country',
            'description'
        )


class RSVPChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return str(obj.person)


class AddOrganizerForm(forms.Form):
    form = forms.CharField(initial="add_organizer_form", widget=forms.HiddenInput())

    def __init__(self, event, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = event

        self.fields['organizer'] = RSVPChoiceField(
            queryset=event.rsvps.exclude(person__organized_events=event), label=False
        )

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', _('Ajouter comme co-organisateur')))

    def save(self, commit=True):
        rsvp = self.cleaned_data['organizer']

        organizer_config = OrganizerConfig(
            event=rsvp.event,
            person=rsvp.person
        )

        if commit:
            organizer_config.save()

        return organizer_config


class EventGeocodingForm(GeocodingBaseForm):
    geocoding_task = geocode_event
    messages = {
        'use_geocoding': _("La localisation de votre événement sur la carte va être réinitialisée à partir de son adresse."
                           " Patientez quelques minutes pour voir la nouvelle localisation apparaître."),
        'coordinates_updated': _("La localisation de votre événement a été correctement mise à jour. Patientez quelques"
                                 " minutes pour la voir apparaître sur la carte.")
    }

    class Meta:
        model = Event
        fields = ('coordinates',)


class EventReportForm(forms.ModelForm):
    accept_license = AcceptCreativeCommonsLicenceField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['report_image'].label = 'Image de couverture (optionnelle)'

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', _('Sauvegarder et publier')))
        self.helper.layout = Layout(
            'report_content',
            'report_image',
            'accept_license',
        )

    def clean(self):
        cleaned_data = super().clean()
        report_image = cleaned_data['report_image']
        accept_license = cleaned_data['accept_license']

        if report_image and not accept_license:
            self.add_error('accept_license', self.fields['accept_license'].error_messages['required'])

        return cleaned_data

    class Meta:
        model = Event
        fields = ('report_image', 'report_content')


class UploadEventImageForm(forms.ModelForm):
    accept_license = AcceptCreativeCommonsLicenceField(required=True)

    def __init__(self, *args, author=None, event=None, **kwargs):
        super().__init__(*args, **kwargs)
        if author is not None:
            self.instance.author = author
        if event is not None:
            self.instance.event = event

        self.helper = FormHelper()
        self.helper.add_input(Submit('submit', _('Ajouter mon image')))
        self.helper.layout = Layout(
            'image',
            'accept_license',
            'legend',
        )

    class Meta:
        model = EventImage
        fields = ('image', 'legend')