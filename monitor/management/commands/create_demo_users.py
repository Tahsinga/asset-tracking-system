from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from monitor.models import UserProfile


class Command(BaseCommand):
    help = 'Create demo users for the application'

    def handle(self, *args, **options):
        for username, password, role in [
            ('user1', 'password', 'USER'),
            ('admin1', 'password', 'ADMIN'),
            ('guard1', 'password', 'GATE_GUARD'),
        ]:
            user, created = User.objects.get_or_create(username=username)
            user.set_password(password)  # Always set password
            if role == 'ADMIN':
                user.is_staff = True
                user.is_superuser = True
            user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.save()
            self.stdout.write(
                self.style.SUCCESS(f'Set {username} role {role}')
            )