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

import os
import logging
from xml.etree.ElementTree import TreeBuilder, tostring
from tempfile import mkstemp
from zipfile import ZipFile
from six import string_types

try:
    from urllib.parse import urljoin, quote, urlencode, urlparse
except ImportError:
    from urlparse import urljoin, urlparse
    from urllib import quote, urlencode

try:
    from past.builtins import basestring
except ImportError:
    pass

logger = logging.getLogger("gsconfig.support")

FORCE_DECLARED = "FORCE_DECLARED"
# The projection handling policy for layers that should use coordinates
# directly while reporting the configured projection to clients.  This should be
# used when projection information is missing from the underlying datastore.


FORCE_NATIVE = "FORCE_NATIVE"
# The projection handling policy for layers that should use the projection
# information from the underlying storage mechanism directly, and ignore the
# projection setting.

REPROJECT = "REPROJECT"
# The projection handling policy for layers that should use the projection
# information from the underlying storage mechanism to reproject to the
# configured projection.


def build_url(base, seg, query=None):
    """
    Create a URL from a list of path segments and an optional dict of query
    parameters.
    """

    def clean_segment(segment):
        """
        Cleans the segment and encodes to UTF-8 if the segment is unicode.
        """
        segment = segment.strip("/")
        if isinstance(segment, string_types):
            segment = segment
        return segment

    seg = (quote(clean_segment(s)) for s in seg)
    if query is None or len(query) == 0:
        query_string = ""
    else:
        query_string = f"?{urlencode(query)}"
    path = "/".join(seg) + query_string
    adjusted_base = f"{base.rstrip('/')}/"
    return urljoin(str(adjusted_base), str(path))


def xml_property(path, converter=lambda x: x.text, default=None):
    def getter(self):
        if hasattr(self, f"_{path}"):
            return getattr(self, f"_{path}")
        try:
            if path in self.dirty:
                return self.dirty[path]
            else:
                if self.dom is None:
                    self.fetch()
                node = self.dom.find(path)
                if node is not None:
                    res = converter(self.dom.find(path))
                    if issubclass(type(res), StaticResourceInfo):
                        setattr(self, f"_{path}", res)
                    return res
                return default
        except Exception as e:
            raise AttributeError(e)

    def setter(self, value):
        self.dirty[path] = value
        x = 1

    def delete(self):
        self.dirty[path] = None

    return property(getter, setter, delete)


def bbox(node):
    if node is not None:
        minx = node.find("minx")
        maxx = node.find("maxx")
        miny = node.find("miny")
        maxy = node.find("maxy")
        crs = node.find("crs")
        crs = crs.text if crs is not None else None

        if None not in [minx, maxx, miny, maxy]:
            return (minx.text, maxx.text, miny.text, maxy.text, crs)
        else:
            return None
    else:
        return None


def string_list(node):
    if node is not None:
        return [n.text for n in node.findall("string")]


def attribute_list(node):
    if node is not None:
        return [n.text for n in node.findall("attribute/name")]


def key_value_pairs(node):
    if node is not None:
        return dict(
            (entry.attrib["key"], entry.text) for entry in node.findall("entry")
        )


def read_string(node):
    return node.text


def write_string(name):
    def write(builder, value):
        builder.start(name, dict())
        if value is not None and value:
            builder.data(value)
        builder.end(name)

    return write


def read_bool(node):
    text = node.text
    if text:
        return text == "true"
    else:
        return None


def write_bool(name):
    def write(builder, b):
        builder.start(name, dict())
        builder.data("true" if b and b != "false" else "false")
        builder.end(name)

    return write


def read_int(node):
    text = node.text
    try:
        res = int(text)
        return res
    except Exception as e:
        raise ValueError(e)


def write_int(name):
    def write(builder, b):
        builder.start(name, dict())
        builder.data(str(b))
        builder.end(name)

    return write


def read_float(node):
    text = node.text
    try:
        res = float(text)
        return res
    except Exception as e:
        raise ValueError(e)


def write_float(name):
    def write(builder, b):
        builder.start(name, dict())
        builder.data(str(b))
        builder.end(name)

    return write


def write_bbox(name):
    def write(builder, b):
        builder.start(name, dict())
        bbox_xml(builder, b)
        builder.end(name)

    return write


