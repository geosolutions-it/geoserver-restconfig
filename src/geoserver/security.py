# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright 2019, GeoSolutions Sas.
# Jendrusk also was here
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE.txt file in the root directory of this source tree.
#
#########################################################################
try:
    from urllib.parse import urljoin
except BaseException:
    from urlparse import urljoin

from geoserver.support import ResourceInfo, xml_property, write_bool


def user_from_index(catalog, node):
    user_name = node.find("userName").text
    return User(catalog, user_name)


class User(ResourceInfo):
    resource_type = "user"

    def __init__(self, catalog, user_name):
        super(User, self).__init__()
        self._catalog = catalog
        self._user_name = user_name

    @property
    def catalog(self):
        return self._catalog

    @property
    def user_name(self):
        return self._user_name

    @property
    def href(self):
        return urljoin(
            f"{self.catalog.service_url}/",
            f"security/usergroup/users/{self.user_name}"
        )

    enabled = xml_property("enabled", lambda x: x.lower() == 'true')
    writers = {
        'enabled': write_bool("enabled")
    }

    def __repr__(self):
        return f"{self.user_name} @ {self.href}"
