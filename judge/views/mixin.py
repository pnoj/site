from .. import models
from django.views.generic.base import ContextMixin
from django.views.generic.list import MultipleObjectMixin
from django.contrib.sites.models import Site
from django.templatetags.static import static
from django.contrib.auth import get_user_model
from pnoj import settings
import random

User = get_user_model()

class TitleMixin(ContextMixin):
    title = ''

    def get_title(self):
        return self.title

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.get_title()
        return context

class MetaMixin(ContextMixin):
    og_type = 'website'
    description = settings.description
    og_image = None
    meta_payment_pointers = settings.payment_pointers

    def get_description(self):
        return self.description

    def get_og_image(self):
        return self.og_image

    def get_author(self):
        return models.User.objects.none()

    def get_payment_pointers(self):
        authors = self.get_author()
        author_payment_pointers = [author.payment_pointer for author in authors if author.payment_pointer]
        if author_payment_pointers:
            return author_payment_pointers
        else:
            return self.meta_payment_pointers

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context['site'] = Site.objects.get_current()
        context['og_type'] = self.og_type
        description = self.get_description().replace('\n', ' ').split('. ')
        summary = description[0]
        for i in range(1, len(description)):
            if len('. '.join(description[:i])) > 160:
                summary = '. '.join(description[:max(i-1, 1)])
                break
        summary = summary[:min(len(summary), 160)].strip(' .!?') + "."
        context['meta_description'] = summary
        context['og_image'] = self.get_og_image()
        payment_pointers = self.get_payment_pointers()
        if payment_pointers:
            context['meta_payment_pointer'] = random.choice(payment_pointers)
        return context
