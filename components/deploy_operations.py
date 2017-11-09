from components.deploy_components import (
    DeploymentComposite, DeployMySQL, DeploySSO, DeployFeedbackApi,
    DeployRabbitMQ, DeployXircleFeebackBundle, prepare_images
)
from helpers.git_operations import clone_repositories

try:
    from config import CONTAINERS
except ImportError:
    print('You need to create config file, from example config_default.py')


def run_deployment():

    prepare_images()
    clone_repositories()

    deployment_composite = DeploymentComposite()

    # TODO: after finishing - move all settings to config

    mysql_dep = DeployMySQL(
        container_name='deployer_mysql57',
        image_name='centos/mysql-57-centos7',
        docker_port=3306,
        localhost_port=3370,
        mysql_pwd='root',
    )

    rabbitmq_dep = DeployRabbitMQ(
        container_name='deployer_rabbitmq',
        image_name='rabbitmq:3-management',
        docker_port=15672,
        localhost_port=15675,
    )

    sso_dep = DeploySSO(
        container_name='deployer_sso',
        image_name='sso',
        docker_port=81,
        localhost_port=10180
    )

    # graylog_dep = DeployGraylog(
    #     container_name='deployer_graylog',
    #     image_name='graylog2/server',
    #     docker_port=9000,
    #     localhost_port=9000,
    # )


    feedback_dep = DeployFeedbackApi(
        container_name='deployer_feedback',
        image_name='feedback',
        docker_port=81,
        localhost_port=10181
    )

    xircle_feedback_bundle_dep = DeployXircleFeebackBundle(
        container_name='deployer_xircl_ui',
        image_name='xircl_ui',
        docker_port=8080,
        localhost_port=8081
    )

    deployment_composite.append_component([
        mysql_dep,
        rabbitmq_dep,
        sso_dep,
        feedback_dep,
        xircle_feedback_bundle_dep
    ])

    deployment_composite.execute_deployment()