def write_string_list(name):
    def write(builder, words):
        builder.start(name, dict())
        if words:
            words = [w for w in words if len(w) > 0]
            for w in words:
                builder.start("string", dict())
                builder.data(w)
                builder.end("string")
        builder.end(name)

    return write


def write_dict(name):
    def write(builder, pairs):
        builder.start(name, dict())
        for k, v in pairs.items():
            if k == "port":
                v = str(v)
            builder.start("entry", dict(key=k))
            v = v if isinstance(v, string_types) else str(v)
            builder.data(v)
            builder.end("entry")
        builder.end(name)

    return write


def write_metadata(name):
    def write(builder, metadata):
        builder.start(name, dict())
        for k, v in metadata.items():
            builder.start("entry", dict(key=k))
            if k in ["time", "elevation"] or k.startswith("custom_dimension"):
                dimension_info(builder, v)
            elif k == "DynamicDefaultValues":
                dynamic_default_values_info(builder, v)
            elif k == "JDBC_VIRTUAL_TABLE":
                jdbc_virtual_table(builder, v)
            else:
                builder.data(v)
            builder.end("entry")
        builder.end(name)

    return write


class StaticResourceInfo(object):
    def __init__(self):
        self.write_all = True
        self.dom = None
        self.dirty = dict()

    def dirty_all(self):
        for key in self.writers.keys():
            attr = getattr(self, key)
            if issubclass(type(attr), StaticResourceInfo):
                attr.dirty_all()
            else:
                self.dirty[key] = attr

    def serialize(self, builder):
        # GeoServer will disable the resource if we omit the <enabled> tag,
        # so force it into the dirty dict before writing
        if hasattr(self, "enabled"):
            self.dirty["enabled"] = self.enabled

        if hasattr(self, "advertised"):
            self.dirty["advertised"] = self.advertised

        for k, writer in self.writers.items():
            if hasattr(self, k) and issubclass(
                type(getattr(self, k)), StaticResourceInfo
            ):
                attr = getattr(self, k)
                if attr.dirty:
                    attr.serialize_all(builder)
            elif k in self.dirty:
                val = self.dirty[k]
                writer(builder, val)
            elif self.write_all:
                attr = None
            elif self.write_all and hasattr(self, k):
                attr = getattr(self, k)
                val = self.dirty[k] if self.dirty.get(k) else attr
                writer(builder, val)

    def serialize_all(self, builder):
        builder.start(self.resource_type, dict())
        self.serialize(builder)
        builder.end(self.resource_type)

    def message(self):
        builder = TreeBuilder()
        self.serialize_all(builder)
        msg = tostring(builder.close())
        return msg


class ResourceInfo(StaticResourceInfo):
    def __init__(self):
        self.write_all = False
        self.dom = None
        self.dirty = dict()

    def _clear_subclasses(self):
        sbcs = [
            k for k, v in vars(self).items() if issubclass(type(v), StaticResourceInfo)
        ]
        for sbc in sbcs:
            delattr(self, sbc)

    def fetch(self):
        self.dom = self.catalog.get_xml(self.href)

    def clear(self):
        self.dirty = dict()
        self._clear_subclasses()

    def refresh(self):
        self.clear()
        self.fetch()


def prepare_upload_bundle(name, data):
    """GeoServer's REST API uses ZIP archives as containers for file formats such
    as Shapefile and WorldImage which include several 'boxcar' files alongside
    the main data.  In such archives, GeoServer assumes that all of the relevant
    files will have the same base name and appropriate extensions, and live in
    the root of the ZIP archive.  This method produces a zip file that matches
    these expectations, based on a basename, and a dict of extensions to paths or
    file-like objects. The client code is responsible for deleting the zip
    archive when it's done."""
    fd, path = mkstemp()
    zip_file = ZipFile(path, "w", allowZip64=True)
    for ext, stream in data.items():
        fname = f"{name}.{ext}"
        if isinstance(stream, string_types):
            zip_file.write(stream, fname)
        else:
            zip_file.writestr(fname, stream.read())
    zip_file.close()
    os.close(fd)
    return path


def atom_link(node):
    if "href" in node.attrib:
        return node.attrib["href"]
    else:
        link = node.find("{http://www.w3.org/2005/Atom}link")
        return link.get("href")


