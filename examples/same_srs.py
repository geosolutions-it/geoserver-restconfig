#!/usr/bin/env python

'''
gsconfig is a python library for manipulating a GeoServer instance via the GeoServer RESTConfig API.

The project is distributed under a MIT License .
'''

__author__ = "David Winslow"
__copyright__ = "Copyright 2012-2018 Boundless, Copyright 2010-2012 OpenPlans"
__license__ = "MIT"

from geoserver.catalog import Catalog

cat = Catalog("http://localhost:8080/geoserver/rest", "admin", "geoserver")

resources = cat.get_resources(workspaces='sf')
if len(resources) > 0:
    assert all(r.projection == "EPSG:26713" for r in resources)
