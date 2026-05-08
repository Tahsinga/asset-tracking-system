web: gunicorn webapp.wsgi:application
release: python manage.py migrate && python manage.py create_demo_users