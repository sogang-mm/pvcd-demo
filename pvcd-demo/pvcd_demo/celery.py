import os
from celery import Celery
from kombu import Queue, Exchange

# from celery.schedules import crontab


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pvcd_demo.settings')

app = Celery('worker',
             broker='amqp://user:user@rabbitmq',
             backend='redis://pvcd-demo_redis:6379/0')
app.conf.update(
    accept_content=["json", "pickle"],
    task_serializer="json",
    result_serializer="pickle"
)
app.autodiscover_tasks()

app.conf.task_queues = (
    Queue('django', 'pvcd', routing_key='django_tasks'),
)
# app.conf.task_default_exchange = 'pvcd'
# app.conf.task_default_exchange_type = 'direct'
