from pvcd_demo.celery import app
from pvcd.models import Query, Result, Reference
from pvcd.storage import ReferenceStorageField
from pvcd.tasks import get_references

from django.contrib.auth.models import User, Group
from rest_framework import serializers

from pathlib import Path

DEFAULT_METADATA = ['format', 'duration', 'size',
                    'video_codec', 'width', 'height', 'rotate',
                    'framecount', 'framerate', 'audio_codec']


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['url', 'username', 'email', 'groups']


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']


class NestReferenceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Reference
        fields = ('id', 'url')
        read_only_fields = fields


class ReferenceSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    video = ReferenceStorageField()
    _video = ReferenceStorageField(read_only=True)
    thumbnail = ReferenceStorageField(read_only=True)
    poster = ReferenceStorageField(read_only=True)
    feature = ReferenceStorageField(read_only=True)
    metadata = serializers.JSONField(read_only=True)

    class Meta:
        model = Reference
        fields = '__all__'
        read_only_fields = ('name', '_video', 'poster', 'thumbnail', 'feature', 'metadata')

    def create(self, validated_data):
        validated_data['name'] = validated_data['video'].name
        instance = super(ReferenceSerializer, self).create(validated_data)
        self.update_reference_video_async(instance)
        return instance

    def update(self, instance, validated_data):
        update = validated_data.get('video', None)
        if update is not None:
            validated_data['name'] = validated_data['video'].name
            instance = super(ReferenceSerializer, self).update(instance, validated_data)
            self.update_reference_video_async(instance)
        return instance

    def update_reference_video_async(self, instance):
        app.send_task(name='video.tasks.update_reference_video_async',
                      args=[instance.id, instance.video.path],
                      exchange='pvcd',
                      routing_key='video_tasks')


class ResultSerializer(serializers.ModelSerializer):
    reference = ReferenceSerializer(many=False, read_only=True)

    class Meta:
        model = Result
        fields = ('rank', 'query_start', 'query_end', 'reference', 'reference_start', 'reference_end', 'score', 'match')
        read_only_fields = fields


class QuerySerializer(serializers.HyperlinkedModelSerializer):
    topk = serializers.IntegerField(initial=100)
    window = serializers.IntegerField(initial=10)
    score_threshold = serializers.FloatField(initial=0.6)
    match_threshold = serializers.IntegerField(initial=3)
    results = ResultSerializer(many=True, read_only=True)

    class Meta:
        model = Query
        fields = ('url', 'video', '_video', 'thumbnail', 'name', 'metadata', 'topk',
                  'window', 'score_threshold', 'match_threshold',
                  'feature', 'uploaded_date', 'updated_date', 'results')
        read_only_fields = (
            '_video', 'thumbnail', 'name', 'metadata', 'feature', 'results', 'uploaded_date', 'updated_date')

    def create(self, validated_data):
        print(f'Get {validated_data}')
        validated_data['name'] = validated_data['video'].name
        instance = super(QuerySerializer, self).create(validated_data)
        instance = self.update_query_video(instance)

        return instance

    def update(self, instance, validated_data):
        update = validated_data.get('video', None)
        if update is not None:
            validated_data['name'] = validated_data['video'].name
            instance = super(QuerySerializer, self).update(instance, validated_data)
            instance = self.update_query_video(instance)

        return instance

    def update_query_video(self, instance):
        video_path = Path(instance.video.path)

        result = app.send_task(name='video.tasks.parse_video',
                               args=[video_path.as_posix(), True, 1, None],
                               exchange='pvcd',
                               routing_key='video_tasks').get()

        instance._video = instance._video.storage.path_to_name(result['_video'])
        instance.thumbnail = instance.thumbnail.storage.path_to_name(result['thumbnail'])
        instance.metadata = result['metadata']

        feature_path = video_path.parent.joinpath(f'{video_path.stem}.npy').as_posix()
        feature = app.send_task(name='extractor.tasks.extract_feature_by_frames',
                                args=[result['frames'], feature_path],
                                exchange='pvcd',
                                routing_key='torch_tasks',
                                serializer='pickle',
                                ).get()
        instance.feature = instance.feature.storage.path_to_name(feature_path)

        results = app.send_task(name='search.tasks.search_partial_copy',
                                args=[feature, instance.topk, instance.window, instance.score_threshold,
                                      instance.match_threshold],
                                exchange='pvcd',
                                routing_key='search_tasks',
                                serializer='pickle',
                                ).get()

        Result.objects.bulk_create([Result(rank=n,
                                           query=instance,
                                           query_start=r['query']['start'],
                                           query_end=r['query']['end'],
                                           reference=Reference.objects.get(pk=r['id']),
                                           reference_start=r['reference']['start'],
                                           reference_end=r['reference']['end'],
                                           score=r['score'],
                                           match=r['match']
                                           ) for n, r in enumerate(results, start=1)])
        instance.save()

        return instance
