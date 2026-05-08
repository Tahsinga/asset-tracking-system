import os

from django.apps import AppConfig


class MonitorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitor'

    def ready(self):
        # Create demo users on startup if the database is ready.
        # This is idempotent and avoids broken login when Render deployment does not run the release step.
        if os.environ.get('RUN_MAIN') not in ('true', '1') and os.environ.get('WERKZEUG_RUN_MAIN') not in ('true', '1'):
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
