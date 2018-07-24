#!/bin/bash

./wait-for-it.sh db:5432 -- echo "Creating config file"

if [ ! -f manage.py ]; then
  cd aquarius
fi

if [ ! -f aquarius/config.py ]; then
    cp aquarius/config.py.example aquarius/config.py
fi

echo "Apply database migrations"
python manage.py migrate

# Create admin superuser
echo "Create users"
python manage.py shell -c "from django.contrib.auth.models import User; \
  User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')"

#Start server
echo "Starting server"
python manage.py runserver 0.0.0.0:8002
