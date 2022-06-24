import os
import sys

from celery import Celery
from celery.signals import worker_init, worker_process_init, worker_ready
from billiard import current_process
from kombu import Queue
from kombu.common import Broadcast
import threading

from search.engine import Engine

from pathlib import Path

app = Celery('worker-search',
             broker='amqp://user:user@rabbitmq',
             backend='redis://pvcd-demo_redis:6379/3')

app.conf.update(
    task_serializer="pickle",
    accept_content=['pickle', "json"],
    result_serializer="pickle",
)

app.conf.task_queues = (
    Queue('search', 'pvcd', routing_key='search_tasks'),
)


def print_worker(task):
    def wrapped(*args, **kwargs):
        worker = current_process().name
        thread = threading.currentThread().getName()
        print(f"Run: {task.__name__}, Worker({worker}), Thread({thread})")
        return task(*args, **kwargs)

    wrapped.__name__ = task.__name__
    return wrapped


class Context:
    reference = None
    engine = None


@worker_init.connect
@print_worker
def model_load_info(**__):
    Context.reference = get_reference().get()
    print(len(Context.reference))


##################################
# remove comment when use Multi-Threading
# initialize on only main thread
# share object with threads
##################################
# @worker_ready.connect
# @print_worker
# def module_ready(**__):
#     Context.engine = Engine(Context.reference)
#     print(Context.engine)


##################################
# remove comment when use Multi-Processing
# initialize all worker(all process)
##################################
@worker_process_init.connect
@print_worker
def module_load_init(**__):    
    Context.engine = Engine(Context.reference)
    print(Context.engine)


@app.task
@print_worker
def get_reference():
    reference = app.send_task(name='pvcd.tasks.get_references',
                              args=[],
                              exchange='pvcd',
                              routing_key='django_tasks',
                              )
    return reference


@app.task
@print_worker
def search_partial_copy(feature, topk, window, score, match):
    result = Context.engine.search_nearest(feature, topk)
    result = Context.engine.temporal_align(*result, window, score, match)

    return result
