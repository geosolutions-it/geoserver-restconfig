GeoServer Configuration Objects
===============================

``gsconfig`` operates on the GeoServer configuration in terms of several variants of *configuration objects:*

  * **Layers** are spatial datasets published in the OGC services provided by GeoServer. 

  * **LayerGroups** are preset groupings of layers that can be accessed by WMS clients as if they were a single layer.
    For example, you might create a basemap LayerGroup by overlaying several layers containing road, hydrography, impervious area, and forestry information.

  * **Styles** are sets of rendering rules that define how a Layer should be drawn when accessed via WMS.
    A Layer may be associated with many Styles and a Style may be associated with many Layers.

  * **Resources** are coherent datasets.
    A Resource containing vector data (discrete features with geometries and associated fields) is called a **FeatureType,** while a Resource containing raster data (a grid of numeric cells) is called a **Coverage.**

  * **Stores** represent connections to some repository of geospatial information, such as a PostGIS database or a directory containing Shapefiles.
    Stores can contain multiple Resources; for example, when connecting to a spatial database each table or view could be published as a separate layer.
    A Store containing only FeatureTypes is called a **DataStore,** while a Store containing only Coverages is called a **CoverageStore.**
    A Store must be either a DataStore or a CoverageStore, never both.

  * **Workspaces** are arbitrary groupings of data which can help administrators organize data.
    Currently workspaces are also associated with **Namespaces** which affect the advertised names of layers in some OGC services, such as WFS and WCS.

Installing gsconfig and Connecting to GeoServer
+++++++++++++++++++++++++++++++++++++++++++++++

Since gsconfig interacts with GeoServer via HTTP requests, GeoServer must be running before you can use gsconfig to operate on the GeoServer configuration.
See the GeoServer user's manual for information on installing and running GeoServer.

In addition to GeoServer, you'll also need:
  * Python, along with the setuptools module for installation
  * The Git command line tools

Once you have the prerequisite software installed, follow these steps:

1. Fetch the gsconfig.py sources::

   $ git clone git://github.com/dwins/gsconfig.py.git

2. Switch directories to the new copy of gsconfig::

   $ cd gsconfig.py/

3. Run the setup.py script to make the package available::

       $ python setup.py install

   If you intend to add features or fix bugs in gsconfig, you may prefer to install in "development mode" which will cause any changes you make to the gsconfig sources to instantly apply to other scripts loading it::

       $ python setup.py develop

.. seealso:: 
   
    `virtualenv <http://pypi.python.org/pypi/virtualenv>`_ is a popular Python package for managing modules and avoiding version conflicts.
    The `setuptools documentation <http://peak.telecommunity.com/DevCenter/setuptools>`_ has more information about the setup.py script.

Now that gsconfig is installed you should be able to load it::

    $ python -m geoserver.catalog && echo "GeoServer loaded properly"


To connect to GeoServer, you can simply use the ``geoserver.catalog.Catalog`` constructor.  This example assumes that the default admin username and password are being used::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")

That should work for connecting to a "default" GeoServer configuration, immediately after running the GeoServer installer for your platform or deploying the GeoServer WAR.
If you are using other credentials (highly recommended for production,) you can provide them to the constructor as well::

    from geoserver.catalog import Catalog
    cat = Catalog("http://example.com/geoserver/rest",
        username="root", password="t0ps3cr3t")

For simplicity's sake, other examples in this documentation will assume you're working against a GeoServer installed locally using the default security settings.

Working with Layers
+++++++++++++++++++

Layers provide settings related only to the publishing of data.
You can get a listing of all Layers configured in GeoServer::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    all_layers = cat.get_layers()

If you know a Layer's name you can also retrieve it directly::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    that_layer = cat.get_layer("roads")

Once you have a Layer, you can manipulate its properties to change the configuration.
However, no changes will actually be applied until you save it::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    that_layer = cat.get_layer("roads")
    that_layer.enabled = False
    # at this point that_layer is still published in GeoServer
    cat.save(that_layer)
    # now it is disabled

Layers provide these settings:

* **enabled** is a Boolean flag which may be set to ``False`` to stop serving a layer without deleting it.
  If this is set to ``True`` then the layer will be served.

* **default_style** is the Style used in WMS requests when no Style is specified by the client.

* **alternate_styles** is a list of other Styles that should be advertised as suitable for use with the layer.

  .. note:: There is currently a caveat regarding the usage of list properties in ``gsconfig``.

* **attribution_object** contains information regarding the name, logo, and link to more information about a Layer's provider.


