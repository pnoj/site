from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import pytz
import random
import pnoj.settings as settings
from django.contrib.auth.models import AbstractUser
from django.db.models import Sum
import uuid
import zipfile
import yaml

# Create your models here.

status_choices = [
    ('AC', 'Accepted'),
    ('WA', 'Wrong Answer'),
    ('TLE', 'Time Limit Exceeded'),
    ('MLE', 'Memory Limit Exceeded'),
    ('OLE', 'Output Limit Exceeded'),
    ('IR', 'Invalid Return'),
    ('IE', 'Internal Error'),
    ('AB', 'Aborted'),
]

class User(AbstractUser):
    email = models.EmailField(unique=True)
    description = models.TextField(blank=True)

    timezone_choices = [(i, i) for i in pytz.common_timezones]
    timezone = models.CharField(max_length=50, choices=timezone_choices, default="UTC")

    main_language_choices = [(i['code'], i['name']) for i in settings.languages]
    main_language = models.CharField(max_length=10, choices=main_language_choices, default='py3')

    registered_date = models.DateTimeField(auto_now_add=True)

    organizations = models.ManyToManyField('Organization', blank=True)

    points = models.FloatField(default=0)
    num_problems_solved = models.PositiveIntegerField(default=0)

    # def update_stats(self):
    #     problems = Problem.objects.filter(author__exact=self).order_by()
    #     points = problems.aggregate(Sum('points'))
    #     num_problems = problems.filter().count()


class Organization(models.Model):
    creator = models.ForeignKey(User, on_delete=models.PROTECT, related_name="organizations_owning")
    admins = models.ManyToManyField('User', related_name="organizations_maintaining")
    name = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    slug = models.SlugField(unique=True)
    
    is_private = models.BooleanField(default=False)

class Category(models.Model):
    name = models.CharField(max_length=12)
    description = models.TextField(blank=True)
    slug = models.SlugField(unique=True)
    class Meta:
        abstract = True

class ProblemCategory(Category):
    pass

class ProblemType(Category):
    pass

def problem_file_path(instance, filename):
    ext = filename.split(".")[-1]
    uuid_hex = uuid.uuid4().hex
    return "problems/{0}.{1}".format(uuid_hex, ext)

class Problem(models.Model):
    problem_file = models.FileField(upload_to=problem_file_path, unique=True)
    manifest = models.TextField()

    author = models.ManyToManyField(User, related_name="problems_authored", blank=True)
    name = models.CharField(max_length=128)
    description = models.TextField()
    slug = models.SlugField(unique=True)

    points = models.PositiveSmallIntegerField()
    is_partial = models.BooleanField()
    time_limit = models.FloatField()
    memory_limit = models.FloatField()

    category = models.ManyToManyField(ProblemCategory, blank=True)
    problem_type = models.ManyToManyField(ProblemType, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        with zipfile.ZipFile(self.problem_file.file) as z:
            with z.open('manifest.yaml') as manifest_file:
                self.manifest = manifest_file.read()
            manifest_dict = yaml.safe_load(self.manifest)        

            self.name = manifest_dict['name']

            with z.open(manifest_dict['metadata']['description']) as description_file:
                self.description = description_file.read()

            self.points = manifest_dict['metadata']['points']
            self.is_partial = manifest_dict['metadata']['partial']

            self.time_limit = manifest_dict['metadata']['limit']['time']
            self.memory_limit = manifest_dict['metadata']['limit']['memory']
            
        super().save(*args, **kwargs)  # Call the "real" save() method.

        authors = User.objects.filter(username__in=manifest_dict['author'])
        self.author.set(authors)

        categories = ProblemCategory.objects.filter(name__in=manifest_dict['metadata']['category'])
        self.category.set(categories)
        problem_types = ProblemType.objects.filter(name__in=manifest_dict['metadata']['type'])
        self.problem_type.set(problem_types)

        super().save(*args, **kwargs)  # Call the "real" save() method.

class Submission(models.Model):
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    message = models.TextField(blank=True)

    scored = models.PositiveSmallIntegerField()
    scoreable = models.PositiveSmallIntegerField()

    points = models.FloatField()

    time = models.FloatField()
    memory = models.FloatField()

    source = models.FileField(upload_to="submissions/")

    status = models.CharField(max_length=4, choices=status_choices)

class SubmissionBatchResult(models.Model):
    name = models.CharField(max_length=20)
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    message = models.TextField(blank=True)

    scored = models.PositiveSmallIntegerField()
    scoreable = models.PositiveSmallIntegerField()

    status = models.CharField(max_length=4, choices=status_choices)

    time = models.FloatField()
    memory = models.FloatField()

class SubmissionTestcaseResult(models.Model):
    name = models.CharField(max_length=20)
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    batch = models.ForeignKey(SubmissionBatchResult, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    message = models.TextField(blank=True)

    status = models.CharField(max_length=4, choices=status_choices)

    time = models.FloatField()
    memory = models.FloatField()

class Comment(models.Model):
    parent_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    parent_object_id = models.PositiveIntegerField()
    parent = GenericForeignKey('parent_content_type', 'parent_object_id')

    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_date = models.DateTimeField(auto_now_add=True)

    text = models.TextField()

class SidebarItem(models.Model):
    name = models.CharField(max_length=24)
    view = models.CharField(max_length=36)
    order = models.PositiveSmallIntegerField()

    def __str__(self):
        return self.name
