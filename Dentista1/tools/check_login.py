import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE','mxodontologia.settings')
sys.path.insert(0, os.getcwd())
import django
django.setup()
from django.test import Client
from clinic.views import ensure_demo_user
from django.conf import settings

ensure_demo_user()
client = Client()
# allow testserver host used by Django test client
if 'testserver' not in settings.ALLOWED_HOSTS:
	settings.ALLOWED_HOSTS.append('testserver')
# Attempt login via the root page using the 'next' and prefixed fields
resp = client.post('/', {'form_type': 'login', 'login-username': 'demo', 'login-password': 'demo123'}, follow=True)
print('STATUS:', resp.status_code)
print('URL:', resp.request.get('PATH_INFO'))
print('COOKIES:', client.cookies.get('sessionid'))
print('CONTENT START:', resp.content[:400])
# Now test logout
resp2 = client.get('/logout/', follow=True)
print('LOGOUT STATUS:', resp2.status_code)
print('LOGOUT URL:', resp2.request.get('PATH_INFO'))
print('COOKIES AFTER LOGOUT:', client.cookies.get('sessionid'))
