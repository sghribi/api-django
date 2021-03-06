from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ViewSet, ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import list_route
from rest_framework.permissions import DjangoModelPermissionsOrAnonReadOnly

from lib.pagination import LegacyPaginator
from lib.permissions import RestrictViewPermissions, HasSpecificPermissions
from authentication.models import Role

from . import serializers, models
from .scopes import scopes, Scope


class HasViewClientPermission(HasSpecificPermissions):
    permissions = ['clients.view_client']


class LegacyClientViewSet(ModelViewSet):
    permission_classes = (RestrictViewPermissions,)
    serializer_class = serializers.LegacyClientSerializer
    queryset = models.Client.objects.all()
    pagination_class = LegacyPaginator

    def get_queryset(self):
        if not self.request.user.has_perm('clients.view_client'):
            if hasattr(self.request.user, 'type') and self.request.user.type == Role.CLIENT_ROLE:
                return self.queryset.filter(pk=self.request.user.client.pk)
            else:
                return self.queryset.none()
        return super(LegacyClientViewSet, self).get_queryset()

    def get_object(self):
        """
        Returns the object the view is displaying.

        You may want to override this if you need to provide non-standard
        queryset lookups.  Eg if objects are referenced using multiple
        keyword arguments in the url conf.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        assert lookup_url_kwarg in self.kwargs, (
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (self.__class__.__name__, lookup_url_kwarg)
        )

        try:
            obj = queryset.get(**{self.lookup_field: self.kwargs[lookup_url_kwarg]})
        except (ObjectDoesNotExist, ValidationError, TypeError, ValueError):
            obj = get_object_or_404(queryset, label=self.kwargs[lookup_url_kwarg])

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj


    @list_route(methods=["POST"], permission_classes=[HasViewClientPermission])
    def authenticate_client(self, request):
        input_serializer = serializers.ClientAuthenticationSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        client = input_serializer.validated_data['client']

        # the serializer needs the request in the context to generate the URLs
        context = self.get_serializer_context()
        output_serializer = serializers.LegacyClientSerializer(instance=client, context=context)

        return Response(output_serializer.data)


class ScopeViewSet(ViewSet):
    permission_classes = []

    def list(self, request):
        output_serializer = serializers.ScopeSerializer(scopes, many=True)
        return Response(output_serializer.data)

    def retrieve(self, request, pk=None):
        scope = scopes[[scope.name for scope in scopes].index(pk)]
        output_serializer = serializers.ScopeSerializer(scope)
        return Response(output_serializer.data)


class AuthorizationViewSet(ModelViewSet):
    permission_classes = (RestrictViewPermissions, )
    serializer_class = serializers.AuthorizationSerializer
    queryset = models.Authorization.objects.all()

    def get_queryset(self):
        if not self.request.user.has_perm('clients.view_authorization'):
            if hasattr(self.request.user, 'type') and self.request.user.type == Role.PERSON_ROLE:
                return self.queryset.filter(person_id=self.request.user.person.pk)
            else:
                return self.queryset.none()
        return super(AuthorizationViewSet, self).get_queryset()
