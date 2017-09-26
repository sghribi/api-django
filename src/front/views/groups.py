from django.utils.translation import ugettext as _, ugettext_lazy
from django.views.generic import CreateView, UpdateView, ListView, DeleteView, DetailView, TemplateView
from django.contrib import messages
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy, reverse
from django.db import transaction

from groups.models import SupportGroup, Membership
from groups.tasks import send_support_group_changed_notification

from ..forms import SupportGroupForm, AddReferentForm, AddManagerForm
from ..view_mixins import LoginRequiredMixin, PermissionsRequiredMixin

__all__ = [
    "SupportGroupListView", "SupportGroupManagementView", "CreateSupportGroupView", "ModifySupportGroupView",
    "QuitSupportGroupView", 'RemoveManagerView', "SupportGroupDetailView"
]


class CheckMembershipMixin:
    def user_is_referent(self):
        return self.user_membership is not None and self.user_membership.is_referent

    def user_is_manager(self):
        return self.user_membership is not None and (self.user_membership.is_referent or self.user_membership.is_manager)

    @property
    def user_membership(self):
        if not hasattr(self, '_user_membership'):
            if isinstance(self.object, SupportGroup):
                group = self.object
            else:
                group = self.object.supportgroup

            try:
                self._user_membership = group.memberships.get(person=self.request.user.person)
            except Membership.DoesNotExist:
                self._user_membership = None

        return self._user_membership


class SupportGroupListView(LoginRequiredMixin, ListView):
    """List person support groups
    """
    paginate_by = 20
    template_name = 'front/groups/list.html'
    context_object_name = 'memberships'

    def get_queryset(self):
        return Membership.objects.filter(person=self.request.user.person) \
            .select_related('supportgroup')


class SupportGroupDetailView(DetailView):
    template_name = "front/events/detail.html"
    queryset = SupportGroup.objects.all()


class SupportGroupManagementView(LoginRequiredMixin, CheckMembershipMixin, DetailView):
    template_name = "front/groups/manage.html"
    queryset = SupportGroup.objects.all().prefetch_related('memberships')
    messages = {
        'add_referent_form': ugettext_lazy("{} est maintenant correctement signalé comme second·e référent·e"),
        'add_manager_form': ugettext_lazy("{} a bien été ajouté·e comme gestionnaire pour ce groupe"),
    }

    def get_forms(self):
        kwargs = {}

        if self.request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': self.request.POST,
            })

        return {
            'add_referent_form': AddReferentForm(self.object, **kwargs),
            'add_manager_form': AddManagerForm(self.object, **kwargs),
        }

    def get_context_data(self, **kwargs):
        referents = self.object.memberships.filter(is_referent=True).order_by('created')
        managers = self.object.memberships.filter(is_manager=True, is_referent=False).order_by('created')
        members = self.object.memberships.all().order_by('created')

        return super().get_context_data(
            referents=referents,
            managers=managers,
            members=members,
            is_referent=self.user_membership is not None and self.user_membership.is_referent,
            is_manager=self.user_membership is not None and (self.user_membership.is_referent or self.user_membership.is_manager),
            **self.get_forms()
        )

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        # only managers can access the page
        if not self.user_is_manager():
            return HttpResponseForbidden(b'Interdit')

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        # only referents can add referents and managers
        if not self.user_is_referent():
            return HttpResponseForbidden(b'Interdit')

        forms = self.get_forms()
        form_name = request.POST.get('form')
        if form_name in forms:
            form = forms[form_name]
            if form.is_valid():
                membership = form.save()

                messages.add_message(
                    request,
                    messages.SUCCESS,
                    self.messages[form_name].format(membership.person.email)
                )

        return HttpResponseRedirect(reverse("manage_group", kwargs={'pk': self.object.pk}))


