import hashlib
import hmac

import qrcode
from django.conf import settings
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import list_route, detail_route
import django_filters

from front.utils import generate_token_params
from lib.pagination import LegacyPaginator
from lib.permissions import RestrictViewPermissions
from lib.views import NationBuilderViewMixin
from authentication.models import Role
from people.tasks import send_welcome_mail

from . import serializers, models


class PeopleFilter(django_filters.rest_framework.FilterSet):
    email = django_filters.CharFilter(name='emails__address')

    class Meta:
        model = models.Person
        fields = ['tags']


class LegacyPersonViewSet(NationBuilderViewMixin, ModelViewSet):
    """
    Legacy endpoint for people that imitates the endpoint from Eve Python
    """
    pagination_class = LegacyPaginator
    queryset = models.Person.objects.all()
    permission_classes = (RestrictViewPermissions, )
    filter_class = PeopleFilter

    @detail_route()
    def qrcode(self, request, pk=None):
        signature = hmac.new(
            key=settings.PROMO_CODE_KEY,
            msg=pk.encode('utf-8'),
            digestmod=hashlib.sha1
        ).hexdigest()
        img = qrcode.make(pk + '.' + signature)
        response = HttpResponse(content_type='image/png')
        img.save(response, "PNG")

        return response

    @list_route()
    def me(self, request):
        self.kwargs['pk'] = self.request.user.person.pk
        return self.retrieve(request)

    @list_route(methods=['POST'])
    def subscribe(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        send_welcome_mail.delay(serializer.instance.id)
        headers = self.get_success_headers(serializer.data)
        return Response(generate_token_params(serializer.instance), status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):
        if not ('pk' in self.kwargs or self.request.user.has_perm('people.view_person')):
            if hasattr(self.request.user, 'type') and self.request.user.type == Role.PERSON_ROLE:
                return self.queryset.filter(pk=self.request.user.person.pk)
            else:
                return self.queryset.none()
        return super(LegacyPersonViewSet, self).get_queryset()

    def get_serializer_class(self):
        if not self.request.user.has_perm('people.view_person'):
            return serializers.LegacyUnprivilegedPersonSerializer
        return serializers.LegacyPersonSerializer


class PersonTagViewSet(ModelViewSet):
    """
    Endpoint for person tags
    """
    serializer_class = serializers.PersonTagSerializer
    queryset = models.PersonTag.objects.all()
    permission_classes = (RestrictViewPermissions, )
