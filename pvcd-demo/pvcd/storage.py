from django.core.files.storage import FileSystemStorage
from django.conf import settings
from rest_framework import serializers

from urllib.parse import urljoin
import os


class _FileSystemStorage(FileSystemStorage):
    def path_to_name(self, path):
        return os.path.relpath(path, self.location)

    def name_to_path(self, name):
        return os.path.join(self.location, name)


class ReferenceStorageField(serializers.FileField):
    def to_representation(self, value):
        try:
            # print(value)
            url = value.url
        except AttributeError:
            return None
        except ValueError:
            return None

        request = self.context.get('request', None)
        if request is not None:
            return urljoin(request._current_scheme_host, url)
        return None


ReferenceStorage = _FileSystemStorage(location=settings.REFERENCE_ROOT,
                                      base_url=settings.REFERENCE_URL)

QueryStorage = _FileSystemStorage(location=settings.MEDIA_ROOT,
                                  base_url=settings.MEDIA_URL)
