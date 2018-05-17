#!/bin/bash

# Apply database migrations
echo "Apply database migrations"
./wait-for-it.sh db:5432 -- python manage.py migrate

# Create admin superuser
echo "Create users"
python manage.py shell -c "from django.contrib.auth.models import User; \
  User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')"

  if [ ! -f aquarius/config.py ]; then
      echo "Creating config file"
      cp aquarius/config.py.example aquarius/config.py
  fi

#Start server
echo "Starting server"
python manage.py runserver 0.0.0.0:8000