Working with Resources
++++++++++++++++++++++

Further settings, deemed more integral to the data, are available on the Resource associated with the Layer.
If you already have a Layer object, you can get the corresponding Resource easily::

    resource = layer.resource

Alternatively, you can directly retrieve a list of all Resources::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    resources = cat.get_resources()

As with Layers, you can retrieve a resource specifically by name::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    resource = cat.get_resource("roads")

With only one argument, ``get_resource`` will search all Workspaces and Stores for a resource with the given name.
However, it is possible to have multiple resources with a particular name.
If gsconfig detects that a request is ambiguous, it will raise ``geonode.catalog.AmbiguousRequestError`` rather than return a resource that might not be theone you had in mind.
You can be more specific by specifying a Workspace or Store along with the name (although the name is always required.)
For example, if you know that the ``roads`` Resource is coming from a Store named ``municipality`` you can avoid an ``AmbiguousRequestError`` by telling the ``Catalog`` about it::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    resource = cat.get_resource("roads", store="municpality")

A Workspace can be specified similarly::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    resource = cat.get_resource("roads", workspace="municipality")

It's also possible to use a Store or Workspace object directly::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    workspace = cat.get_workspace("municipality")
    resource = cat.get_resource("roads", workspace=workspace)

Similar to Layers, you must explicitly save changes to Resources for them to be applied::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    that_resource = cat.get_resource("roads")
    that_resource.enabled = False
    # at this point that_layer is still published in GeoServer
    cat.save(that_resource)
    # now it is disabled

While FeatureTypes (vector Resources) and Coverages (raster Resources) each provide settings unique to their specific needs, there are some common settings as well:

* **title** is a string naming the Layer in a human-friendly way.
  For example, it should be suitable for display in a layer listing GUI.

* **abstract** is a string describing the Layer in more detail than the title.

* **keywords** is a list of short strings naming topics relevant to this dataset.

  .. note:: There is currently a caveat regarding the usage of list properties in ``gsconfig``.


* **enabled** is a Boolean flag which may be set to ``False`` to stop serving a Resource without deleting it.
  If this is set to ``True`` then (assuming a corresponding enabled Layer exists) the Resource will be served.

* **native_bbox** is a list of strings indicating the bounding box of the dataset in its native projection (the projection used to actually store it in physical media.)
  The first four elements of this list will be the bounding box coordinates (in the order minx, maxx, miny, maxy) and the last element will either be an EPSG code for the projection (for example, "EPSG:4326") or the WKT for a projection not defined in the EPSG database.

  .. note:: There is currently a caveat regarding the usage of list properties in ``gsconfig``.

* **latlon_bbox** is a list of strings indicating the bounding box of the dataset in latitude/longitude coordinates.
  The first four elements of this list will be the bounding box coordinates (in the order minx, maxx, miny, maxy).
  The fifth element is optional and, if present, will always be "EPSG:4326".

  .. note:: There is currently a caveat regarding the usage of list properties in ``gsconfig``.

* **projection** is a string describing the projection GeoServer should advertise as the native one for the resource.
  The way this influences the actual values GeoServer will report for data from this resource are determined by the **projection_policy**.

* **projection_policy** is a string determining how GeoServer will interpret the **projection** setting.
  It may take three values:
  
    * ``FORCE_DECLARED``: the data from the underlying store is assumed to be in the projection specified
    * ``FORCE_NATIVE``: the projection setting is ignored and GeoServer will publish the projection as determined by inspecting the source data
    * ``REPROJECT``: GeoServer will reproject the data in the underlying source to the one specified

  These are enumerated as constants in the ``geoserver.support`` package.

* **metadata_links**  is a list of links to metadata about the resource annotated with a MIME type string and a string identifying the metadata standard.

  .. note:: There is currently a caveat regarding the usage of list properties in ``gsconfig``.

Working with FeatureTypes (Vector Data)
---------------------------------------

* **attributes** is a list of objects describing the names and types of the fields in the data set.

  .. note::

    There is currently a caveat regarding the usage of list properties in ``gsconfig``.
    Also, I'm not totally sure what the implications are of editing this property; it is editable through restconfig but not through the GUI.


Working with Coverages (Raster Data)
------------------------------------

* **request_srs_list** is a list of strings defining the SRS's that GeoServer should allow in requests against this coverage.
  Each SRS should be specified by its EPSG code.

* **response_srs_list** is a list of strings defining the SRS's that GeoServer should use for responding to requests against this coverage.
  Each SRS should be specified by its EPSG code.

