from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from monitor.models import UserProfile

class Command(BaseCommand):
    help = 'Create demo users'

    def handle(self, *args, **options):
        self.stdout.write("Starting demo user creation...")
        
        for username, password, role in [
            ('user1', 'password', 'USER'),
            ('admin1', 'password', 'ADMIN'),
            ('guard1', 'password', 'GATE_GUARD'),
        ]:
            user, created = User.objects.get_or_create(username=username)
            user.set_password(password)
            if role == 'ADMIN':
                user.is_staff = True
                user.is_superuser = False
            else:
                user.is_staff = False
                user.is_superuser = False
            user.save()
            
            profile, profile_created = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.save()
            
            status = "Created" if created else "Updated"
            self.stdout.write(f"✓ {status} {username} (role={role}, staff={user.is_staff})")
        
        self.stdout.write(self.style.SUCCESS("Demo users ready!"))