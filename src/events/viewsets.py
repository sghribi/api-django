from django.db.models import Q, Sum, F
from django.db import transaction
from django.utils import timezone
from django.views.decorators.cache import cache_control
from rest_framework.viewsets import ModelViewSet
from rest_framework_extensions.mixins import NestedViewSetMixin
from rest_framework.decorators import list_route
from rest_framework.response import Response
from authentication.models import Role
import django_filters
from django_filters.rest_framework.backends import DjangoFilterBackend

from lib.permissions import PermissionsOrReadOnly, RestrictViewPermissions, DjangoModelPermissions
from lib.pagination import LegacyPaginator
from lib.filters import DistanceFilter, OrderByDistanceToBackend
from lib.views import NationBuilderViewMixin, CreationSerializerMixin

from . import serializers, models


class EventFilterSet(django_filters.rest_framework.FilterSet):
    close_to = DistanceFilter(name='coordinates', lookup_expr='distance_lte')
    after = django_filters.IsoDateTimeFilter(name='end_time', lookup_expr='gte')
    before = django_filters.IsoDateTimeFilter(name='start_time', lookup_expr='lte')
    path = django_filters.CharFilter(name='nb_path', lookup_expr='exact')
    calendar = django_filters.ModelChoiceFilter(
        name='calendar', to_field_name='slug', queryset=models.Calendar.objects.all()
    )

    class Meta:
        model = models.Event
        fields = ('contact_email', 'close_to', 'path', 'before', 'after')


class LegacyEventViewSet(NationBuilderViewMixin, ModelViewSet):
    """
    Legacy endpoint for events that imitates the endpoint from Eve Python
    """
    permission_classes = (PermissionsOrReadOnly,)
    pagination_class = LegacyPaginator
    serializer_class = serializers.LegacyEventSerializer
    filter_backends = (DjangoFilterBackend, OrderByDistanceToBackend)
    filter_class = EventFilterSet

    def get_queryset(self):
        queryset = (models.Event.objects.all()
                    .select_related('calendar')
                    .prefetch_related('tags')
                    .annotate(_participants=Sum(F('rsvps__guests') + 1))
                    )
        if not self.request.user.has_perm('events.view_hidden_event'):
            queryset = queryset.filter(published=True)

        after_query = self.request.query_params.get('after', None)
        before_query = self.request.query_params.get('before', None)
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        # in the case there is no after_query parameters, and we are not on a single object page
        # we set a default after value of today
        if lookup_url_kwarg not in self.kwargs and after_query is None and before_query is None:
            queryset = queryset.upcoming(as_of=timezone.now(), published_only=False)

        return queryset

    def perform_create(self, serializer):
        with transaction.atomic():
            event = serializer.save()

            if self.request.user.type == Role.PERSON_ROLE:
                models.OrganizerConfig.objects.create(
                    event=event,
                    person=self.request.user.person
                )

    def perform_update(self, serializer):
        with transaction.atomic():
            event = serializer.save()

            if self.request.user.type == Role.PERSON_ROLE and self.request.user.person not in event.organizers.all():
                models.OrganizerConfig.objects.create(
                    event=event,
                    person=self.request.user.person
                )

    @list_route(methods=['GET'])
    @cache_control(max_age=60, public=True)
    def summary(self, request, *args, **kwargs):
        events = self.get_queryset().filter(end_time__gt=timezone.now()).select_related('calendar')
        serializer = serializers.SummaryEventSerializer(instance=events, many=True,
                                                        context=self.get_serializer_context())
        return Response(data=serializer.data)


class CalendarViewSet(ModelViewSet):
    """
    Calendar Viewset !
    """
    serializer_class = serializers.CalendarSerializer
    queryset = models.Calendar.objects.all()
    permission_classes = (PermissionsOrReadOnly,)


class EventTagViewSet(ModelViewSet):
    """
    EventTag viewset
    """
    serializer_class = serializers.EventTagSerializer
    queryset = models.EventTag.objects.all()
    permission_classes = (PermissionsOrReadOnly,)



class RSVPViewSet(CreationSerializerMixin, ModelViewSet):
    """

    """

    def get_queryset(self):
        queryset = super(RSVPViewSet, self).get_queryset()

        if not self.request.user.has_perm('events.view_rsvp'):
            if hasattr(self.request.user, 'type') and self.request.user.type == Role.PERSON_ROLE:
                return queryset.filter(person=self.request.user.person)
            else:
                return queryset.none()
        return queryset

    serializer_class = serializers.RSVPSerializer
    creation_serializer_class = serializers.RSVPCreationSerializer
    queryset = models.RSVP.objects.select_related('event', 'person')
    permission_classes = (RestrictViewPermissions,)


class NestedRSVPViewSet(CreationSerializerMixin, NestedViewSetMixin, ModelViewSet):
    """

    """
    serializer_class = serializers.RSVPSerializer
    queryset = models.RSVP.objects.select_related('event', 'person')
    permission_classes = (RestrictViewPermissions,)
    creation_serializer_class = serializers.EventRSVPCreatableSerializer

    def get_queryset(self):
        queryset = super(NestedRSVPViewSet, self).get_queryset()

        if not self.request.user.has_perm('events.view_rsvp'):
            if hasattr(self.request.user, 'type') and self.request.user.type == Role.PERSON_ROLE:
                return queryset.filter(
                    Q(person=self.request.user.person) | Q(event__organizers=self.request.user.person))
            else:
                return queryset.none()
        return queryset

    def get_serializer_context(self):
        parents_query_dict = self.get_parents_query_dict()
        context = super(NestedRSVPViewSet, self).get_serializer_context()
        context.update(parents_query_dict)
        return context

    @list_route(methods=['PUT'], permission_classes=(DjangoModelPermissions,))
    def bulk(self, request, *args, **kwargs):
        parents_query_dict = self.get_parents_query_dict()
        rsvps = models.RSVP.objects.filter(**parents_query_dict)

        context = self.get_serializer_context()
        context.update(parents_query_dict)

        serializer = serializers.EventRSVPBulkSerializer(rsvps, data=request.data, many=True, context=context)
        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(serializer.data)
