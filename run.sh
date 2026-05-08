#!/usr/bin/env bash
set -e

echo "=== Django Startup ==="
echo "Running migrations..."
python manage.py migrate --noinput 2>&1

echo ""
echo "Creating demo users..."
python manage.py create_demo_users 2>&1

echo ""
echo "Verifying users were created..."
python manage.py shell << 'EOF'
from django.contrib.auth.models import User
users = User.objects.all()
print(f"Total users in database: {users.count()}")
for user in users:
    try:
        print(f"  - {user.username} (staff={user.is_staff}, role={user.profile.role})")
    except:
        print(f"  - {user.username} (no profile)")
EOF

echo ""
echo "Starting gunicorn..."
exec gunicorn webapp.wsgi:application --bind 0.0.0.0:$PORT