def atom_link_xml(builder, href):
    builder.start(
        "atom:link",
        {
            "rel": "alternate",
            "href": href,
            "type": "application/xml",
            "xmlns:atom": "http://www.w3.org/2005/Atom",
        },
    )
    builder.end("atom:link")


def bbox_xml(builder, box):
    minx, maxx, miny, maxy, crs = box
    builder.start("minx", dict())
    builder.data(str(minx))
    builder.end("minx")
    builder.start("maxx", dict())
    builder.data(str(maxx))
    builder.end("maxx")
    builder.start("miny", dict())
    builder.data(str(miny))
    builder.end("miny")
    builder.start("maxy", dict())
    builder.data(str(maxy))
    builder.end("maxy")
    if crs is not None and crs:
        builder.start("crs", {"class": "projected"})
        builder.data(crs)
        builder.end("crs")


def dimension_info(builder, metadata):
    if isinstance(metadata, DimensionInfo):
        builder.start("dimensionInfo", dict())
        builder.start("enabled", dict())
        builder.data("true" if metadata.enabled else "false")
        builder.end("enabled")
        if metadata.presentation is not None:
            accepted = ["LIST", "DISCRETE_INTERVAL", "CONTINUOUS_INTERVAL"]
            if metadata.presentation not in accepted:
                raise ValueError(
                    f"metadata.presentation must be one of the following {accepted}"
                )
            else:
                builder.start("presentation", dict())
                builder.data(metadata.presentation)
                builder.end("presentation")
        if metadata.attribute is not None:
            builder.start("attribute", dict())
            builder.data(metadata.attribute)
            builder.end("attribute")
        if metadata.end_attribute is not None:
            builder.start("endAttribute", dict())
            builder.data(metadata.end_attribute)
            builder.end("endAttribute")
        if metadata.resolution is not None:
            builder.start("resolution", dict())
            builder.data(str(metadata.resolution_millis()))
            builder.end("resolution")
        if metadata.units is not None:
            builder.start("units", dict())
            builder.data(metadata.units)
            builder.end("units")
        if metadata.unitSymbol is not None:
            builder.start("unitSymbol", dict())
            builder.data(metadata.unitSymbol)
            builder.end("unitSymbol")
        if metadata.strategy is not None:
            builder.start("defaultValue", dict())
            builder.start("strategy", dict())
            builder.data(metadata.strategy)
            builder.end("strategy")
            if metadata.referenceValue:
                builder.start("referenceValue", dict())
                builder.data(metadata.referenceValue)
                builder.end("referenceValue")
            builder.end("defaultValue")
        if metadata.nearestMatchEnabled is not None:
            builder.start("nearestMatchEnabled", dict())
            builder.data(metadata.nearestMatchEnabled)
            builder.end("nearestMatchEnabled")

        builder.end("dimensionInfo")


class DimensionInfo(object):
    _lookup = (
        ("seconds", 1),
        ("minutes", 60),
        ("hours", 3600),
        ("days", 86400),
        # this is the number geoserver computes for 1 month
        ("months", 2628000000),
        ("years", 31536000000),
    )

    def __init__(
        self,
        name,
        enabled,
        presentation,
        resolution,
        units,
        unitSymbol,
        strategy=None,
        attribute=None,
        end_attribute=None,
        reference_value=None,
        nearestMatchEnabled=None,
    ):
        self.name = name
        self.enabled = enabled
        self.attribute = attribute
        self.end_attribute = end_attribute
        self.presentation = presentation
        self.resolution = resolution
        self.units = units
        self.unitSymbol = unitSymbol
        self.strategy = strategy
        self.referenceValue = reference_value
        self.nearestMatchEnabled = nearestMatchEnabled

    def _multipier(self, name):
        name = name.lower()
        found = [i[1] for i in self._lookup if i[0] == name]
        if not found:
            raise ValueError(f"invalid multipler: {name}")
        return found[0] if found else None

    def resolution_millis(self):
        """if set, get the value of resolution in milliseconds"""
        if self.resolution is None or not isinstance(self.resolution, string_types):
            return self.resolution
        val, mult = self.resolution.split(" ")
        return int(float(val) * self._multipier(mult) * 1000)

    def resolution_str(self):
        '''if set, get the value of resolution as "<n> <period>s", for example: "8 seconds"'''
        if self.resolution is None or isinstance(self.resolution, string_types):
            return self.resolution
        seconds = self.resolution / 1000.0
        biggest = self._lookup[0]
        for entry in self._lookup:
            if seconds < entry[1]:
                break
            biggest = entry
        val = seconds / biggest[1]
        if val == int(val):
            val = int(val)
        return f"{val} {biggest[0]}"


