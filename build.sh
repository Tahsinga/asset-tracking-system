#!/usr/bin/env bash
pip install -r requirements.txt
python manage.py migrate
python create_demo_users.py
python create_demo_data.py
