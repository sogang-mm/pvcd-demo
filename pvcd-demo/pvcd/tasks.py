from pvcd_demo.celery import app
from pvcd.storage import ReferenceStorage
from pvcd.models import Reference, Query

from django.core import serializers
from billiard import current_process
import threading




def print_worker(task):
    def wrapped(*args, **kwargs):
        worker = current_process().name
        thread = threading.currentThread().getName()
        print(f"Run: {task.__name__}, Worker: {worker}/{thread}")
        return task(*args, **kwargs)

    wrapped.__name__ = task.__name__
    return wrapped


@app.task
@print_worker
def update_reference_video_async(pk, result):
    r = Reference.objects.get(id=pk)

    r.feature = r.feature.storage.path_to_name(result['feature'])
    r.thumbnail = r.feature.storage.path_to_name(result['thumbnail'])
    r.poster = r.feature.storage.path_to_name(result['poster'])
    r._video = r.feature.storage.path_to_name(result['_video'])
    r.metadata = result['metadata']

    r.save()


@app.task
@print_worker
def get_references():
    reference=Reference.objects.exclude(feature='')
    
    entry = [{'id': r.id,
              'feature': r.feature.storage.name_to_path(r.feature.path)} for r in reference if
             r.feature is not None]

    return entry
