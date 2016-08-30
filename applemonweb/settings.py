import json
import os

from django.utils.crypto import get_random_string


BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Load the secret key if possible, otherwise generate one.
secret_filename = os.path.join(BASE_DIR, 'secrets.json')
try:
    secrets = json.load(open(secret_filename))
    SECRET_KEY = secrets['SECRET_KEY']
except Exception:
    SECRET_KEY = get_random_string(50)
    secrets = {'SECRET_KEY': SECRET_KEY}
    json.dump(secrets, open(secret_filename, 'w'))

if 'DEBUG' in secrets and secrets['DEBUG']:
    DEBUG = True
ALLOWED_HOSTS = ['localhost']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'formtools',
    'massadmin',
    'explorer',
    'armgmt',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'applemonweb.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'applemonweb.db')
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/New_York'
USE_I18N = False
USE_L10N = True
USE_THOUSAND_SEPARATOR = True
USE_TZ = True

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'

LOGIN_URL = '/admin/login/'
LOGOUT_URL = '/admin/logout/'

EXPLORER_DEFAULT_ROWS = 100
EXPLORER_RECENT_QUERY_COUNT = 0
