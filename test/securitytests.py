import unittest
import string
import random
import os
from .utils import DBPARAMS
from .utils import GSPARAMS
import subprocess
import re
import time
from geoserver.catalog import Catalog

if GSPARAMS['GEOSERVER_HOME']:
    dest = GSPARAMS['DATA_DIR']
    data = os.path.join(GSPARAMS['GEOSERVER_HOME'], 'data/release', '')
    if dest:
        os.system(f"rsync -v -a --delete {data} {os.path.join(dest, '')}")
    else:
        os.system(f'git clean -dxf -- {data}')
    os.system(f"curl -XPOST --user '{GSPARAMS['GSUSER']}':'{GSPARAMS['GSPASSWORD']}' '{GSPARAMS['GSURL']}/reload'")

if GSPARAMS['GS_VERSION']:
    subprocess.Popen(["rm", "-rf", f"{GSPARAMS['GS_BASE_DIR']}/gs"]).communicate()
    subprocess.Popen(["mkdir", f"{GSPARAMS['GS_BASE_DIR']}/gs"]).communicate()
    subprocess.Popen(
        [
            "wget",
            "http://central.maven.org/maven2/org/eclipse/jetty/jetty-runner/9.4.5.v20170502/jetty-runner-9.4.5.v20170502.jar",
            "-P", f"{GSPARAMS['GS_BASE_DIR']}/gs"
        ]
    ).communicate()

    subprocess.Popen(
        [
            "wget",
            f"https://build.geoserver.org/geoserver/{GSPARAMS['GS_VERSION']}/geoserver-{GSPARAMS['GS_VERSION']}-latest-war.zip",
            "-P", f"{GSPARAMS['GS_BASE_DIR']}/gs"
        ]
    ).communicate()

    subprocess.Popen(
        [
            "unzip",
            "-o",
            "-d",
            f"{GSPARAMS['GS_BASE_DIR']}/gs",
            f"{GSPARAMS['GS_BASE_DIR']}/gs/geoserver-{GSPARAMS['GS_VERSION']}-latest-war.zip"
        ]
    ).communicate()

    FNULL = open(os.devnull, 'w')

    match = re.compile(r'[^\d.]+')
    geoserver_short_version = match.sub('', GSPARAMS['GS_VERSION']).strip('.')
    if geoserver_short_version >= "2.15" or GSPARAMS['GS_VERSION'].lower() == 'master':
        java_executable = "/usr/local/lib/jvm/openjdk11/bin/java"
    else:
        java_executable = "/usr/lib/jvm/java-8-openjdk-amd64/jre/bin/java"

    print(f"geoserver_short_version: {geoserver_short_version}")
    print(f"java_executable: {java_executable}")
    proc = subprocess.Popen(
        [
            java_executable,
            "-Xmx1024m",
            "-Dorg.eclipse.jetty.server.webapp.parentLoaderPriority=true",
            "-jar", f"{GSPARAMS['GS_BASE_DIR']}/gs/jetty-runner-9.4.5.v20170502.jar",
            "--path", "/geoserver", f"{GSPARAMS['GS_BASE_DIR']}/gs/geoserver.war"
        ],
        stdout=FNULL, stderr=subprocess.STDOUT
    )
    child_pid = proc.pid
    print("Sleep (90)...")
    time.sleep(40)


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.cat = Catalog(GSPARAMS['GSURL'], username=GSPARAMS['GSUSER'], password=GSPARAMS['GSPASSWORD'])
        self.bkp_cat = Catalog(GSPARAMS['GSURL'], username=GSPARAMS['GSUSER'], password=GSPARAMS['GSPASSWORD'])
        self.gs_version = self.cat.get_short_version()
        self.bkp_masterpwd = self.bkp_cat.get_master_pwd()
        self.bkp_my_pwd = self.cat.password

    def tearDown(self) -> None:
        self.bkp_cat.set_master_pwd(self.bkp_masterpwd)
        self.bkp_cat.set_my_pwd(self.bkp_my_pwd)

    def test_get_users(self):
        users = self.cat.get_users()
        self.assertGreater(len(users), 0)

    def test_get_master_pwd(self):
        master_pwd = self.cat.get_master_pwd()
        self.assertIsNotNone(master_pwd)

    def test_set_master_pwd(self):
        test_pwd = ''.join(random.sample(string.ascii_lowercase, 10))
        master_pwd = self.cat.set_master_pwd(new_pwd=test_pwd)
        self.assertIsNotNone(master_pwd)
        self.assertEqual(master_pwd, test_pwd)
        new_master_pwd = self.cat.get_master_pwd()
        self.assertEqual(new_master_pwd, test_pwd)

    def test_set_my_pwd(self):
        test_pwd = ''.join(random.sample(string.ascii_lowercase, 10))
        new_pwd = self.cat.set_my_pwd(new_pwd=test_pwd)
        self.assertIsNotNone(new_pwd)
        self.assertEqual(new_pwd, test_pwd)
        self.assertEqual(self.cat.password, test_pwd)
