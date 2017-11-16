import datetime
from time import sleep
import MySQLdb
from helpers.color_print import ColorPrint
from config import CONTAINERS

cprint = ColorPrint()


def get_mysql_connection():
    conn = MySQLdb.connect(
        host=CONTAINERS['MYSQL']['NETWORK']['IPV4_ADDRESS'],
        user='root',
        passwd=CONTAINERS['MYSQL']['MYSQL_ROOT_PASSWORD'],
        port=CONTAINERS['MYSQL']['DOCKER_PORT']
    )
    conn.autocommit(True)

    return conn


def raw_sql(sql):
    _conn = get_mysql_connection()
    try:
        cur = _conn.cursor(MySQLdb.cursors.DictCursor)
        cur.execute(sql)
        res = cur.fetchall()  # tuple of dicts
        return res
    finally:
        _conn.close()


def wait_for_mysql_starts():
    wait_timeout = datetime.datetime.now() + datetime.timedelta(
        seconds=CONTAINERS['MYSQL']['WAIT_FOR_START_TIMEOUT'])
    cprint.orange('Waiting for MySQL server starts...')
    while True:
        if datetime.datetime.now() >= wait_timeout:
            cprint.red('Wait timeout expired. MySQL server does not respond!')
            break
        try:
            result = raw_sql("SELECT VERSION() AS mysql_ver;")
            cprint.green(
                str.format('MySQL {} is running.', result[0]['mysql_ver']))
            break
        except Exception:
            sleep(1)
            cprint.yellow('Waiting...')
