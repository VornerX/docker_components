from abc import ABC, abstractmethod
from time import sleep
from io import BytesIO
import json
import os
import docker
from docker import types
from helpers.color_print import ColorPrint
from config import (
    DOCKER_NETWORK, CONTAINERS, GIT_REPOSITORIES, HOME_DEPLOYMENT_DIR
)

client = docker.from_env()
cprint = ColorPrint()


def prepare_images():
    """ Pull images if they're doesn't exists locally. """
    images_to_prepare = [
        v['IMAGE_NAME'] for k, v in CONTAINERS.items()
        if 'IMAGE_NAME' in v.keys()
    ]
    for image_name in images_to_prepare:
        if image_name != 'custom':
            for s in client.api.pull(image_name, stream=True):
                resp = json.loads(s.decode().replace('\r\n', ''))
                if 'progressDetail' not in resp.keys():
                    print(str.format('[{}]', resp['status']))
                else:
                    print(str.format('[{}] Progress: {}',
                                     resp['status'], resp['progressDetail']))


def prepare_network():
    for net in client.api.networks():
        if net['Name'] in (DOCKER_NETWORK['NETWORK_NAME'], 'deployer_Network'):
            client.api.remove_network(net['Id'])

    ipam_pool = docker.types.IPAMPool(
        subnet=DOCKER_NETWORK['SUBNET'],
        gateway=DOCKER_NETWORK['GATEWAY']
    )

    ipam_config = docker.types.IPAMConfig(
        pool_configs=[ipam_pool]
    )

    client.api.create_network(
        DOCKER_NETWORK['NETWORK_NAME'], driver="bridge", ipam=ipam_config)


class DeploymentComponent(ABC):

    def __init__(
            self, container_name, image_name, docker_port, localhost_port):
        self.image_name = image_name
        self.container_name = container_name
        self.localhost_port = localhost_port
        self.docker_port = docker_port
        self.report_string = None

    def inspect_after_start(self):
        inspect = client.api.inspect_container(self.container_name)
        net_settings = inspect.get('NetworkSettings')

        ipv4_address = net_settings[
            'Networks'][DOCKER_NETWORK['NETWORK_NAME']]['IPAddress']

        local_ports = []
        for port in net_settings['Ports'].keys():
            if net_settings['Ports'][port] is not None:
                for p in net_settings['Ports'][port]:
                    local_ports.append(p['HostPort'])

        docker_ports = [
            p.replace('/tcp', '') for p in net_settings['Ports'].keys()]

        create_datetime = inspect['Created'].split('.')[0].replace('T', ' ')

        self.report_string = str.format(
            "Container '{}' successfully deployed\n"
            "Container id: {}\n"
            "Available at localhost as: http://{}:{}\n"
            "Available inside Docker as: http://{}:{}\n"
            "Create time: {}\r\n",
            self.container_name,
            inspect['Id'],
            'localhost',
            ', '.join(local_ports),
            ipv4_address,
            ', '.join(docker_ports),
            create_datetime
        )

        cprint.blue(self.report_string)

    def exec_cmd(self, container_name, cmd):

        container = client.containers.get(container_name)

        if isinstance(cmd, list):
            response = container.exec_run(
                cmd="bash -c '" + " ".join(cmd) + "'", stream=True)
            for r in response:
                cprint.yellow(r.decode())

        elif isinstance(cmd, str):
            response = container.exec_run(
                cmd=str.format("bash -c '{}'", cmd), stream=True)
            for r in response:
                cprint.yellow(r.decode())
        else:
            raise TypeError("'cmd' parameter must me list or str.")

    def build_links(self, container_name=None):
        con_name = container_name if container_name else self.container_name
        links = {
            settings['CONTAINER_NAME']: settings['CONTAINER_NAME']
            for srv, settings in CONTAINERS.items()
            if settings['CONTAINER_NAME'] != con_name
        }

        return links

    def build_image_from_dockerfile(self, dockerfile):
        """ Builds image and returns a tag for using in container creation """
        with open(os.path.join('docker_files', dockerfile),
                  mode="r") as dockerfile:
            tag = str.format('{}_image', self.container_name)
            f = BytesIO(dockerfile.read().encode('utf-8'))
            try:
                for line in client.api.build(
                    fileobj=f,
                    nocache=False,
                    rm=True,
                    tag=tag,
                    decode=True,
                    pull=True
                ):
                    line = line.get('stream')
                    if line is not None:
                        cprint.green(line)

                return tag

            except Exception:
                raise IOError("Invalid Dockerfile!")

    @abstractmethod
    def create(self):
        pass


