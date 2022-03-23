import os
import sys

from celery import Celery
from celery.signals import worker_init, worker_process_init
from billiard import current_process
from kombu import Queue
import threading

from PIL import Image
import requests
import ffmpeg
import numpy as np
import traceback
import math
from pathlib import Path

app = Celery('worker-video',
             broker='amqp://user:user@rabbitmq',
             backend='redis://pvcd-demo_redis:6379/2')

app.conf.update(
    task_serializer="json",
    accept_content=["json", "pickle"],
    result_serializer="pickle"
)

app.conf.task_queues = (
    Queue('video', 'pvcd', routing_key='video_tasks'),
)


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
def update_reference_video_async(pk, path):
    try:
        result = parse_video(path, decode=True, decode_rate=1, decode_size=None, poster=True)
        result['video'] = path

        app.send_task(name='extractor.tasks.update_reference_video_async',
                      args=[pk, result],
                      exchange='pvcd',
                      routing_key='torch_tasks',
                      serializer='pickle')
    except Exception as e:
        print(sys.stdout.decode())
        print(sys.stderr.decode())



"""
METADATA_KEY_MAP = {
    'format': 'format.format_name',
    'duration': 'format.duration',
    'size': 'format.size',

    'video_codec': 'video.codec_name',
    'width': 'video.width',
    'height': 'video.height',
    'rotate': 'video.tags.rotate',
    'framecount': 'video.nb_read_frames',
    'framerate': 'video.avg_frame_rate',

    'audio_codec': 'audio.codec_name',
}
"""

METADATA_KEY_MAP = {
    'format': ('format.format_name', str),
    'duration': ('format.duration', float),
    'size': ('format.size', int),

    'video_codec': ('video.codec_name', str),
    'width': ('video.width', int),
    'height': ('video.height', int),
    'rotate': ('video.tags.rotate', int),
    'framecount': ('video.nb_read_frames', int),
    'framerate': ('video.avg_frame_rate', float),

    'audio_codec': ('audio.codec_name', str),
}

DEFAULT_DOWNSCALE_FACTORS = {
    3200: 12,  # ~4k
    2100: 8,  # ~2k
    1700: 6,  # ~1080p
    1200: 5,
    900: 4,  # ~720p
    600: 3,
    400: 2  # ~480p
}


def compute_downscale_factor(width, height):
    long_side = width if width > height else height
    for length in sorted(DEFAULT_DOWNSCALE_FACTORS.keys(), reverse=True):
        if long_side > length:
            return DEFAULT_DOWNSCALE_FACTORS[length]
    return 1


def compute_transcode(metadata):
    invalid_format = 'mp4' not in metadata['format'].split(',')
    invalid_vcodec = metadata['video_codec'] != 'h264'  # 'vp8'
    invalid_acodec = metadata['audio_codec'] != 'aac'  # 'vorbis'

    ds_factor = compute_downscale_factor(metadata['width'], metadata['height'])
    scale = (f'trunc(iw/{ds_factor}/2)*2', -2)

    transcoding = invalid_format or invalid_vcodec or invalid_acodec or ds_factor != 1

    return transcoding, scale


def compute_thumbnail(metadata):
    size = (metadata['width'], metadata['height'])
    rotate = 0 if metadata['rotate'] is None else int(metadata['rotate'])
    display_size = size if rotate in [0, 180] else size[::-1]

    thumbnail_height = 60
    thumbnail_width = int(display_size[0] * thumbnail_height / display_size[1])
    thumbnail_count = 15 if display_size[0] > display_size[1] else 30

    thumbnail_per_frame = math.ceil(int(metadata['framecount']) / thumbnail_count)

    return (thumbnail_width, thumbnail_height), thumbnail_per_frame, thumbnail_count


def compute_decode(metadata, decode_size):
    size = (metadata['width'], metadata['height'])
    rotate = 0 if metadata['rotate'] is None else int(metadata['rotate'])
    display_size = size if rotate in [0, 180] else size[::-1]

    if decode_size is None:
        scale = display_size
    elif isinstance(decode_size, int):
        # short side -> decode size
        pass
    elif hasattr(decode_size, '__iter__') and len(decode_size) == 2:
        scale = list(decode_size)
    else:
        pass

    return scale


