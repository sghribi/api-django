from rest_framework import serializers

from lib.serializers import LegacyBaseAPISerializer, LegacyLocationMixin, RelatedLabelField
from clients.serializers import PersonAuthorizationSerializer

from . import models


class LegacyPersonSerializer(LegacyLocationMixin, LegacyBaseAPISerializer):
    tags = RelatedLabelField(
        many=True,
        required=False,
        queryset=models.PersonTag.objects.all()
    )

    email_opt_in = serializers.BooleanField(
        source='subscribed',
        required=False,
    )
    rsvps = serializers.HyperlinkedRelatedField(
        view_name='legacy:rsvp-detail',
        read_only=True,
        many=True
    )
    groups = serializers.PrimaryKeyRelatedField(
        read_only=True,
        many=True,
        source='supportgroups'
    )
    memberships = serializers.HyperlinkedRelatedField(
        view_name='legacy:membership-detail',
        read_only=True,
        many=True
    )

    authorizations = PersonAuthorizationSerializer(
        many=True,
        required=False
    )

    class Meta:
        model = models.Person
        fields = (
            'url', '_id', 'id', 'email', 'first_name', 'last_name', 'bounced', 'bounced_date', '_created', '_updated',
            'email_opt_in', 'events', 'rsvps', 'groups', 'memberships', 'tags', 'location', 'authorizations',
        )
        read_only_fields = ('url', '_id', '_created', '_updated')
        extra_kwargs = {
            'url': {'view_name': 'legacy:person-detail',}
        }


class PersonTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PersonTag
        fields = ('url', 'id', 'label', 'description')
