import os
SECRET_KEY = os.urandom(32)
# Grabs the folder where the script runs.
basedir = os.path.abspath(os.path.dirname(__file__))

# Enable debug mode.
DEBUG = True

# Enter USERNAME to Connect to local instance of the database


USERNAME = 'malcolmsuhr'
SQLALCHEMY_DATABASE_URI = 'postgresql://'+USERNAME+'@localhost:5432/fyyur'
SQLALCHEMY_TRACK_MODIFICATIONS = False
