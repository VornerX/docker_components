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

DOCKER_NETWORK = {
    'NETWORK_NAME': 'dep_network',
    'SUBNET': '192.168.1.0/24',
    'GATEWAY': '192.168.1.254'
}

CONTAINERS = {

    'MYSQL': {
        'DOCKER_PORT': 3306,
        'LOCAL_PORT': 3370,
        'CONTAINER_NAME': 'dep_mysql57',
        'IMAGE_NAME': 'centos/mysql-57-centos7',
        'NETWORK': {
            'IPV4_ADDRESS': '192.168.1.2',
            'HOSTNAME': ['dep_mysql57', 'mysqlhost']
        },
        'MYSQL_ROOT_PASSWORD': 'root',
    },

    'RABBITMQ': {
        'DOCKER_PORT': 15672,
        'LOCAL_PORT': 15675,
        'CONTAINER_NAME': 'dep_rabbitmq',
        'IMAGE_NAME': 'rabbitmq:3-management',
        'NETWORK': {
            'IPV4_ADDRESS': '192.168.1.3',
            'HOSTNAME': ['dep_rabbitmq', 'rabbitmqhost']
        },
    },

    'SSO': {
        'DOCKER_PORT': 81,
        'LOCAL_PORT': 10180,
        'CONTAINER_NAME': 'deployer_xircl_ui',
        'IMAGE_NAME': 'custom',  # from Dockerfile
        'NETWORK': {
            'IPV4_ADDRESS': '192.168.1.4',
            'HOSTNAME': ['dep_sso', 'ssohost']
        },
    },

    'FEEDBACK_API': {
        'DOCKER_PORT': 81,
        'LOCAL_PORT': 10181,
        'CONTAINER_NAME': 'dep_feedback_api',
        'IMAGE_NAME': 'custom',  # from Dockerfile
        'NETWORK': {
            'IPV4_ADDRESS': '192.168.1.5',
            'HOSTNAME': ['dep_feedback_api', 'feedbackapihost']
        },
    },

    'XIRCL_FB_BUNDLE': {
        'DOCKER_PORT': 8080,
        'LOCAL_PORT': 8081,
        'CONTAINER_NAME': 'deployer_xircl_ui',
        'IMAGE_NAME': 'custom',  # from Dockerfile
        'NETWORK': {
            'IPV4_ADDRESS': '192.168.1.6',
            'HOSTNAME': ['dep_xircl_ui', 'xircluihost']
        },
    }
}