def md_dimension_info(name, node):
    """Extract metadata Dimension Info from an xml node"""

    def _get_value(child_name):
        return getattr(node.find(child_name), "text", None)

    resolution = _get_value("resolution")
    defaultValue = node.find("defaultValue")
    strategy = defaultValue.find("strategy") if defaultValue is not None else None
    strategy = strategy.text if strategy is not None else None
    return DimensionInfo(
        name,
        _get_value("enabled") == "true",
        _get_value("presentation"),
        int(resolution) if resolution else None,
        _get_value("units"),
        _get_value("unitSymbol"),
        strategy,
        _get_value("attribute"),
        _get_value("endAttribute"),
        _get_value("referenceValue"),
        _get_value("nearestMatchEnabled"),
    )


def dynamic_default_values_info(builder, metadata):
    if isinstance(metadata, DynamicDefaultValues):
        builder.start("DynamicDefaultValues", dict())

        if metadata.configurations is not None:
            builder.start("configurations", dict())
            for c in metadata.configurations:
                builder.start("configuration", dict())
                if c.dimension is not None:
                    builder.start("dimension", dict())
                    builder.data(c.dimension)
                    builder.end("dimension")
                if c.policy is not None:
                    builder.start("policy", dict())
                    builder.data(c.policy)
                    builder.end("policy")
                if c.defaultValueExpression is not None:
                    builder.start("defaultValueExpression", dict())
                    builder.data(c.defaultValueExpression)
                    builder.end("defaultValueExpression")
                builder.end("configuration")
            builder.end("configurations")
        builder.end("DynamicDefaultValues")


class DynamicDefaultValuesConfiguration(object):
    def __init__(self, dimension, policy, defaultValueExpression):
        self.dimension = dimension
        self.policy = policy
        self.defaultValueExpression = defaultValueExpression


class DynamicDefaultValues(object):
    def __init__(self, name, configurations):
        self.name = name
        self.configurations = configurations


def md_dynamic_default_values_info(name, node):
    """Extract metadata Dynamic Default Values from an xml node"""
    configurations = node.find("configurations")
    if configurations is not None:
        configurations = []
        for n in node.findall("configuration"):
            dimension = n.find("dimension")
            dimension = dimension.text if dimension is not None else None
            policy = n.find("policy")
            policy = policy.text if policy is not None else None
            defaultValueExpression = n.find("defaultValueExpression")
            defaultValueExpression = (
                defaultValueExpression.text
                if defaultValueExpression is not None
                else None
            )

            configurations.append(
                DynamicDefaultValuesConfiguration(
                    dimension, policy, defaultValueExpression
                )
            )

    return DynamicDefaultValues(name, configurations)


class JDBCVirtualTableGeometry(object):
    def __init__(self, _name, _type, _srid):
        self.name = _name
        self.type = _type
        self.srid = _srid


class JDBCVirtualTableParam(object):
    def __init__(self, _name, _defaultValue, _regexpValidator):
        self.name = _name
        self.defaultValue = _defaultValue
        self.regexpValidator = _regexpValidator


class JDBCVirtualTable(object):
    def __init__(
        self, _name, _sql, _escapeSql, _geometry, _keyColumn=None, _parameters=None
    ):
        self.name = _name
        self.sql = _sql
        self.escapeSql = _escapeSql
        self.geometry = _geometry
        self.keyColumn = _keyColumn
        self.parameters = _parameters