class DeployMySQL(DeploymentComponent):
    def create(self):
        print('\r\nStart deploying of MySQL container.\r\n')

        networking_config = client.api.create_networking_config({
            DOCKER_NETWORK['NETWORK_NAME']: client.api.create_endpoint_config(
                ipv4_address=CONTAINERS['MYSQL']['NETWORK']['IPV4_ADDRESS'],
                aliases=CONTAINERS['MYSQL']['NETWORK']['HOSTNAME'],
                links=self.build_links()
            )
        })

        mysql_container = client.api.create_container(
            name=self.container_name,
            image=self.image_name,
            environment={
                'MYSQL_ROOT_PASSWORD': CONTAINERS['MYSQL'][
                    'MYSQL_ROOT_PASSWORD'],
            },
            ports=[self.docker_port],
            host_config=client.api.create_host_config(port_bindings={
                self.docker_port: self.localhost_port
            }),
            hostname=self.container_name,
            domainname=self.container_name,
            networking_config=networking_config
        )
        client.api.start(mysql_container)

        print('Waiting for MySQL server starts...\r\n')
        sleep(7)

        # TODO: move this to separate method with mysqlclient actions
        for d in ('sso', 'feedback', 'feedback_default', 'demo'):
            self.exec_cmd(
                container_name=self.container_name,
                cmd=str.format(
                    'mysql -u root -e "create database if not exists {};"', d)
            )


        # client.api.kill(mysql_container_id)
        # client.api.wait(mysql_container_id)
        # client.api.remove_container(mysql_container_id)
        # print(mysql_container)


class DeployRabbitMQ(DeploymentComponent):
    def create(self):
        networking_config = client.api.create_networking_config({
            DOCKER_NETWORK['NETWORK_NAME']: client.api.create_endpoint_config(
                ipv4_address=CONTAINERS['RABBITMQ']['NETWORK']['IPV4_ADDRESS'],
                aliases=CONTAINERS['RABBITMQ']['NETWORK']['HOSTNAME'],
                links=self.build_links()
            )
        })
        rabbitmq_container = client.api.create_container(
            name=self.container_name,
            image=self.image_name,
            environment={},
            ports=[self.docker_port],
            host_config=client.api.create_host_config(port_bindings={
                self.docker_port: self.localhost_port
            }),
            hostname=self.container_name,
            user='root',
            domainname=self.container_name,
            networking_config=networking_config
        )
        client.api.start(rabbitmq_container)


# class DeployGraylog(DeploymentComponent):
#     def create(self):
#         print('Start deploying of Graylog container.\r\n')
#
#         # elastic search
#         es_container = client.api.create_container(
#             name='1_deployer_elastic_search',
#             image='elasticsearch:2',
#             environment={},
#             ports=[9200],
#             host_config=client.api.create_host_config(port_bindings={
#                 9200: 9200
#             }),
#         )
#         client.api.start(es_container)
#
#         # mongodb
#         mongodb_container = client.api.create_container(
#             name='1_deployer_mongodb',
#             image='mongo:2.6',
#             environment={},
#             ports=[27017],
#             host_config=client.api.create_host_config(port_bindings={
#                 27017: 27020
#             }),
#         )
#         client.api.start(mongodb_container)
#
#         # graylog
#         graylog_container = client.api.create_container(
#             name=self.container_name,
#             image=self.image_name,
#             environment={
#                 'GRAYLOG_WEB_ENDPOINT_URI': 'http://127.0.0.1:9000/api'
#             },
#             ports=[self.docker_port],
#             host_config=client.api.create_host_config(port_bindings={
#                 self.docker_port: self.localhost_port,
#                 '12201/udp': '12201/udp',
#             }),
#         )
#         client.api.start(graylog_container)
#
#         self.inspect_after_start()


