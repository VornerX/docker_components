from components.deploy_components import (
    DeploymentComposite, DeployMySQL, DeployGraylog, DeploySSO,
    DeployFeedbackApi, DeployXircleFeebackBundle
)

try:
    from config import CONTAINERS_SETTINGS
except ImportError:
    print('You need to create config file, from example config_default.py')


def run_deployment():
    deployment_composite = DeploymentComposite()

    mysql_dep = DeployMySQL(
        container_name=CONTAINERS_SETTINGS['MYSQL']['MYSQL_CONTAINER_NAME'],
        image_name=CONTAINERS_SETTINGS['MYSQL']['MYSQL_CONTAINER_IMAGE'],
        local_port=CONTAINERS_SETTINGS['MYSQL']['LOCAL_PORT'],
        docker_port=CONTAINERS_SETTINGS['MYSQL']['DOCKER_PORT'],
        mysql_pwd=CONTAINERS_SETTINGS['MYSQL']['MYSQL_ROOT_PASSWORD'],
        mysql_port=CONTAINERS_SETTINGS['MYSQL']['DOCKER_PORT']
    )

    graylog_dep = DeployGraylog(
        container_name='deployer_graylog',
        image_name='',
        local_port='',
        docker_port=''
    )

    sso_dep = DeploySSO(
        container_name='deployer_sso',
        image_name='',
        local_port=10180,
        docker_port=81
    )

    feedback_dep = DeployFeedbackApi(
        container_name='deployer_feedback',
        image_name='',
        local_port=10181,
        docker_port=81
    )

    deployment_composite.append_component([
        mysql_dep,
        graylog_dep,
        sso_dep,
        feedback_dep
    ])

    deployment_composite.execute_deployment()
