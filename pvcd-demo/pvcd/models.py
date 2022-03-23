from pvcd_demo.celery import app
from pvcd.storage import ReferenceStorage, QueryStorage
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from datetime import datetime, timedelta
from utils import filename
import requests
import os


class Query(models.Model):
    video = models.FileField(upload_to=filename.uploaded_date,
                             storage=QueryStorage)
    _video = models.FileField(storage=QueryStorage)
    thumbnail = models.ImageField(storage=QueryStorage)

    name = models.CharField(max_length=128)
    feature = models.FileField(storage=QueryStorage, null=True)
    metadata = models.JSONField(null=True)

    # detect
    topk = models.IntegerField(default=100)
    window = models.IntegerField(default=10, validators=[MinValueValidator(1)])
    score_threshold = models.FloatField(default=0.8, validators=[MaxValueValidator(1.), MinValueValidator(0.)])
    match_threshold = models.IntegerField(default=3, validators=[MinValueValidator(1)])

    uploaded_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)


class Result(models.Model):
    rank = models.IntegerField()
    query = models.ForeignKey('Query', related_name='results', on_delete=models.CASCADE)
    query_start = models.IntegerField(null=True)
    query_end = models.IntegerField(null=True)
    reference = models.ForeignKey('Reference', on_delete=models.DO_NOTHING)
    reference_start = models.IntegerField(null=True)
    reference_end = models.IntegerField(null=True)
    score = models.FloatField(null=True)
    match = models.IntegerField(null=True)


class Reference(models.Model):
    video = models.FileField(upload_to=filename.default,
                             storage=ReferenceStorage,
                             max_length=256)
    name = models.CharField(max_length=256)
    _video = models.FileField(storage=ReferenceStorage, max_length=256)
    thumbnail = models.ImageField(storage=ReferenceStorage, max_length=256)
    poster = models.ImageField(storage=ReferenceStorage, max_length=256)
    feature = models.FileField(storage=ReferenceStorage, max_length=256)
    metadata = models.JSONField(null=True)

    def check_status(self):
        print('====')
        print(self.id)
        print(self.name)
        print(ReferenceStorage.exists(self.video.name), 111, self.video.name, )
        print(ReferenceStorage.exists(self._video.name), 222, self._video.name, )
        print(ReferenceStorage.exists(self.thumbnail.name), 333, self.thumbnail.name, )
        print(ReferenceStorage.exists(self.feature.name), 444, self.feature.name, self.feature)

        print('==============')