class DeployFeedbackApi(DeploymentComponent):

    def manage_access_code(self):
        # TODO: Use mysqlclient instead of this command line shit
        cprint.green('Generating access code')

        check_access_code_cmd = """mysql --skip-column-names --silent -e "select token from sso.app_token where id=1;" """

        access_code = None

        response = self.exec_cmd(self.container_name, check_access_code_cmd)
        if response:
            for r in response:
                if r:
                    access_code = r.decode()

        if not access_code:
            self.exec_cmd(
                'deployer_sso', 'sso-mgm accesscode -y -e 1 -a feedback')

        response = self.exec_cmd(self.container_name, check_access_code_cmd)
        if response:
            for r in response:
                if r:
                    access_code = r.decode()

        if not access_code:
            raise Exception('Access code empty. Something goes wrong.')

        access_code_filepath = os.path.join(
            HOME_DEPLOYMENT_DIR, 'feedback_api', '.sso_access_code')

        with open(file=access_code_filepath, mode='w') as access_code_file:
            access_code_file.write(access_code)

        response = self.exec_cmd(
            self.container_name, 'fbapi-mgm generate_token')

        for r in response:
            cprint.cyan(r.decode())

    def create(self):
        print('Start deploying of Feedback API container.\r\n')

        # TODO: move Dockerfile processing to separate method at base class
        # with open('docker_files/feedback_local_Dockerfile',
        #           mode="r") as dockerfile:
        #     f = BytesIO(dockerfile.read().encode('utf-8'))
        #     try:
        #         for line in client.api.build(
        #             fileobj=f,
        #             nocache=False,
        #             rm=True,
        #             tag='{}_image'.format(self.container_name),
        #             decode=True,
        #             pull=True
        #         ):
        #             line = line.get('stream')
        #             if line is not None:
        #                 cprint.green(line)
        #     except Exception:
        #         raise IOError("Invalid Dockerfile!")

        networking_config = client.api.create_networking_config({
            DOCKER_NETWORK['NETWORK_NAME']: client.api.create_endpoint_config(
                ipv4_address=CONTAINERS[
                    'FEEDBACK_API']['NETWORK']['IPV4_ADDRESS'],
                aliases=CONTAINERS['FEEDBACK_API']['NETWORK']['HOSTNAME'],
                links=self.build_links()
            )
        })

        image_tag = self.build_image_from_dockerfile(
            'feedback_local_Dockerfile')

        local_dir = GIT_REPOSITORIES['feedback-api-python']['local_dir']

        feedback_container = client.api.create_container(
            image=image_tag,
            name=self.container_name,
            stdin_open=True, tty=True,
            ports=[self.docker_port],
            host_config=client.api.create_host_config(
                port_bindings={self.docker_port: self.localhost_port},
                binds={
                    local_dir: {
                        'bind': '/feedback-api-python',
                        'mode': 'rw',
                    }
                }
            ),
            environment={
                'CONTAINER': 'feedback',  # db name
                'GRAYLOG_IP': 'localhost',
                'MYSQL_HOST': CONTAINERS['MYSQL']['NETWORK']['HOSTNAME'][0],
                'SSO_CONTAINER': CONTAINERS['SSO']['CONTAINER_NAME'],
                'SSO_PORT': CONTAINERS['SSO']['LOCAL_PORT'],
                'SSO_IP': CONTAINERS['SSO']['NETWORK']['HOSTNAME'][0],
                'MYSQL_PWD': CONTAINERS['MYSQL']['MYSQL_ROOT_PASSWORD'],
                'PORT_TO_DEPLOY': CONTAINERS['FEEDBACK_API']['LOCAL_PORT'],
                'RABBIT_MQ_IP': CONTAINERS[
                    'RABBITMQ']['NETWORK']['HOSTNAME'][0],
            },
            networking_config=networking_config
        )

        client.api.start(feedback_container)

        prepare_app_commands = [
            "cd feedback-api-python;",
            "rm -rf feedback_api/dist;",
            "rm -rf feedback_api/.config;",
            "cp feedback_api/autodeployment/local_nginx.conf /etc/nginx/conf.d/;",
            "cp feedback_api/autodeployment/crontab_local /etc/crontab;",
            "python2.7 /get-pip.py;",
            "python3.4 setup.py venv --project=feedback_api;",
            "pip2.7 install fabric;",
            "source feedback_api/dist/env/bin/activate;",
            "python setup.py develop --project=feedback_api;",
            "python setup.py uncomment_local_config --project=feedback_api;",
            "python feedback_api/autodeployment/update_config_files.py;",
            "fbapi-mgm check;"
        ]
        self.exec_cmd(self.container_name, prepare_app_commands)

        db_commands = [
            "fbapi-mgm migrate contenttypes --database=demo;",
            "fbapi-mgm migrate contenttypes --database=default;",
            "fbapi-mgm migrate model_generic --database=default;",
            "fbapi-mgm migrate model --database=demo;",
            "fbapi-mgm makeunit --db=demo --unitname=local_unit;",
            "fbapi-mgm migrate model --database=demo;"
        ]
        self.exec_cmd(self.container_name, db_commands)

        load_data_commands = [
            "fbapi-mgm loaddata --app model --database demo channel;",
            "fbapi-mgm loaddata --app model --database demo state;",
            "fbapi-mgm loaddata --app model --database demo protocol;",
            "fbapi-mgm loaddata --app model --database demo language;",
            "fbapi-mgm loaddata --app model --database demo entity_lookup;",
            "fbapi-mgm loaddata --app model --database demo deploy_initial_data;",
            "fbapi-mgm makeconfig --db=demo;",
            "fbapi-mgm makequesttype --db=demo;"
        ]
        self.exec_cmd(self.container_name, load_data_commands)

        server_run_commands = [
            "fbapi-mgm collectstatic --noinput;",
            "fbapi-uwsgi start;",
            "nginx;",
            "usr/sbin/crond;",
            "cd /feedback-api-python/feedback_api/autodeployment/;",
            'python2.7 restart_celery.py'
        ]
        self.exec_cmd(self.container_name, server_run_commands)

        # TODO: Finish this
        # self.manage_access_code()


