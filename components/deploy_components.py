from abc import ABC, abstractmethod
from io import BytesIO
import docker
from helpers.color_print import ColorPrint

client = docker.from_env()
cprint = ColorPrint()


class DeploymentComponent(ABC):

    def __init__(
            self, container_name, image_name, docker_port, local_port):
        self.image_name = image_name
        self.container_name = container_name
        self.docker_port = docker_port
        self.local_port = local_port

    def inspect_after_start(self):
        inspect = client.api.inspect_container(self.container_name)
        cprint.blue(
            "{} (id: {}) started.\nIt's available at IP {} ({}).\r\n".format(
                self.container_name,
                inspect['Id'],
                inspect['NetworkSettings']['IPAddress'],
                inspect['NetworkSettings']['Ports']
        ))

    @abstractmethod
    def create(self):
        pass


class DeployMySQL(DeploymentComponent):

    def __init__(self, container_name, image_name, local_port, docker_port,
                 mysql_pwd):
        self._mysql_pwd = mysql_pwd
        super().__init__(container_name, image_name, local_port, docker_port)

    def create(self):
        print('Start deploying of MySQL container.\r\n')
        mysql_container = client.api.create_container(
            name=self.container_name,
            image=self.image_name,
            environment={
                'MYSQL_ROOT_PASSWORD': self._mysql_pwd,
            },
            ports=[self.docker_port],
            host_config=client.api.create_host_config(port_bindings={
                self.docker_port: self.local_port
            }),
        )
        client.api.start(mysql_container)

        # TODO: when (if) finished - move this to composite execute
        self.inspect_after_start()

        # client.api.kill(mysql_container_id)
        # client.api.wait(mysql_container_id)
        # client.api.remove_container(mysql_container_id)
        # print(mysql_container)


class DeployGraylog(DeploymentComponent):
    def create(self):
        print('Start deploying of Graylog container.\r\n')

        # elastic search
        es_container = client.api.create_container(
            name='1_deployer_elastic_search',
            image='elasticsearch:2',
            environment={},
            ports=[9200],
            host_config=client.api.create_host_config(port_bindings={
                9200: 9200
            }),
        )
        client.api.start(es_container)

        # mongodb
        mongodb_container = client.api.create_container(
            name='1_deployer_mongodb',
            image='mongo:2.6',
            environment={},
            ports=[27017],
            host_config=client.api.create_host_config(port_bindings={
                27017: 27020
            }),
        )
        client.api.start(mongodb_container)

        # graylog
        graylog_container = client.api.create_container(
            name='1_deployer_graylog',
            image='graylog2/server',
            environment={
                'GRAYLOG_WEB_ENDPOINT_URI': 'http://127.0.0.1:9000/api'
            },
            ports=[self.docker_port],
            host_config=client.api.create_host_config(port_bindings={
                self.docker_port: self.local_port,
                '12201/udp': '12201/udp',
            }),
        )

        client.api.create_network("deployer_network", driver="bridge")
        client.api.connect_container_to_network(
            net_id='deployer_network', container=graylog_container,
            links={
                '1_deployer_elastic_search': 'elasticsearch',  # name: alias
                '1_deployer_mongodb': 'mongodb'
            }
        )

        client.api.start(graylog_container)

        self.inspect_after_start()


class DeployFeedbackApi(DeploymentComponent):
    def create(self):
        print('Start deploying of Feedback API container.\r\n')
        with open('docker_files/feedback_local_Dockerfile',
                  mode="r") as dockerfile:
            f = BytesIO(dockerfile.read().encode('utf-8'))
            try:
                for line in client.api.build(
                    fileobj=f,
                    nocache=False,
                    rm=True,
                    tag='{}_image'.format(self.container_name),
                    decode=True,
                    pull=True
                ):
                    line = line.get('stream')
                    if line is not None:
                        cprint.green(line)
            except Exception:
                raise IOError("Invalid Dockerfile!")

        feedback_container = client.api.create_container(
            image='{}_image'.format(self.container_name),
            name=self.container_name,
            stdin_open=True, tty=True,
            ports=[self.docker_port],
            host_config=client.api.create_host_config(
                port_bindings={self.docker_port: self.local_port}
            ),
            # environment=''
        )
        client.api.start(feedback_container)
        self.inspect_after_start()


class DeploySSO(DeploymentComponent):

    def create(self):
        print('Start deploying of SSO container.\r\n')
        with open('docker_files/sso_local_Dockerfile', mode="r") as dockerfile:
            f = BytesIO(dockerfile.read().encode('utf-8'))
            try:
                for line in client.api.build(
                    fileobj=f,
                    nocache=False,
                    rm=True,
                    tag='{}_image'.format(self.container_name),
                    decode=True,
                    pull=True
                ):
                    line = line.get('stream')
                    if line is not None:
                        cprint.green(line)
            except Exception:
                raise IOError("Invalid Dockerfile!")

        sso_container = client.api.create_container(
            image='{}_image'.format(self.container_name),
            name=self.container_name,
            stdin_open=True, tty=True,
            ports=[self.docker_port],
            host_config=client.api.create_host_config(
                port_bindings={self.docker_port: self.local_port}
            ),
            # environment=''
        )

        # get object by name
        # mysql_container = client.containers.get('deployer_mysql57')
        # client.api.create_network("dev_network", driver="bridge")
        # client.api.connect_container_to_network(
        #     net_id='dev_network', container=sso_container,
        #     links={'deployer_mysql57': 'mysql'}  # name: alias
        # )

        client.api.start(sso_container)
        self.inspect_after_start()


class DeployXircleFeebackBundle(DeploymentComponent):
    def create(self):
        print('Start deploying of XircleFeebackBundle container.\r\n')


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
                # c.inspect_after_start()
