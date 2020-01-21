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

#Start server
echo "Starting server"
python manage.py runserver 0.0.0.0:8002
