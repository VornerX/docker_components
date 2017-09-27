from components.deploy_components import DeploymentComposite, DeployMySQL, \
    DeployGraylog, DeploySSO

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

    sso_dep = DeploySSO('deployer_sso', '', '', '')

    deployment_composite.append_component([
        mysql_dep,
        sso_dep
    ])

    deployment_composite.execute_deployment()
