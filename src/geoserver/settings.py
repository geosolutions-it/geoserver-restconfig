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

from geoserver.support import (
    ResourceInfo, StaticResourceInfo,
    xml_property,
    read_bool, read_float, read_int, read_string,
    write_bool, write_float, write_int, write_string)


def write_subclass(sbc):
    def write(builder, sbc):
        sbc.serialize_all(builder)
    return write


class Contact(StaticResourceInfo):
    resource_type = "contact"

    def __init__(self, dom):
        super(Contact, self).__init__()
        self.dom = dom

    addressCity = xml_property("addressCity", read_string)
    addressCountry = xml_property("addressCountry", read_string)
    addressType = xml_property("addressType", read_string)
    contactEmail = xml_property("contactEmail", read_string)
    contactOrganization = xml_property("contactOrganization", read_string)
    contactPerson = xml_property("contactPerson", read_string)
    contactPosition = xml_property("contactPosition", read_string)

    writers = {
        "addressCity": write_string("addressCity"),
        "addressCountry": write_string("addressCountry"),
        "addressType": write_string("addressType"),
        "contactEmail": write_string("contactEmail"),
        "contactOrganization": write_string("contactOrganization"),
        "contactPerson": write_string("contactPerson"),
        "contactPosition": write_string("contactPosition")
    }


class Settings(StaticResourceInfo):
    resource_type = "settings"

    def __init__(self, dom):
        super(Settings, self).__init__()
        self.dom = dom

    id = xml_property("id", read_string)
    contact = xml_property("contact", Contact)
    charset = xml_property("charset", read_string)
    numDecimals = xml_property("numDecimals", read_int)
    onlineResource = xml_property("onlineResource", read_string)
    verbose = xml_property("verbose", read_bool)
    verboseExceptions = xml_property("verboseExceptions", read_bool)
    localWorkspaceIncludesPrefix = xml_property("localWorkspaceIncludesPrefix", read_bool)

    writers = {
        "id": write_string("id"),
        "contact": write_subclass("contact"),
        "charset": write_string("charset"),
        "numDecimals": write_int("numDecimals"),
        "onlineResource": write_string("onlineResource"),
        "verbose": write_bool("verbose"),
        "verboseExceptions": write_bool("verboseExceptions"),
        "localWorkspaceIncludesPrefix": write_bool("localWorkspaceIncludesPrefix"),
    }


class Jai(StaticResourceInfo):

    def __init__(self, dom):
        super(Jai, self).__init__()
        self.dom = dom

    resource_type = "jai"

    allowInterpolation = xml_property("allowInterpolation", read_bool)
    recycling = xml_property("recycling", read_bool)
    tilePriority = xml_property("tilePriority", read_int)
    tileThreads = xml_property("tileThreads", read_int)
    memoryCapacity = xml_property("memoryCapacity", read_float)
    memoryThreshold = xml_property("memoryThreshold", read_float)
    imageIOCache = xml_property("imageIOCache", read_bool)
    pngAcceleration = xml_property("pngAcceleration", read_bool)
    jpegAcceleration = xml_property("jpegAcceleration", read_bool)
    allowNativeMosaic = xml_property("allowNativeMosaic", read_bool)
    allowNativeWarp = xml_property("allowNativeWarp", read_bool)

    writers = {
        "allowInterpolation": write_bool("allowInterpolation"),
        "recycling": write_bool("recycling"),
        "tilePriority": write_int("tilePriority"),
        "tileThreads": write_int("tileThreads"),
        "memoryCapacity": write_float("memoryCapacity"),
        "memoryThreshold": write_float("memoryThreshold"),
        "imageIOCache": write_bool("imageIOCache"),
        "pngAcceleration": write_bool("pngAcceleration"),
        "jpegAcceleration": write_bool("jpegAcceleration"),
        "allowNativeMosaic": write_bool("allowNativeMosaic"),
        "allowNativeWarp": write_bool("allowNativeWarp")
    }


class CoverageAccess(StaticResourceInfo):

    def __init__(self, dom):
        super(CoverageAccess, self).__init__()
        self.dom = dom

    resource_type = "coverageAccess"

    maxPoolSize = xml_property("maxPoolSize", read_int)
    corePoolSize = xml_property("corePoolSize", read_int)
    keepAliveTime = xml_property("keepAliveTime", read_int)
    queueType = xml_property("queueType", read_string)
    imageIOCacheThreshold = xml_property("imageIOCacheThreshold", read_int)

    writers = {
        "maxPoolSize": write_int("maxPoolSize"),
        "corePoolSize": write_int("corePoolSize"),
        "keepAliveTime": write_int("keepAliveTime"),
        "queueType": write_string("queueType"),
        "imageIOCacheThreshold": write_int("imageIOCacheThreshold")
    }


class GlobalSettings(ResourceInfo):
    resource_type = "global"
    save_method = "put"

    def __init__(self, catalog):
        super(GlobalSettings, self).__init__()
        self._catalog = catalog

    @property
    def catalog(self):
        return self._catalog

    @property
    def href(self):
        return urljoin(
            f"{self.catalog.service_url}/",
            "settings"
        )

    settings = xml_property("settings", Settings)
    jai = xml_property("jai", Jai)
    coverageAccess = xml_property("coverageAccess", CoverageAccess)
    updateSequence = xml_property("updateSequence", lambda x: int(x.text))
    featureTypeCacheSize = xml_property("featureTypeCacheSize", lambda x: int(x.text))
    globalServices = xml_property("globalServices", lambda x: x.text.lower() == 'true')
    xmlPostRequestLogBufferSize = xml_property("xmlPostRequestLogBufferSize", lambda x: int(x.text))

    writers = {
        'settings': write_subclass("settings"),
        'jai': write_subclass("jai"),
        'coverageAccess': write_subclass("coverageAccess"),
        'featureTypeCacheSize': write_int("featureTypeCacheSize"),
        'globalServices': write_bool("globalServices"),
        'xmlPostRequestLogBufferSize': write_int("xmlPostRequestLogBufferSize")
    }

    def __repr__(self):
        return f"settings @ {self.href}"