def jdbc_virtual_table(builder, metadata):
    if isinstance(metadata, JDBCVirtualTable):
        builder.start("virtualTable", dict())
        # name
        builder.start("name", dict())
        builder.data(metadata.name)
        builder.end("name")
        # sql
        builder.start("sql", dict())
        builder.data(metadata.sql)
        builder.end("sql")
        # escapeSql
        builder.start("escapeSql", dict())
        builder.data(metadata.escapeSql)
        builder.end("escapeSql")
        # keyColumn
        if metadata.keyColumn is not None:
            builder.start("keyColumn", dict())
            builder.data(metadata.keyColumn)
            builder.end("keyColumn")

        # geometry
        if metadata.geometry is not None:
            g = metadata.geometry
            builder.start("geometry", dict())
            if g.name is not None and g.name:
                builder.start("name", dict())
                builder.data(g.name)
                builder.end("name")
            if g.type is not None and g.type:
                builder.start("type", dict())
                builder.data(g.type)
                builder.end("type")
            if g.srid is not None and g.srid:
                builder.start("srid", dict())
                builder.data(g.srid)
                builder.end("srid")
            builder.end("geometry")

        # parameters
        if metadata.parameters is not None:
            for p in metadata.parameters:
                builder.start("parameter", dict())
                if p.name is not None:
                    builder.start("name", dict())
                    builder.data(p.name)
                    builder.end("name")
                if p.defaultValue is not None:
                    builder.start("defaultValue", dict())
                    builder.data(p.defaultValue)
                    builder.end("defaultValue")
                if p.regexpValidator is not None:
                    builder.start("regexpValidator", dict())
                    builder.data(p.regexpValidator)
                    builder.end("regexpValidator")
                builder.end("parameter")

        builder.end("virtualTable")


def md_jdbc_virtual_table(key, node):
    """Extract metadata JDBC Virtual Tables from an xml node"""
    name = node.find("name")
    sql = node.find("sql")
    escapeSql = node.find("escapeSql")
    escapeSql = escapeSql.text if escapeSql is not None else None
    keyColumn = node.find("keyColumn")
    keyColumn = keyColumn.text if keyColumn is not None else None
    n_g = node.find("geometry")
    geometry = JDBCVirtualTableGeometry(
        n_g.find("name"), n_g.find("type"), n_g.find("srid")
    )
    parameters = []
    for n_p in node.findall("parameter"):
        p_name = n_p.find("name")
        p_defaultValue = n_p.find("defaultValue")
        p_defaultValue = p_defaultValue.text if p_defaultValue is not None else None
        p_regexpValidator = n_p.find("regexpValidator")
        p_regexpValidator = (
            p_regexpValidator.text if p_regexpValidator is not None else None
        )
        parameters.append(
            JDBCVirtualTableParam(p_name, p_defaultValue, p_regexpValidator)
        )

    return JDBCVirtualTable(name, sql, escapeSql, geometry, keyColumn, parameters)


def md_entry(node):
    """Extract metadata entries from an xml node"""
    key = None
    value = None
    if "key" in node.attrib:
        key = node.attrib["key"]
    else:
        key = None

    if key in ["time", "elevation"] or key.startswith("custom_dimension"):
        value = md_dimension_info(key, node.find("dimensionInfo"))
    elif key == "DynamicDefaultValues":
        value = md_dynamic_default_values_info(key, node.find("DynamicDefaultValues"))
    elif key == "JDBC_VIRTUAL_TABLE":
        value = md_jdbc_virtual_table(key, node.find("virtualTable"))
    else:
        value = node.text

    if None in [key, value]:
        return None
    else:
        return (key, value)


def metadata(node):
    if node is not None:
        return dict(md_entry(n) for n in node.findall("entry"))


def _decode_list(data):
    rv = []
    for item in data:
        if isinstance(item, string_types):
            item = item
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv


def _decode_dict(data):
    rv = {}
    for key, value in data.items():
        if isinstance(key, string_types):
            key = key
        if isinstance(value, string_types):
            value = value
        elif isinstance(value, list):
            value = _decode_list(value)
        elif isinstance(value, dict):
            value = _decode_dict(value)
        rv[key] = value
    return rv


def workspace_from_url(url):
    parts = urlparse(url)
    split_path = parts.path.split("/")
    if "workspaces" in split_path:
        return split_path[split_path.index("workspaces") + 1]
    else:
        return None


def resource_from_url(url, workspace):
    parts = urlparse(url)
    split_path = parts.path.split("/")
    if workspace in split_path:
        resource_type = split_path[split_path.index(workspace) + 1]
        return split_path[split_path.index(resource_type) + 1]
    else:
        return None
