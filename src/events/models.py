import os
import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import formats, timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.text import slugify
from model_utils.models import TimeStampedModel

from stdimage.models import StdImageField
from stdimage.utils import UploadToAutoSlug

from lib.models import (
    BaseAPIResource, AbstractLabel, NationBuilderResource, ContactMixin, LocationMixin, ImageMixin, DescriptionMixin,
    DescriptionField, UploadToRelatedObjectDirectoryWithUUID, UploadToInstanceDirectoryWithFilename
)
from lib.form_fields import DateTimePickerWidget

EVENT_GRACE_PERIOD = timezone.timedelta(hours=12)


def upcoming_only(as_of):
    return models.Q(end_time__gt=as_of - EVENT_GRACE_PERIOD)


def past_only(as_of):
    return models.Q(end_time__lt=as_of)


class EventQuerySet(models.QuerySet):
    def upcoming(self, as_of, published_only=True):
        condition = upcoming_only(as_of)
        if published_only:
            condition &= models.Q(published=True)

        return self.filter(condition)

    def past(self, as_of, published_only=True):
        condition = past_only(as_of)
        if published_only:
            condition &= models.Q(published=True)
        return self.filter(condition)


class RSVPQuerySet(models.QuerySet):
    def upcoming(self, as_of, published_only=True):
        condition = models.Q(event__end_time__gt=as_of - EVENT_GRACE_PERIOD)
        if published_only:
            condition &= models.Q(event__published=True)

        return self.filter(condition)


class CustomDateTimeField(models.DateTimeField):
    def formfield(self, **kwargs):
        defaults = {'widget': DateTimePickerWidget}
        defaults.update(kwargs)
        return super().formfield(**defaults)


class Event(BaseAPIResource, NationBuilderResource, LocationMixin, ImageMixin, DescriptionMixin, ContactMixin):
    """
    Model that represents an event
    """
    objects = EventQuerySet.as_manager()

    name = models.CharField(
        _("nom"),
        max_length=255,
        blank=False,
        help_text=_("Le nom de l'événement"),
    )

    published = models.BooleanField(
        _('publié'),
        default=True,
        help_text=_('L\'évenement doit-il être visible publiquement.')
    )

    nb_path = models.CharField(_('NationBuilder path'), max_length=255, blank=True)

    tags = models.ManyToManyField('EventTag', related_name='events', blank=True)

    start_time = CustomDateTimeField(_('date et heure de début'), blank=False)
    end_time = CustomDateTimeField(_('date et heure de fin'), blank=False)

    calendar = models.ForeignKey('Calendar', related_name='events', blank=False, on_delete=models.PROTECT)

    attendees = models.ManyToManyField('people.Person', related_name='events', through='RSVP')

    organizers = models.ManyToManyField('people.Person', related_name='organized_events', through="OrganizerConfig")
    organizers_groups = models.ManyToManyField('groups.SupportGroup', related_name='organized_events', through="OrganizerConfig")

    report_image = StdImageField(
        verbose_name=_('image de couverture'),
        blank=True,
        variations={
            'thumbnail': (400, 250),
            'banner': (1200, 400),
        },
        upload_to=UploadToInstanceDirectoryWithFilename('report_banner'),
        help_text=_("Cette image apparaîtra en tête de votre compte-rendu, et dans les partages que vous ferez du"
                    " compte-rendu sur les réseaux sociaux."),
    )

    report_content = DescriptionField(
        verbose_name=_("compte-rendu de l'événement"),
        blank=True,
        allowed_tags='allowed_tags',
        help_text=_("Ajoutez un compte-rendu de votre événement. N'hésitez pas à inclure des photos.")
    )

    class Meta:
        verbose_name = _('événement')
        verbose_name_plural = _('événements')
        ordering = ('-start_time', '-end_time')
        permissions = (
            # DEPRECIATED: every_event was set up as a potential solution to Rest Framework django permissions
            # Permission class default behaviour of requiring both global permissions and object permissions before
            # allowing users. Was not used in the end.s
            ('every_event', _('Peut éditer tous les événements')),
            ('view_hidden_event', _('Peut voir les événements non publiés')),
        )
        indexes = (
            models.Index(fields=['start_time', 'end_time'], name='events_datetime_index'),
            models.Index(fields=['end_time'], name='events_end_time_index'),
            models.Index(fields=['nb_path'], name='events_nb_path_index'),
        )

    def __str__(self):
        return self.name

    @property
    def participants(self):
        try:
            return self._participants
        except AttributeError:
            return self.rsvps.aggregate(participants=models.Sum(models.F('guests') + 1))['participants']

    def get_display_date(self):
        tz = timezone.get_current_timezone()
        start_time = self.start_time.astimezone(tz)
        end_time = self.end_time.astimezone(tz)

        if start_time.date() == end_time.date():
            date = formats.date_format(start_time, 'DATE_FORMAT')
            return _("le {date}, de {start_hour} à {end_hour}").format(
                date=date,
                start_hour=formats.time_format(start_time, 'TIME_FORMAT'),
                end_hour=formats.time_format(end_time, 'TIME_FORMAT')
            )

        return _("du {start_date}, {start_time} au {end_date}, {end_time}").format(
            start_date=formats.date_format(start_time, 'DATE_FORMAT'),
            start_time=formats.date_format(start_time, 'TIME_FORMAT'),
            end_date=formats.date_format(end_time, 'DATE_FORMAT'),
            end_time=formats.date_format(end_time, 'TIME_FORMAT'),
        )

    def is_past(self):
        return timezone.now() > self.end_time

    def clean(self):
        if self.start_time and self.end_time and self.end_time < self.start_time:
            raise ValidationError({
                'end_time': _("La date de fin de l'événement doit être postérieure à sa date de début.")
            })


