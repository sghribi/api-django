from django.db.models import Q
from django.views.generic import TemplateView

from events.models import Event
from front.view_mixins import SoftLoginRequiredMixin
from groups.models import SupportGroup


class DashboardView(SoftLoginRequiredMixin, TemplateView):
    template_name = 'front/dashboard.html'

    def get_context_data(self, **kwargs):
        person = self.request.user.person

        all_groups = SupportGroup.objects.filter(memberships__person=person)
        managed_groups = SupportGroup.objects.filter(
            Q(memberships__person=person),
            Q(memberships__is_manager=True) | Q(memberships__is_referent=True)
        )

        rsvped_events = Event.objects.filter(attendees=person)
        suggested_events = [
            (event, 'Cet événément est organisé par un groupe dont vous êtes membre.')
            for event in Event.objects.filter(Q(organizers_groups__in=person.supportgroups.all()) & ~Q(attendees=person))
        ]

        kwargs.update({
            'person': person,
            'all_groups': all_groups,
            'managed_groups': managed_groups,
            'rsvped_events': rsvped_events,
            'suggested_events': suggested_events,
        })

        return super().get_context_data(**kwargs)

