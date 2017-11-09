from abc import ABC, abstractmethod
from time import sleep
from io import BytesIO
import json
import os
import docker
from helpers.color_print import ColorPrint
from config import CONTAINERS, GIT_REPOSITORIES, HOME_DEPLOYMENT_DIR

client = docker.from_env()
cprint = ColorPrint()


def prepare_images():
    """ Pull images if they're doesn't exists locally. """
    images_to_prepare = [
        v['IMAGE_NAME'] for k, v in CONTAINERS.items()
        if 'IMAGE_NAME' in v.keys()
    ]
    for image_name in images_to_prepare:
        for s in client.api.pull(image_name, stream=True):
            resp = json.loads(s.decode().replace('\r\n', ''))
            if 'progressDetail' not in resp.keys():
                print(str.format('[{}]', resp['status']))
            else:
                print(str.format('[{}] Progress: {}',
                                 resp['status'], resp['progressDetail']))


# def prepare_network():
#     for net in client.api.networks():
#         if net['Name'] not in ('bridge', 'host', 'none'):
#             client.api.remove_network(net['Id'])
#
#     client.api.create_network("deployer_network", driver="bridge")


class DeploymentComponent(ABC):

    def __init__(
            self, container_name, image_name, docker_port, localhost_port):
        self.image_name = image_name
        self.container_name = container_name
        self.localhost_port = localhost_port
        self.docker_port = docker_port

    def inspect_after_start(self):
        inspect = client.api.inspect_container(self.container_name)
        cprint.blue(
            "{} (id: {}) started.\nIt's available at IP {} ({}).\r\n".format(
                self.container_name,
                inspect['Id'],
                inspect['NetworkSettings']['IPAddress'],
                inspect['NetworkSettings']['Ports']
            ))

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

    @abstractmethod
    def create(self):
        pass


class DeployMySQL(DeploymentComponent):

    def __init__(self, container_name, image_name, docker_port, localhost_port,
                 mysql_pwd):
        self._mysql_pwd = mysql_pwd
        super().__init__(
            container_name, image_name, docker_port, localhost_port)

    def create(self):
        print('\r\nStart deploying of MySQL container.\r\n')
        mysql_container = client.api.create_container(
            name=self.container_name,
            image=self.image_name,
            environment={
                'MYSQL_ROOT_PASSWORD': self._mysql_pwd,
            },
            ports=[self.docker_port],
            host_config=client.api.create_host_config(port_bindings={
                self.docker_port: self.localhost_port
            }),
            hostname=self.container_name
        )
        client.api.start(mysql_container)

        # client.api.connect_container_to_network(
        #     net_id='deployer_network', container=self.container_name,
        #     aliases=[self.container_name]
        #     # links={
        #     #     '1_deployer_elastic_search': 'elasticsearch',
        #     #     '1_deployer_mongodb': 'mongodb'
        #     # }
        # )

        # TODO: when (if) finished - move this to composite execute
        self.inspect_after_start()

        print('Waiting for MySQL server starts...\r\n')
        sleep(7)

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
        rabbitmq_container = client.api.create_container(
            name=self.container_name,
            image=self.image_name,
            environment={},
            ports=[self.docker_port],
            host_config=client.api.create_host_config(port_bindings={
                self.docker_port: self.localhost_port
            }),
            hostname=self.container_name,
            user='root'
        )
        client.api.start(rabbitmq_container)

        self.inspect_after_start()


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
            name=self.container_name,
            image=self.image_name,
            environment={
                'GRAYLOG_WEB_ENDPOINT_URI': 'http://127.0.0.1:9000/api'
            },
            ports=[self.docker_port],
            host_config=client.api.create_host_config(port_bindings={
                self.docker_port: self.localhost_port,
                '12201/udp': '12201/udp',
            }),
        )
        client.api.start(graylog_container)

        self.inspect_after_start()


class DeployFeedbackApi(DeploymentComponent):

    def manage_access_code(self):
        # TODO: refactor this
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

        local_dir = GIT_REPOSITORIES['feedback-api-python']['local_dir']

        feedback_container = client.api.create_container(
            image='{}_image'.format(self.container_name),
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
                'MYSQL_HOST': '172.17.0.2',  # 172.17.0.2
                'SSO_CONTAINER': 'deployer_sso',
                'SSO_PORT': '10180',
                'SSO_IP': '172.17.0.4',
                'MYSQL_PWD': 'root',
                'PORT_TO_DEPLOY': '10181',
                'RABBIT_MQ_IP': '172.17.0.3',
            }
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

        self.manage_access_code()

        self.inspect_after_start()


class DeploySSO(DeploymentComponent):

    def create(self):
        print('\r\nStart deploying of SSO container.\r\n')
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

        local_dir = GIT_REPOSITORIES['sso']['local_dir']

        sso_container = client.api.create_container(
            image='{}_image'.format(self.container_name),
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
                'MYSQL_HOST': '172.17.0.2',
                'MYSQL_PWD': 'root'
            },
            hostname='sso',
            user='root',
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

        self.inspect_after_start()


class DeployXircleFeebackBundle(DeploymentComponent):
    def create(self):
        print('Start deploying of XircleFeebackBundle container.\r\n')

        local_dir = GIT_REPOSITORIES['feedback_ui']['local_dir']

        # Create local config.js
        xircl_fb_config = """
/* -----------------------------------------------------------------
//
// `config.js` generated for Docker container
//
// ----------------------------------------------------------------- */

// SSO URL
window.ssoApiUrl = 'http://{sso_url}/api/';

// Feedback REST API URL
window.feedbackV2ApiUrl = 'http://{fbapi_url}/';

// Xircl BaseURL
window.xirclxirclfeedback = '/';

// Analytics
window.googleAnalyticsEnabled = false;
window.uxMetricsEnabled = false;""".format(
            sso_url='172.17.0.4', fbapi_url='172.17.0.3'
        )

        with open(
            os.path.join(local_dir, 'Resources', 'public', 'js', 'config.js'),
            mode='w'
        ) as config_js:
            config_js.write(xircl_fb_config)

        with open(
            'docker_files/xircl_fb_bundle_local_Dockerfile', mode="r"
        ) as dockerfile:
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



        xircl_fb_container = client.api.create_container(
            image='{}_image'.format(self.container_name),
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
                # c.inspect_after_start()
