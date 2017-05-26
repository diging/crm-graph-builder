import os

NEO4J_URL = os.environ.get('NEO4J_URL')
CRM_URL = os.environ.get('CRM_URL')

OAUTH_CREDENTIALS = {
    'github': {
        'id': os.environ.get('GITHUB_KEY'),
        'secret': os.environ.get('GITHUB_SECRET')
    },
}
SECRET_KEY = os.environ.get('SECRET_KEY', 'asdf')
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:////tmp/db.sqlite')
STATIC_URL = os.environ.get('STATIC_URL')

ADMIN_SOCIALID = os.environ.get('ADMIN_SOCIALID')
ADMIN_NICKNAME = os.environ.get('ADMIN_NICKNAME')
ADMIN_SOCIAL_PROVIDER = os.environ.get('ADMIN_SOCIAL_PROVIDER')

SERVER_NAME = os.environ.get('SERVER_NAME')