class DeploySSO(DeploymentComponent):

    def create(self):
        print('\r\nStart deploying of SSO container.\r\n')

        networking_config = client.api.create_networking_config({
            DOCKER_NETWORK['NETWORK_NAME']: client.api.create_endpoint_config(
                ipv4_address=CONTAINERS['SSO']['NETWORK']['IPV4_ADDRESS'],
                aliases=CONTAINERS['SSO']['NETWORK']['HOSTNAME'],
                links=self.build_links()
            )
        })

        image_tag = self.build_image_from_dockerfile('sso_local_Dockerfile')

        local_dir = GIT_REPOSITORIES['sso']['local_dir']

        sso_container = client.api.create_container(
            image=image_tag,
            name=self.container_name,
            stdin_open=True, tty=True,
            ports=[self.docker_port],
            host_config=client.api.create_host_config(
                port_bindings={self.docker_port: self.localhost_port},
                binds={
                    local_dir: {
                        'bind': '/sso',
                        'mode': 'rw',
                    }
                }
            ),
            environment={
                # TODO: this shit 'CONTAINER' are linked in Dockerfile from
                # TODO: autodeployment_settings.py inside SSO project.
                # TODO: rename it to DB_NAME or something like this.
                'CONTAINER': 'sso',
                'MYSQL_HOST': CONTAINERS['MYSQL']['NETWORK']['HOSTNAME'][0],
                'MYSQL_PWD': CONTAINERS['MYSQL']['MYSQL_ROOT_PASSWORD']
            },
            hostname='sso',
            user='root',
            networking_config=networking_config
        )

        client.api.start(sso_container)
        # get object by name
        # mysql_container = client.containers.get('deployer_mysql57')
        # client.api.create_network("dev_network", driver="bridge")
        # client.api.connect_container_to_network(
        #     net_id='dev_network', container=sso_container,
        #     links={'deployer_mysql57': 'mysql'}  # name: alias
        # )

        venv_commands = [
            'cd sso;',
            'cp autodeployment/sso_local_nginx.conf /etc/nginx/conf.d/;'
            'python3.4 setup.py venv;',
            'source dist/env/bin/activate;',
            'python setup.py develop;',
            'python setup.py uncomment_local_config_files;',
            'deactivate;'
        ]
        self.exec_cmd(self.container_name, venv_commands)

        deploy_commands = [
            'cd sso/autodeployment;',
            'sso-mgm check;',
            'sso-mgm migrate;',
            'npm install -g bower && sso-mgm bower_install -- --allow-root;',
            'sso-mgm loaddata app_local.json;',
            'sso-mgm loaddata app_group_local.json;',
            'sso-mgm loaddata enterprise_local.json;',
            "sso-mgm loaddata user_local.json;"
        ]
        self.exec_cmd(self.container_name, deploy_commands)

        # TODO: in a case of dev environment, maybe start it
        # TODO: with Django development server?
        server_commands = [
            'sso-mgm collectstatic --noinput;',
            'sso-uwsgi start;',
            'nginx'
        ]
        self.exec_cmd(self.container_name, server_commands)