* **supported_formats** is a list of strings identifying the formats that GeoServer should use for encoding responses to requests against this Coverage.
  New formats may be added by GeoServer extensions, but in a default installation of GeoServer these format names are accepted:

  * ARCGRID

  * IMAGEMOSAIC

  * GTOPO30

  * GEOTIFF

  * GIF

  * PNG

  * JPEG

  * TIFF

Working with Styles
+++++++++++++++++++

Styles provide rules for determining how a data layer should be rendered as an image for viewing.
You can get a listing of all Styles configured in GeoServer::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    all_styles = cat.get_styles()

If you know a Style's name you can also retrieve it directly::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    that_style = cat.get_style("highway")

Additionally, you can follow the links from a Layer to the Styles that are associated with it::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    that_layer = cat.get_layer("roads")
    that_style = that_layer.default_style

Styles are a bit odd out of all the objects in gsconfig in that they have no writable properties.
Instead, they are simply a small decoration around style files in SLD format which can be added, deleted, or replaced in full.

To *add* a Style, generate an SLD somehow (``gsconfig`` does not provide any facilities for doing this.)
Typically this will be saved to a file, for example :file:`railroad.sld`.
This code will then add the SLD file to GeoServer as a Style available for WMS requests::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    with open("railroad.sld") as f:
        cat.create_style("railroad", f.read())
 
To *replace* an existing Style, simply add another parameter named ``overwrite``::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    with open("railroad.sld") as f:
        cat.create_style("railroad", f.read(), overwrite=True)

If you need to *remove* the Style instead, it looks a bit different::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    style = cat.get_style("railroad")
    cat.delete(style)

Working with LayerGroups
++++++++++++++++++++++++

A LayerGroup "packages up" several Layers to make them more convenient to access together.
You can get a listing of all Layers configured in GeoServer::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    all_groups = cat.get_layergroups()

If you know a LayerGroup's name you can also retrieve it directly::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    that_group = cat.get_layergroup("basemap")

Once you have a LayerGroup, you can manipulate its properties to find out what Layers and Styles it uses::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    that_group = cat.get_layergroup("basemap")
    assert len(that_group.styles) == len(that_group.layers)

When working with LayerGroups it is important to ensure that the ``layers`` list and ``styles`` list have the same length before saving any changes.

.. note:: 

    GeoServer also lets us read and set the bounding box for LayerGroups via the REST API but gsconfig doesn't support this yet.

Working with Stores
+++++++++++++++++++

Resources in GeoServer are always contained within a Store.
A Store's configuration includes details of how to connect to some store of spatial data, such as login credentials for a PostgreSQL server or the file path to a GeoTIFF file.
You can get a listing of all Stores configured in GeoServer::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    all_stores = cat.get_stores()

If you know a Store's name you can also retrieve it directly::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    that_store = cat.get_store("db_server")

Once you have a Store, you can manipulate its properties to change the configuration.  However, no changes will actually be applied until you save it::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    that_store = cat.get_store("db_server")
    that_store.enabled = False
    # at this point that_store is still enabled in GeoServer
    cat.save(that_store)
    # now it is disabled

Stores provide one common setting:

    * *enabled* A Boolean flag which may be set to ``False`` to stop serving the Resources (and corresponding Layers) for a Store without deleting them or the Store.
      If this is set to ``True`` then the Layers will be available.

Working with DataStores (Vector Data)
-------------------------------------

* **connection_parameters** a dict containing connection details.
  The keys used and interpretation of their values depends on the type of datastore involved.
  See :doc:`examples` for some sample usage, or :doc:`cross-ref-with-geotools` for details on how to identify the parameters for datastores not covered there.

Working with CoverageStores (Raster Data)
-----------------------------------------

* **url** A URL string (usually with the ``file:`` pseudo-protocol) identifying the raster file backing the CoverageStore.

* **type** A string identifying the format of the coverage file.
  While GeoServer extensions can add support for additional formats, the following are supported in a "vanilla" GeoServer installation:

  * ``Gtopo30``, ``GeoTIFF``, ``ArcGrid``, ``WorldImage``, ``ImageMosaic``

Working with Workspaces
+++++++++++++++++++++++

Workspaces provide a logical grouping to help administrators organize the data in a GeoServer instance.
You can get a listing of all Workspaces configured in GeoServer::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    all_workspaces = cat.get_workspaces()

If you know a Workspace's name you can also retrieve it directly::

    from geoserver.catalog import Catalog
    cat = Catalog("http://localhost:8080/geoserver/rest")
    that_workspace = cat.get_workspace("forestry")
