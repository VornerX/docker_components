import os

HOME_DEPLOYMENT_DIR = os.path.join(
    os.path.expanduser('~'), 'deployer_test_dir', 'feedback'
)

GIT_REPOSITORIES = {
    "feedback-api-python": {
        "branch": "master",
        "url": "git@github.com:Alliera/feedback-api-python.git",
        "local_dir": os.path.join(HOME_DEPLOYMENT_DIR, 'feedback-api-python')
    },
    "sso": {
        "branch": "master",
        "url": "git@github.com:Alliera/sso.git",
        "local_dir": os.path.join(HOME_DEPLOYMENT_DIR, 'sso')
    },
    'feedback_ui': {
        "branch": "master",
        "url": "git@github.com:Alliera/XirclFeedbackBundle.git",
        "local_dir": os.path.join(HOME_DEPLOYMENT_DIR, 'feedback-ui')
    }
}

CONTAINERS = {
    'MYSQL': {
        'DOCKER_PORT': 3306,
        'LOCAL_PORT': 3370,
        'MYSQL_ROOT_PASSWORD': 'root',
        'MYSQL_CONTAINER_NAME': '1_deployer_mysql57',
        'IMAGE_NAME': 'centos/mysql-57-centos7',
    },
    'RABBITMQ': {
        'IMAGE_NAME': 'rabbitmq:3-management'
    },
    'FEEDBACK': {},
    'SSO': {}
}

