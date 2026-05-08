import os
import sys

from django.apps import AppConfig


class MonitorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitor'

    def ready(self):
        # Create demo users on startup if the database is ready.
        # This is idempotent and avoids broken login when Render deployment does not run the release step.
        if len(sys.argv) > 1 and sys.argv[1] in [
            'check', 'migrate', 'makemigrations', 'collectstatic', 'shell',
            'createsuperuser', 'test', 'loaddata', 'dumpdata', 'flush',
            'compilemessages', 'sqlmigrate', 'inspectdb',
        ]:
            return

        try:
            from django.contrib.auth.models import User
            from django.db import OperationalError, ProgrammingError
            from monitor.models import UserProfile

            for username, password, role in [
                ('user1', 'password', 'USER'),
                ('admin1', 'password', 'ADMIN'),
                ('guard1', 'password', 'GATE_GUARD'),
            ]:
                user, _ = User.objects.get_or_create(username=username)
                user.set_password(password)
                user.is_staff = role == 'ADMIN'
                user.is_superuser = False
                user.save()

                profile, _ = UserProfile.objects.get_or_create(user=user)
                profile.role = role
                profile.save()
        except (OperationalError, ProgrammingError):
            # Database may not be ready yet during migrations or first startup.
            pass
