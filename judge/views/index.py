from django.views.generic import DetailView, ListView
import judge.models as models
from django.contrib.contenttypes.models import ContentType
from . import mixin

class Index(ListView, mixin.TitleMixin, mixin.MetaMixin):
    template_name = 'judge/info/index.html'
    model = models.BlogPost
    context_object_name = 'posts'
    title = 'PNOJ'

    def get_ordering(self):
        return '-created'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['problems'] = models.Problem.objects.order_by('-created')[:5]
        context['comments'] = models.Comment.objects.order_by('-created_date')[:5]
        return context

class BlogPost(DetailView, mixin.TitleMixin, mixin.MetaMixin):
    model = models.BlogPost
    context_object_name = 'post'
    template_name = "judge/info/blog_post.html"
    og_type = 'article'

    def get_title(self):
        return 'PNOJ: ' + self.get_object().title

    def get_author(self):
        return self.get_object().author.all()

    def get_description(self):
        return self.get_object().text

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        blogpost_contenttype = ContentType.objects.get_for_model(models.BlogPost)
        context['comments'] = models.Comment.objects.filter(parent_content_type=blogpost_contenttype, parent_object_id=self.get_object().pk)
        return context
