# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright 2019, GeoSolutions Sas.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE.txt file in the root directory of this source tree.
#
#########################################################################
try:
    from urllib.parse import urljoin
except:
    from urlparse import urljoin

from geoserver.support import ResourceInfo, xml_property, write_bool


def workspace_from_index(catalog, node):
    name = node.find("name")
    return Workspace(catalog, name.text)


class Workspace(ResourceInfo):
    resource_type = "workspace"

    def __init__(self, catalog, name):
        super(Workspace, self).__init__()
        self._catalog = catalog
        self._name = name

    @property
    def catalog(self):
        return self._catalog

    @property
    def name(self):
        return self._name

    @property
    def href(self):
        return urljoin(
            "{}/".format(self.catalog.service_url),
            "workspaces/{}.xml".format(self.name)
        )

    @property
    def coveragestore_url(self):
        return urljoin(
            "{}/".format(self.catalog.service_url),
            "workspaces/{}/coveragestores.xml".format(self.name)
        )

    @property
    def datastore_url(self):
        return urljoin(
            "{}/".format(self.catalog.service_url),
            "workspaces/{}/datastores.xml".format(self.name)
        )

    @property
    def wmsstore_url(self):
        return urljoin(
            "{}/".format(self.catalog.service_url),
            "workspaces/{}/wmsstores.xml".format(self.name)
        )

    enabled = xml_property("enabled", lambda x: x.lower() == 'true')
    writers = {
        'enabled': write_bool("enabled")
    }

    def __repr__(self):
        return "{} @ {}".format(self.name, self.href)
