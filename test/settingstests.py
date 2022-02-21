from copy import deepcopy
import unittest
import string
import random
import os
import subprocess
import re
import time
from geoserver.catalog import Catalog
from geoserver.support import StaticResourceInfo
from .utils import DBPARAMS
from .utils import GSPARAMS

try:
    import psycopg2
    # only used for connection sanity if present
    conn = psycopg2.connect(('dbname=%(database)s user=%(user)s password=%(passwd)s'
                             ' port=%(port)s host=%(host)s'
                             ) % DBPARAMS)
except ImportError:
    pass

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


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.cat = Catalog(GSPARAMS['GSURL'], username=GSPARAMS['GSUSER'], password=GSPARAMS['GSPASSWORD'])
        self.bkp_cat = Catalog(GSPARAMS['GSURL'], username=GSPARAMS['GSUSER'], password=GSPARAMS['GSPASSWORD'])
        self.gs_version = self.cat.get_short_version()
        self.bkp_global_settings = deepcopy(self.bkp_cat.get_global_settings())
        self.global_enums = {}
        self.settings_enums = {}
        self.contact_enums = {}
        self.coverageAccess_enums = {"queueType": ["UNBOUNDED", "DIRECT"]}
        self.jai_enums = {}

    def tearDown(self) -> None:
        self.bkp_global_settings.dirty_all()
        self.bkp_cat.save(self.bkp_global_settings)

    def test_get_settings(self):
        glob = self.cat.get_global_settings()
        self.assertIsNotNone(glob)

    def test_set_global(self):

        test_class = self.cat.get_global_settings()

        # test boolean
        attrs = [k for k, v in test_class.writers.items() if isinstance(getattr(test_class, k), bool)]
        enums = getattr(self, f"{test_class.resource_type}_enums")
        for attr in attrs:
            setattr(test_class, attr, False)
            self.cat.save(test_class)
            test_class.refresh()
            self.assertIsNone(test_class.dirty.get(attr), msg=f"Attribute {attr} still in dirty list")
            self.assertFalse(getattr(test_class, attr))
            setattr(test_class, attr, True)
            self.cat.save(test_class)
            test_class.refresh()
            self.assertIsNone(test_class.dirty.get(attr), msg=f"Attribute {attr} still in dirty list")
            self.assertTrue(getattr(test_class, attr), msg=f"Invalid value for object {attr}")

        # test string
        attrs = [k for k, v in test_class.writers.items() if
                 isinstance(getattr(test_class, k), str) and k not in enums.keys()]
        for attr in attrs:
            test_str = ''.join(random.sample(string.ascii_lowercase, 10))
            setattr(test_class, attr, test_str)
            self.cat.save(test_class)
            test_class.refresh()
            self.assertIsNone(test_class.dirty.get(attr), msg=f"Attribute {attr} still in dirty list")
            self.assertEqual(getattr(test_class, attr), test_str, msg=f"Invalid value for object {attr}")

        # test enums
        attrs = [k for k in enums.keys()]
        for attr in attrs:
            test_str = enums[attr][random.randint(0, len(enums[attr]) - 1)]
            setattr(test_class, attr, test_str)
            self.cat.save(test_class)
            test_class.refresh()
            self.assertIsNone(test_class.dirty.get(attr), msg=f"Attribute {attr} still in dirty list")
            self.assertEqual(getattr(test_class, attr), test_str, msg=f"Invalid value for object {attr}")

        # test int
        attrs = [k for k in test_class.writers.keys() if isinstance(getattr(test_class, k), int) and not isinstance(getattr(test_class, k), bool)]
        for attr in attrs:
            test_int = random.randint(1, 20)
            setattr(test_class, attr, test_int)
            self.cat.save(test_class)
            test_class.refresh()
            self.assertIsNone(test_class.dirty.get(attr), msg=f"Attribute {attr} still in dirty list")
            self.assertEqual(getattr(test_class, attr), test_int, msg=f"Invalid value for object {attr}")

    def test_set_settings(self):
        glob = self.cat.get_global_settings()
        subclasses = [x for x in glob.writers.keys() if issubclass(type(getattr(glob, x)), StaticResourceInfo)]

        for subcls in subclasses:

            # test boolean
            attrs = [k for k, v in getattr(glob, subcls).writers.items() if isinstance(getattr(getattr(glob, subcls), k), bool)]
            enums = getattr(self, f"{getattr(glob, subcls).resource_type}_enums")

            for attr in attrs:
                setattr(getattr(glob, subcls), attr, False)
                self.cat.save(glob)
                glob.refresh()
                self.assertIsNone(getattr(glob, subcls).dirty.get(attr), msg=f"Attribute {attr} still in dirty list")
                self.assertFalse(getattr(getattr(glob, subcls), attr))
                setattr(getattr(glob, subcls), attr, True)
                self.cat.save(glob)
                glob.refresh()
                self.assertIsNone(getattr(glob, subcls).dirty.get(attr), msg=f"Attribute {attr} still in dirty list")
                self.assertTrue(getattr(getattr(glob, subcls), attr), msg=f"Invalid value for object {attr}")

            # test string
            attrs = [k for k, v in getattr(glob, subcls).writers.items() if
                     isinstance(getattr(getattr(glob, subcls), k), str) and k not in enums.keys()]
            for attr in attrs:
                test_str = ''.join(random.sample(string.ascii_lowercase, 10))
                setattr(getattr(glob, subcls), attr, test_str)
                self.cat.save(glob)
                glob.refresh()
                self.assertIsNone(getattr(glob, subcls).dirty.get(attr), msg=f"Attribute {attr} still in dirty list")
                self.assertEqual(getattr(getattr(glob, subcls), attr), test_str,
                                 msg=f"Invalid value for object {attr}")

            # test enums
            attrs = [k for k in enums.keys()]
            for attr in attrs:
                test_str = enums[attr][random.randint(0, len(enums[attr]) - 1)]
                setattr(getattr(glob, subcls), attr, test_str)
                self.cat.save(glob)
                glob.refresh()
                self.assertIsNone(getattr(glob, subcls).dirty.get(attr), msg=f"Attribute {attr} still in dirty list")
                self.assertEqual(getattr(getattr(glob, subcls), attr), test_str,
                                 msg=f"Invalid value for object {attr}")

            # test int
            attrs = [k for k in getattr(glob, subcls).writers.keys() if isinstance(getattr(getattr(glob, subcls), k), int) and not isinstance(getattr(getattr(glob, subcls), k), bool)]
            for attr in attrs:
                test_int = random.randint(1, 20)
                setattr(getattr(glob, subcls), attr, test_int)
                self.cat.save(glob)
                glob.refresh()
                self.assertIsNone(getattr(glob, subcls).dirty.get(attr), msg=f"Attribute {attr} still in dirty list")
                self.assertEqual(getattr(getattr(glob, subcls), attr), test_int,
                                 msg=f"Invalid value for object {attr}")
