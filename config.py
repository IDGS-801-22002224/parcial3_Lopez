# config.py
import os
from sqlalchemy import create_engine
import urllib

class Config(object):
    SECRET_KEY = os.getenv('SECRET_KEY', 'mi-random-secret-key-1234567890')  
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:root@127.0.0.1/ExamenSegundoParcial'
    SQLALCHEMY_TRACK_MODIFICATIONS = False