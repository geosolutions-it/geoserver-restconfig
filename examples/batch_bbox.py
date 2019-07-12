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

native_bbox = ['589434.856', '4914006.338', '609527.21', '4928063.398', 'EPSG:26713']
latlon_bbox = ['-103.877', '44.371', '-103.622', '44.5', 'EPSG:4326']

for rs in cat.get_resources(workspaces='sf'):
    rs.native_bbox = native_bbox
    rs.latlon_bbox = latlon_bbox
    cat.save(rs)
