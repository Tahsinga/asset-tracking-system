"""
WSGI config for webapp project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
import sys

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webapp.settings')

application = get_wsgi_application()

# Ensure migrations run on startup (safety net if run.sh fails)
if os.environ.get('RENDER') and not os.environ.get('_DJANGO_MIGRATIONS_DONE'):
    try:
        from django.core.management import call_command
        print("[WSGI] Running migrations...", file=sys.stderr)
        call_command('migrate', verbosity=1)
        print("[WSGI] Migrations complete", file=sys.stderr)
        os.environ['_DJANGO_MIGRATIONS_DONE'] = '1'
    except Exception as e:
        print(f"[WSGI] Migration error: {e}", file=sys.stderr)
