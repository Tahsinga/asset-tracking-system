from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from monitor.models import UserProfile


class Command(BaseCommand):
    help = 'Create demo users for the asset tracking system'

    def handle(self, *args, **options):
        demo_users = [
            ('user1', 'password', 'USER'),
            ('admin1', 'password', 'ADMIN'),
            ('guard1', 'password', 'GATE_GUARD'),
        ]

        for username, password, role in demo_users:
            user, created = User.objects.get_or_create(username=username)
            user.set_password(password)
            if role == 'ADMIN':
                user.is_staff = True
            user.save()
            
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.save()
            
            status = 'Created' if created else 'Updated'
            self.stdout.write(
                self.style.SUCCESS(
                    f'{status} user "{username}" with role "{role}"'
                )
            )
