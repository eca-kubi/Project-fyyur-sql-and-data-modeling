import os
SECRET_KEY = os.urandom(32)
# Grabs the folder where the script runs.
basedir = os.path.abspath(os.path.dirname(__file__))

# Enable debug mode.
DEBUG = True

# IMPLEMENT DATABASE URL
SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:addmin300@localhost:5432/projectfyyur'

#Disable SQLALCHEMY_TRACK_MODIFICATIONS
SQLALCHEMY_TRACK_MODIFICATIONS = False
