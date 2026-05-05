import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','webapp.settings')
import django
django.setup()

from django.contrib.auth.models import User
from monitor.models import UserProfile

for username,password,role in [
    ('user1','password','USER'),
    ('admin1','password','ADMIN'),
    ('guard1','password','GATE_GUARD'),
]:
    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_password(password)
        if role=='ADMIN':
            user.is_staff=True
        user.save()
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.role=role
    profile.save()
    print('Set',username,'role',role)