class CreateSupportGroupView(LoginRequiredMixin, CreateView):
    template_name = "front/groups/create.html"
    model = SupportGroup
    form_class = SupportGroupForm

    def get_success_url(self):
        return reverse('manage_group', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("Publiez votre groupe d'appui")
        return context

    def form_valid(self, form):
        # first get response to make sure there's no error when saving the model before adding message
        with transaction.atomic():
            self.object = group = form.save()
            Membership.objects.create(
                supportgroup=group,
                person=self.request.user.person,
                is_referent=True,
                is_manager=True,
            )

        messages.add_message(
            request=self.request,
            level=messages.SUCCESS,
            message="Votre groupe a été correctement créé.",
        )

        return HttpResponseRedirect(self.get_success_url())


class ModifySupportGroupView(LoginRequiredMixin, PermissionsRequiredMixin, UpdateView):
    permissions_required = ('groups.change_supportgroup',)
    template_name = "front/groups/modify.html"
    model = SupportGroup
    form_class = SupportGroupForm

    CHANGES = {
        'name': "information",
        'contact_name': "contact",
        'contact_email': "contact",
        'contact_phone': "contact",
        'contact_hide_phone': "contact",
        'location_name': "location",
        'location_address1': "location",
        'location_address2': "location",
        'location_city': "location",
        'location_zip': "location",
        'location_country': "location",
        'description': "information"
    }

    def get_success_url(self):
        return reverse("manage_group", kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _("Modifiez votre groupe d'appui")
        return context

    def form_valid(self, form):
        # create set so that values are unique, but turns to list because set are not JSON-serializable
        changes = list({self.CHANGES[field] for field in form.changed_data if field in self.CHANGES})

        # first get response to make sure there's no error when saving the model before adding message
        res = super().form_valid(form)

        if changes and form.cleaned_data['notify']:
            send_support_group_changed_notification.delay(form.instance.pk, changes)

        messages.add_message(
            request=self.request,
            level=messages.SUCCESS,
            message="Les modifications du groupe <em>%s</em> ont été enregistrées." % self.object.name,
        )

        return res


class RemoveManagerView(LoginRequiredMixin, CheckMembershipMixin, DetailView):
    template_name = "front/confirm.html"
    queryset = Membership.objects.all().select_related('supportgroup').select_related('person')

    def get_context_data(self, **kwargs):
        person = self.object.person

        if person.first_name and person.last_name:
            name = "{} {} <{}>".format(person.first_name, person.last_name, person.email)
        else:
            name = person.email

        return super().get_context_data(
            title=_("Confirmer le retrait du gestionnaire ?"),
            message=_(f"""
            Voulez-vous vraiment retirer {name} de la liste des gestionnaires de ce groupe ?
            """),
            button_text="Confirmer le retrait"
        )

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        if not self.user_is_referent():
            return HttpResponseForbidden(b'Interdit!')

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        # user has to be referent, and target user cannot be a referent
        if not self.user_is_referent() or self.object.is_referent:
            return HttpResponseForbidden(b'Interdit')

        self.object.is_manager = False
        self.object.save()

        messages.add_message(
            request,
            messages.SUCCESS,
            _("{} n'est plus un référent du groupe.").format(self.object.person.email)
        )

        return HttpResponseRedirect(
            reverse_lazy('manage_group', kwargs={'pk': self.object.supportgroup_id})
        )


class QuitSupportGroupView(DeleteView):
    template_name = "front/groups/quit.html"
    success_url = reverse_lazy("list_groups")
    model = Membership
    context_object_name = 'membership'

    def get_object(self, queryset=None):
        try:
            return self.get_queryset().select_related('supportgroup').get(supportgroup__pk=self.kwargs['pk'])
        except Membership.DoesNotExist:
            # TODO show specific 404 page maybe?
            raise Http404()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['group'] = self.object.supportgroup
        context['success_url'] = self.get_success_url()
        return context

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()

        # make sure user is not a referent who cannot quit groups
        if self.object.is_referent:
            messages.add_message(
                request,
                messages.ERROR,
                _("Les référents ne peuvent pas quitter un groupe sans avoir abandonné leur role.")
            )

        else:
            self.object.delete()

            messages.add_message(
                request,
                messages.SUCCESS,
                _("Vous avez bien quitté le groupe <em>%s</em>" % self.object.supportgroup.name)
            )

        return HttpResponseRedirect(success_url)