from components.deploy_components import (
    DeploymentComposite, DeployMySQL, DeployGraylog, DeploySSO,
    DeployFeedbackApi, DeployRabbitMQ, DeployXircleFeebackBundle
)

try:
    from config import CONTAINERS_SETTINGS
except ImportError:
    print('You need to create config file, from example config_default.py')


def run_deployment():
    deployment_composite = DeploymentComposite()

    # TODO: after finishing - move all settings to config

    mysql_dep = DeployMySQL(
        container_name='1_deployer_mysql57',
        image_name='centos/mysql-57-centos7',
        docker_port=3306,
        localhost_port=3370,
        mysql_pwd='root',
    )

    rabbitmq_dep = DeployRabbitMQ(
        container_name='1_deployer_rabbitmq',
        image_name='rabbitmq:3-management',
        docker_port=15672,
        localhost_port=15675,
    )

    graylog_dep = DeployGraylog(
        container_name='1_deployer_graylog',
        image_name='graylog2/server',
        docker_port=9000,
        localhost_port=9000,
    )

    sso_dep = DeploySSO(
        container_name='1_deployer_sso',
        image_name='sso',
        docker_port=81,
        localhost_port=10180
    )

    feedback_dep = DeployFeedbackApi(
        container_name='1_deployer_feedback',
        image_name='feedback',
        docker_port=81,
        localhost_port=10181
    )

    deployment_composite.append_component([
        mysql_dep,
        rabbitmq_dep,
        graylog_dep,
        sso_dep,
        feedback_dep
    ])

    deployment_composite.execute_deployment()
