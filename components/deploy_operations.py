from components.deploy_components import (
    DeploymentComposite, DeployMySQL, DeploySSO, DeployFeedbackApi,
    DeployRabbitMQ, DeployXircleFeebackBundle, prepare_images, prepare_network
)
from helpers.git_operations import clone_repositories
from helpers.color_print import ColorPrint
cprint = ColorPrint()
try:
    from config import CONTAINERS
except ImportError:
    cprint.red(
        "Settings will be taken from default config but it's strongly "
        "recommended to create your own config.py, based on it!")
    from config_default import CONTAINERS


def run_deployment():

    prepare_network()
    prepare_images()
    clone_repositories()

    deployment_composite = DeploymentComposite()

    mysql_dep = DeployMySQL(
        container_name=CONTAINERS['MYSQL']['CONTAINER_NAME'],
        image_name=CONTAINERS['MYSQL']['IMAGE_NAME'],
        docker_port=CONTAINERS['MYSQL']['DOCKER_PORT'],
        localhost_port=CONTAINERS['MYSQL']['LOCAL_PORT']
    )

    rabbitmq_dep = DeployRabbitMQ(
        container_name=CONTAINERS['RABBITMQ']['CONTAINER_NAME'],
        image_name=CONTAINERS['RABBITMQ']['IMAGE_NAME'],
        docker_port=CONTAINERS['RABBITMQ']['DOCKER_PORT'],
        localhost_port=CONTAINERS['RABBITMQ']['LOCAL_PORT'],
    )

    sso_dep = DeploySSO(
        container_name=CONTAINERS['SSO']['CONTAINER_NAME'],
        image_name='sso',  # custom
        docker_port=CONTAINERS['SSO']['DOCKER_PORT'],
        localhost_port=CONTAINERS['SSO']['LOCAL_PORT']
    )

    feedback_dep = DeployFeedbackApi(
        container_name=CONTAINERS['FEEDBACK_API']['CONTAINER_NAME'],
        image_name='feedback',  # custom
        docker_port=CONTAINERS['FEEDBACK_API']['DOCKER_PORT'],
        localhost_port=CONTAINERS['FEEDBACK_API']['LOCAL_PORT']
    )

    xircle_feedback_bundle_dep = DeployXircleFeebackBundle(
        container_name=CONTAINERS['XIRCL_FB_BUNDLE']['CONTAINER_NAME'],
        image_name=CONTAINERS['XIRCL_FB_BUNDLE']['IMAGE_NAME'],
        docker_port=CONTAINERS['XIRCL_FB_BUNDLE']['DOCKER_PORT'],
        localhost_port=CONTAINERS['XIRCL_FB_BUNDLE']['LOCAL_PORT']
    )

    # graylog_dep = DeployGraylog(
    #     container_name='deployer_graylog',
    #     image_name='graylog2/server',
    #     docker_port=9000,
    #     localhost_port=9000,
    # )

    deployment_composite.append_component([
        mysql_dep,
        rabbitmq_dep,
        sso_dep,
        feedback_dep,
        xircle_feedback_bundle_dep
    ])

    deployment_composite.execute_deployment()