@app.task
@print_worker
def parse_metadata(video, keys=None):
    metadata = ffmpeg.probe(video, print_format='json', show_format=None, count_frames=None)
    if keys is not None:
        metadata = probe(metadata, [METADATA_KEY_MAP[k] for k in keys])
        metadata = dict(zip(keys, metadata))
    return metadata


def probe(metadata, keys):
    def get_nested_item(d, k, type=str, sep='.'):
        _k = k.split(sep)
        item = d.get(_k[0], None)
        if isinstance(item, dict):
            item = get_nested_item(item, sep.join(_k[1:]), type, sep)
        try:
            item = type(item)
        except Exception:
            item = item
        return item

    video_streams = [s for s in metadata['streams'] if s['codec_type'] == 'video']
    audio_streams = [s for s in metadata['streams'] if s['codec_type'] == 'audio']

    _metadata = []
    for (k, t) in keys:
        if k.startswith('format'):
            m = get_nested_item(metadata, k, t)
        else:
            _k = '.'.join(k.split('.')[1:])
            streams = video_streams if k.startswith('video') else audio_streams
            for s in streams:
                m = get_nested_item(s, _k, t)
                if m is not None:
                    break
        _metadata.append(m)
    return _metadata


@app.task
@print_worker
def parse_video(video, decode=False, decode_rate=1, decode_size=None, poster=False):
    v = Path(video)
    results = dict()

    # metadata
    metadata = parse_metadata(v.as_posix(), keys=METADATA_KEY_MAP.keys())
    results['metadata'] = metadata

    _input = ffmpeg.input(v.as_posix(), vsync=2).split()
    graphs = []

    # thumbnail
    thumb_scale, thumb_rate, thumb_count = compute_thumbnail(metadata)
    thumb_path = v.parent.joinpath(f'{v.stem}_thumbnail.jpg')
    graphs.append(_input[0]
                  .filter('thumbnail', n=thumb_rate)
                  .filter('scale', thumb_scale[0], thumb_scale[1])
                  .filter('tile', f'{thumb_count}x1')
                  .output(thumb_path.as_posix(), vframes=1)
                  )
    results['thumbnail'] = thumb_path.as_posix()

    # transcoding
    transcode, transcode_scale = compute_transcode(metadata)
    if transcode:
        transcode_path = v.parent.joinpath(f'_{v.stem}.mp4')
        # transcode_path = v.parent.joinpath(f'_{v.stem}.webm')
        graphs.append(_input[1]
                      .filter('scale', transcode_scale[0], transcode_scale[1])
                      .output(transcode_path.as_posix(), vcodec='libx264', acodec='aac')
                      # .output(transcode_path.as_posix(), vcodec='libvpx', acodec='libvorbis')
                      )
    else:
        transcode_path = v
    results['_video'] = transcode_path.as_posix()

    if decode:
        graphs.append(_input[2]
                      .filter('fps', fps=decode_rate)
                      .output('pipe:', format='rawvideo', pix_fmt='rgb24'))

    if poster:
        poster_path = v.parent.joinpath(f'{v.stem}_poster.jpg')
        graphs.append(_input[3]
                      .filter('thumbnail', n=metadata['framecount'])
                      .filter('scale', thumb_scale[0], thumb_scale[1])
                      .output(poster_path.as_posix(), vframes=1)
                      )
        results['poster'] = poster_path.as_posix()

    cmd = (ffmpeg
           .merge_outputs(*graphs)
           .global_args('-loglevel', 'error')
           .global_args('-hide_banner')
           )

    out, err = cmd.run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
    if decode:
        decode_scale = compute_decode(metadata, decode_size)

        frames = np.frombuffer(out, np.uint8).reshape([-1, decode_scale[1], decode_scale[0], 3])
        frames = [Image.fromarray(f) if decode_size is None else Image.fromarray(f).resize(decode_size) for f in frames]

        results['frames'] = frames

    return results
