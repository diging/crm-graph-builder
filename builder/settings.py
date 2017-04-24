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
SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/db.sqlite'
