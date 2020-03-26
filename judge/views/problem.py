from django.views.generic import DetailView, ListView
from .. import models
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.generic.edit import CreateView
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
import uuid
from django.core.cache import cache
from django.urls import reverse
from pnoj import settings
import logging
from pnoj.settings import k8s
from pnoj.settings import k8s_config
import json

logger = logging.getLogger('django')

class ProblemIndex(ListView):
    model = models.Problem
    context_object_name = 'problems'
    template_name = 'judge/problem_index.html'

    def get_ordering(self):
        return 'name'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sidebar_items'] = models.SidebarItem.objects.order_by('order')
        context['page_title'] = 'PNOJ: Problems'
        return context

class Problem(DetailView):
    model = models.Problem
    context_object_name = 'problem'
    template_name = "judge/problem.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sidebar_items'] = models.SidebarItem.objects.order_by('order')
        context['page_title'] = 'PNOJ: ' + self.get_object().name
        problem_contenttype = ContentType.objects.get_for_model(models.Problem)
        context['comments'] = models.Comment.objects.filter(parent_content_type=problem_contenttype, parent_object_id=self.get_object().pk)
        return context

def create_judge_job(submission_id, problem_file_url, submission_file_url, callback_url, language, memory_limit):
    # Configureate Pod template container
    resource_config = {'memory': str(memory_limit) + "Mi", 'cpu': settings.cpu_limit}
    resource = k8s.client.V1ResourceRequirements(requests=resource_config, limits=resource_config)
    # securityCapabilties = k8s.client.V1Capabilities(add=["NET_RAW"])
    # securityContext = k8s.client.V1SecurityContext(capabilities=securityCapabilties)
    container = k8s.client.V1Container(
        name="judge-container-{0}".format(submission_id),
        image=settings.languages[language]['docker_image'],
        args=['--submission_file_url', submission_file_url, '--problem_file_url', problem_file_url, '--callback_url', callback_url],
        resources=resource,
        # security_context=securityContext)
        )
    # Create and configurate a spec section
    template = k8s.client.V1PodTemplateSpec(
        metadata=k8s.client.V1ObjectMeta(labels={"app": "pnoj"}),
        spec=k8s.client.V1PodSpec(restart_policy="Never", containers=[container], runtime_class_name="gvisor"))
        # spec=k8s.client.V1PodSpec(restart_policy="Never", containers=[container]))
    # Create the specification of deployment
    spec = k8s.client.V1JobSpec(
        template=template,
	active_deadline_seconds=1800,
	ttl_seconds_after_finished=3600,
        backoff_limit=4)
    # Instantiate the job object
    job = k8s.client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=k8s.client.V1ObjectMeta(name="judge-job-{0}".format(submission_id)),
        spec=spec)

    api_instance = k8s.client.BatchV1Api(k8s.client.ApiClient(k8s_config))
    api_response = api_instance.create_namespaced_job(
        body=job,
        namespace="pnoj")

@method_decorator(login_required, name='dispatch')
class ProblemSubmit(CreateView):
    template_name = 'judge/problem_submit.html'
    model = models.Submission
    fields = ('source', 'language')

    def form_valid(self, form, **kwargs):
        model = form.save(commit=False)
        model.author = self.request.user
        model.problem = models.Problem.objects.get(slug=self.kwargs['slug'])
        model.status = 'MD'
        model.save()

        callback_uuid = uuid.uuid4().hex
        cache.set('callback-{0}'.format(callback_uuid), model.pk, 1800)
        callback_url = self.request.build_absolute_uri(reverse('callback', kwargs={'uuid': callback_uuid}))
        submission_file_url = self.request.build_absolute_uri(model.source.url)
        problem_file_url = self.request.build_absolute_uri(model.problem.problem_file.url)
        if hasattr(settings, 'override_callback_url'):
            logger.info("Callback url for submission #{0}: {1}".format(model.pk, callback_url))
            callback_url = settings.override_callback_url.format(callback_uuid)
        if hasattr(settings, 'override_submission_file_url'):
            logger.info("Submission file url for submission #{0}: {1}".format(model.pk, submission_file_url))
            submission_file_url = settings.override_submission_file_url.format(model.problem.slug, model.language)
        if hasattr(settings, 'override_problem_file_url'):
            logger.info("Problem file url for submission #{0}: {1}".format(model.pk, problem_file_url))
            problem_file_url = settings.override_problem_file_url.format(model.problem.slug)
        create_judge_job(model.pk, problem_file_url, submission_file_url, callback_url, model.language, model.problem.memory_limit * 2)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sidebar_items'] = models.SidebarItem.objects.order_by('order')
        context['problem'] = models.Problem.objects.get(slug=self.kwargs['slug'])
        context['page_title'] = 'PNOJ: Submit to ' + context['problem'].name
        return context

