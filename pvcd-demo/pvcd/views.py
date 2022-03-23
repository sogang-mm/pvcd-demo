from pvcd.models import Query, Result, Reference
from pvcd.serializers import UserSerializer, GroupSerializer, QuerySerializer, ResultSerializer, ReferenceSerializer

from django.contrib.auth.models import User, Group
from django.shortcuts import render
from django.core import serializers
from rest_framework import viewsets
from rest_framework import permissions


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]


class QueryViewSet(viewsets.ModelViewSet):
    queryset = Query.objects.all().order_by('-pk')
    serializer_class = QuerySerializer
    # feature_stream_serializer_class = FeatureStreamSerializer


class ResultViewSet(viewsets.ModelViewSet):
    queryset = Result.objects.all().order_by('-pk')
    serializer_class = ResultSerializer


class ReferenceViewSet(viewsets.ModelViewSet):
    queryset = Reference.objects.all().order_by('-pk')
    serializer_class = ReferenceSerializer


def index(request):
    serializer = QuerySerializer()

    style = {'template_pack': 'rest_framework/vertical/'}

    return render(request, 'pvcd/index.html', {'serializer': serializer, 'style': style})
