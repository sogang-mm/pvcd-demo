import os
from celery import Celery
from celery.signals import worker_init, worker_process_init
from celery.utils import threads
from billiard import current_process
from kombu import Queue
from celery import current_task
import threading

from extractor.extractor import Extractor
import numpy as np
from pathlib import Path

app = Celery('worker-extractor',
             broker='amqp://user:user@rabbitmq',
             backend='redis://pvcd-demo_redis:6379/1')
app.conf.update(
    task_serializer="json",
    accept_content=["json", "pickle"],
    result_serializer="pickle",

)

app.conf.task_queues = (
    Queue('extractor', 'pvcd', routing_key='torch_tasks'),
)


def print_worker(task):
    def wrapped(*args, **kwargs):
        worker = current_process().name
        thread = threading.currentThread().getName()
        print(f"Run: {task.__name__}, Worker({worker}), Thread({thread})")
        return task(*args, **kwargs)

    wrapped.__name__ = task.__name__
    return wrapped


@worker_init.connect
def model_load_info(**__):
    print("====================")
    print("Worker Initialize")
    print("====================")


@worker_process_init.connect
def module_load_init(**__):
    print("====================")
    print(f" Worker: {current_process().name}/{threading.currentThread().getName()}")
    print("====================")


class Context:
    ckpt = './extractor/mobilenet_avg_ep16_ckpt.pth'
    cluster = './extractor/cluster.pkl'
    extractor = Extractor(ckpt, cluster)


@app.task
@print_worker
def extract_feature_by_frames(frames, save=None):
    print(f'Get {len(frames)} frames')
    feature = Context.extractor.inference(frames)
    if save is not None:
        np.save(save, feature)

    return feature


@app.task
@print_worker
def update_reference_video_async(pk, result):
    frames = result.pop('frames')
    video = Path(result['video'])
    path = video.parent.joinpath(f'{video.stem}.npy').as_posix()

    _ = extract_feature_by_frames(frames, path)
    result['feature'] = path

    app.send_task(name='pvcd.tasks.update_reference_video_async',
                  args=[pk, result],
                  exchange='pvcd',
                  routing_key='django_tasks',
                  )
