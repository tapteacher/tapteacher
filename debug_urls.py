import os
import django
from django.urls import get_resolver

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tapteacher_project.settings')
django.setup()

def list_urls(lis, acc=''):
    for entry in lis:
        if hasattr(entry, 'url_patterns'):
            list_urls(entry.url_patterns, acc + str(entry.pattern))
        else:
            print(f"{acc}{str(entry.pattern)} : {entry.name}")

resolver = get_resolver()
list_urls(resolver.url_patterns)