class EventTag(AbstractLabel):
    class Meta:
        verbose_name = 'tag'


class CalendarManager(models.Manager):
    def create_calendar(self, name, slug=None, **kwargs):
        if slug is None:
            slug = slugify(name)

        return super().create(
            name=name,
            slug=slug,
            **kwargs
        )


class Calendar(NationBuilderResource, ImageMixin):
    objects = CalendarManager()

    name = models.CharField(_("titre"), max_length=255)
    slug = models.SlugField(_("slug"))

    user_contributed = models.BooleanField(_('Les utilisateurs peuvent ajouter des événements'), default=False)

    description = models.TextField(_('description'), blank=True,
                                   help_text=_("Saisissez une description (HTML accepté)"))

    image = StdImageField(
        _("bannière"),
        upload_to=UploadToAutoSlug("name", path="events/calendars/"),
        variations={
            'thumbnail': (400, 250),
            'banner': (1200, 400),
        },
        blank=True,
    )

    class Meta:
        verbose_name = 'agenda'

    def __str__(self):
        return self.name


class RSVP(TimeStampedModel):
    """
    Model that represents a RSVP for one person for an event.
    
    An additional field indicates if the person is bringing any guests with her
    """
    objects = RSVPQuerySet.as_manager()

    person = models.ForeignKey('people.Person', related_name='rsvps', on_delete=models.CASCADE, editable=False)
    event = models.ForeignKey('Event', related_name='rsvps', on_delete=models.CASCADE, editable=False)
    guests = models.PositiveIntegerField(_("nombre d'invités supplémentaires"), default=0, null=False)

    canceled = models.BooleanField(_('Annulé'), default=False)

    notifications_enabled = models.BooleanField(_('Recevoir les notifications'), default=True)

    class Meta:
        verbose_name = 'RSVP'
        verbose_name_plural = 'RSVP'
        unique_together = ('event', 'person',)
        permissions = (
            ('view_rsvp', _('Peut afficher les RSVPs')),
        )

    def __str__(self):
        return _('{person} --> {event} ({guests} invités').format(
            person=self.person, event=self.event, guests=self.guests
        )


class OrganizerConfig(models.Model):
    person = models.ForeignKey('people.Person', related_name='organizer_configs', on_delete=models.CASCADE, editable=False)
    event = models.ForeignKey('Event', related_name='organizer_configs', on_delete=models.CASCADE, editable=False)

    is_creator = models.BooleanField(_("Créateur de l'événement"), default=False)
    as_group = models.ForeignKey('groups.SupportGroup', related_name='organizer_configs', on_delete=models.CASCADE,
                                 blank=True, null=True)

    notifications_enabled = models.BooleanField(_('Recevoir les notifications'), default=True)

    def clean(self):
        super().clean()
        memberships = self.person.memberships.filter(is_manager=True).select_related('supportgroup')
        managed_groups = [membership.supportgroup for membership in memberships]
        if self.as_group not in managed_groups:
            raise ValidationError({'as_group': 'Le groupe doit être un groupe que vous gérez.'})


class EventImage(models.Model):
    event = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='images', null=False)
    author = models.ForeignKey('people.Person', related_name='event_images', on_delete=models.PROTECT, null=False)
    image = StdImageField(
        _('Fichier'),
        variations={
            'thumbnail': (200, 200, True),
        },
        upload_to=UploadToRelatedObjectDirectoryWithUUID(related='event'),
        null=False,
        blank=False,
    )
    legend = models.CharField(_('légende'), max_length=280)