@csrf_exempt
@require_POST
def callback(request, uuid):
    submission_pk = cache.get("callback-{0}".format(uuid))

    result = json.loads(request.body)

    logger.info(result)

    submission = models.Submission.objects.get(pk=submission_pk)
    if 'score' in result and result['score']['scoreable'] != None:
        submission.scored = result['score']['scored']
        submission.scoreable = result['score']['scoreable']
        submission.points = (result['score']['scored']/result['score']['scoreable'])*submission.problem.points
    else:
        submission.points = 0
    submission.status = result['status']
    if 'resource' in result:
        submission.time = result['resource']['time']
        submission.memory = result['resource']['memory']
    if 'message' in result and not result['message'] == None:
        submission.message = result['message']

    submission.save()

    for batch_result in result['batches']:
        batch = models.SubmissionBatchResult()
        batch.name = batch_result['name']
        batch.submission = submission
        if 'message' in batch_result and not batch_result['message'] == None:
            batch.message = batch_result['message']
        batch.scored = batch_result['score']['scored']
        batch.scoreable = batch_result['score']['scoreable']
        batch.status = batch_result['status']
        if 'resource' in batch_result:
            batch.time = batch_result['resource']['time']
            batch.memory = batch_result['resource']['memory']
        batch.save()
        for testcase_result in batch_result['testcases']:
            testcase = models.SubmissionTestcaseResult()
            testcase.name = testcase_result['name']
            testcase.submission = submission
            testcase.batch = batch
            if 'message' in testcase_result and not testcase_result['message'] == None:
                testcase.message = testcase_result['message']
            testcase.status = testcase_result['status']
            if 'resource' in testcase_result:
                testcase.time = testcase_result['resource']['time']
                testcase.memory = testcase_result['resource']['memory']
            testcase.save()

    submission.author.save()
    return HttpResponse("OK")

class ProblemAllSubmissions(ListView):
    context_object_name = "submissions"
    template_name = 'judge/submission_list.html'
    paginate_by = 50

    def get_queryset(self):
        self.problem = get_object_or_404(models.Problem, slug=self.kwargs['slug'])
        return models.Submission.objects.filter(problem=self.problem).order_by(self.get_ordering())

    def get_ordering(self):
        return '-created'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sidebar_items'] = models.SidebarItem.objects.order_by('order')
        context['purpose'] = 'problem_all_submissions'
        context['problem'] = self.problem
        context['page_title'] = 'PNOJ: All Submissions for Problem ' + self.problem.name
        return context

class ProblemBestSubmissions(ListView):
    context_object_name = "submissions"
    template_name = 'judge/submission_list.html'
    paginate_by = 50

    def get_queryset(self):
        self.problem = get_object_or_404(models.Problem, slug=self.kwargs['slug'])
        return models.Submission.objects.filter(problem=self.problem).order_by(self.get_ordering())

    def get_ordering(self):
        return '-points'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sidebar_items'] = models.SidebarItem.objects.order_by('order')
        context['purpose'] = 'problem_best_submissions'
        context['problem'] = self.problem
        context['page_title'] = 'PNOJ: Best Submissions for Problem ' + self.problem.name
        return context