class DeployXircleFeebackBundle(DeploymentComponent):
    def create(self):
        print('Start deploying of XircleFeebackBundle container.\r\n')

        local_dir = GIT_REPOSITORIES['feedback_ui']['local_dir']

        xircl_fb_config = """
/* -----------------------------------------------------------------
//
// `config.js` generated for Docker container
//
// ----------------------------------------------------------------- */

// SSO URL
window.ssoApiUrl = 'http://localhost:{sso_local_port}/api/';

// Feedback REST API URL
window.feedbackV2ApiUrl = 'http://localhost:{fbapi_local_port}/';

// Xircl BaseURL
window.xirclxirclfeedback = '/';

// Analytics
window.googleAnalyticsEnabled = false;
window.uxMetricsEnabled = false;""".format(
            sso_local_port=CONTAINERS['SSO']['LOCAL_PORT'],
            fbapi_local_port=CONTAINERS['FEEDBACK_API']['LOCAL_PORT']
        )

        with open(
            os.path.join(local_dir, 'Resources', 'public', 'js', 'config.js'),
            mode='w'
        ) as config_js:
            config_js.write(xircl_fb_config)

        networking_config = client.api.create_networking_config({
            DOCKER_NETWORK['NETWORK_NAME']: client.api.create_endpoint_config(
                ipv4_address=CONTAINERS[
                    'XIRCL_FB_BUNDLE']['NETWORK']['IPV4_ADDRESS'],
                aliases=CONTAINERS['XIRCL_FB_BUNDLE']['NETWORK']['HOSTNAME'],
                links=self.build_links()
            )
        })

        image_tag = self.build_image_from_dockerfile(
            'xircl_fb_bundle_local_Dockerfile')

        xircl_fb_container = client.api.create_container(
            image=image_tag,
            name=self.container_name,
            stdin_open=True, tty=True,
            ports=[self.docker_port],
            host_config=client.api.create_host_config(
                port_bindings={self.docker_port: self.localhost_port},
                binds={
                    local_dir: {
                        'bind': '/XircleFeedbackBundle',
                        'mode': 'rw',
                    }
                }
            ),
            hostname='xircl_fb',
            user='root',
            networking_config=networking_config
        )

        client.api.start(xircl_fb_container)


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
                c.inspect_after_start()

            report = '\n------------------------------------------'.join(
                [c.report_string for c in self.components]
            )

            cprint.cyan(report)