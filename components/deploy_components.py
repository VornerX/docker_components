from abc import ABC, abstractmethod
from io import BytesIO
from pprint import pprint
import docker

client = docker.from_env()


class DeploymentComponent(ABC):

    def __init__(self, container_name, image_name, docker_port, local_port):
        self._image_name = image_name
        self._container_name = container_name
        self._docker_port = docker_port
        self._local_port = local_port

    @abstractmethod
    def create(self):
        pass


class DeployMySQL(DeploymentComponent):

    def __init__(self, container_name, image_name, local_port, docker_port,
                 mysql_pwd, mysql_port):
        self._mysql_pwd = mysql_pwd
        self._mysql_port = mysql_port
        super().__init__(container_name, image_name, local_port, docker_port)

    def create(self):
        print('Deploy MySQL container.\r\n')
        mysql_container = client.api.create_container(
            name='deployer_mysql57',
            image='centos/mysql-57-centos7',
            environment={
                'MYSQL_ROOT_PASSWORD': 'root',
            },
            ports=[3306],
            host_config=client.api.create_host_config(port_bindings={
                3306: 3370
            }),
        )
        client.api.start(mysql_container)
        # client.api.kill(mysql_container_id)
        # client.api.wait(mysql_container_id)
        # client.api.remove_container(mysql_container_id)

        print(mysql_container)


class DeployGraylog(DeploymentComponent):
    def create(self):
        pass

class DeployFeedbackApi(DeploymentComponent):
    pass


class DeploySSO(DeploymentComponent):

    def create(self):

        with open('docker_files/sso_local_Dockerfile', mode="r") as dockerfile:
            f = BytesIO(dockerfile.read().encode('utf-8'))
            try:
                for line in client.api.build(
                    fileobj=f,
                    nocache=False,
                    rm=True,
                    tag='sso_image',
                    decode=True,
                    pull=True
                ):
                    line = line.get('stream')
                    if line is not None:
                        print(line)
            except Exception:
                raise IOError("Invalid Dockerfile!")

        sso_container = client.api.create_container(
            image='sso_image',
            name='deployer_sso',
            stdin_open=True, tty=True,
            ports=[8000],
            host_config=client.api.create_host_config(
                port_bindings={8000: 8081}
            ),
            # environment=''
        )

        # get object by name
        # mysql_container = client.containers.get('deployer_mysql57')

        client.api.connect_container_to_network(
            net_id='dev_net', container=sso_container,
            links={'deployer_mysql57': 'mysql'}  # name: alias
        )

        client.api.start(sso_container)



class DeployXircleFeebackBundle(DeploymentComponent):
    pass


class DeploymentComposite(object):
    def __init__(self):
        self.components = []  # must be a list, because ordering are important

    def append_component(self, component):
        """ Can accept single DeployComponent or list of them """
        if isinstance(component, DeploymentComponent):
            self.components.append(component)
        elif isinstance(component, list):
            for c in component:
                if isinstance(c, DeploymentComponent):
                    self.components.append(c)
                else:
                    raise ValueError(
                        "Component must be an instance of "
                        "'DeploymentComponent'")
        else:
            raise ValueError(
                "Component must be an instance of 'DeploymentComponent'")

    def remove_component(self, component):
        self.components.remove(component)

    def execute_deployment(self):
        if self.components:
            for c in self.components:
                c.create()
