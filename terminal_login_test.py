import os
import json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webapp.settings')
import django
django.setup()
from django.test import Client
from django.contrib.auth.models import User
from monitor.models import UserProfile

c = Client()
print('=== PROFILE STATES ===')
for username in ['user1', 'admin1', 'guard1']:
    try:
        user = User.objects.get(username=username)
        profile = user.profile
        print(username, 'profile:', profile.role)
    except User.DoesNotExist:
        print(username, 'does not exist')
    except UserProfile.DoesNotExist:
        print(username, 'profile missing')

print('\n=== LOGIN TESTS ===')
for username, password, role in [
    ('user1', 'password', 'USER'),
    ('admin1', 'password', 'ADMIN'),
    ('guard1', 'password', 'GATE_GUARD'),
]:
    client = Client()
    r = client.post('/login/', {'username': username, 'password': password, 'role': role}, follow=True)
    print(username, '->', r.status_code)
    print('  final path:', r.request.get('PATH_INFO'))
    print('  redirect_chain:', r.redirect_chain)

print('=== ROOT JSON POST TEST ===')
r = Client().post('/', json.dumps({'device_id': 'dev1', 'notes': 'hi'}), content_type='application/json')
print('root JSON ->', r.status_code, r.content.decode('utf-8'))
