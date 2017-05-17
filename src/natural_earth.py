# coding=utf-8

import os
import xmltodict
import ogr
import osr
import gdal
from config import NATURAL_EARTH_DIR
from pprint import pprint


def read_gpx_file(file_path):
    """Reads a GPX file containing geocaching points.

    :param str file_path: The full path to the file.
    """
    with open(file_path) as gpx_file:
        gpx_dict = xmltodict.parse(gpx_file.read())
    output = []
    for wpt in gpx_dict['gpx']['wpt']:
        geometry = [wpt.pop('@lat'), wpt.pop('@lon')]
        # If geocache is not on the dict, skip this wpt.
        try:
            geocache = wpt.pop('geocache')
        except KeyError:
            continue
        attributes = {'status': geocache.pop('@status')}
        # Merge the dictionaries.
        attributes.update(wpt)
        attributes.update(geocache)
        # Construct a GeoJSON feature and append to the list.
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": geometry},
            "properties": attributes}
        output.append(feature)
    return output


def get_datasource_information(datasource, print_results=False):
    """Get informations about the first layer in the datasource.

    :param datasource: An OGR datasource.
    :param bool print_results: True to print the results on
      the screen.
    """
    info = {}
    layer = datasource.GetLayerByIndex(0)
    bbox = layer.GetExtent()
    info['bbox'] = dict(xmin=bbox[0], xmax=bbox[1],
                        ymin=bbox[2], ymax=bbox[3])
    srs = layer.GetSpatialRef()
    if srs:
        info['epsg'] = srs.GetAttrValue('authority', 1)
    else:
        info['epsg'] = 'not available'
    info['type'] = ogr.GeometryTypeToName(layer.GetGeomType())
    # Gets the attributes names.
    info['attributes'] = []
    layer_definition = layer.GetLayerDefn()
    for index in range(layer_definition.GetFieldCount()):
        info['attributes'].append(layer_definition.GetFieldDefn(index).GetName())
    # Print the results.
    if print_results:
        pprint(info)
    return info


def read_ogr_features(layer):
    """Convert OGR features from a layer into dictionaries.

    :param layer: OGR layer.
    """
    features = []
    layer_defn = layer.GetLayerDefn()
    layer.ResetReading()
    type = ogr.GeometryTypeToName(layer.GetGeomType())
    for item in layer:
        attributes = {}
        for index in range(layer_defn.GetFieldCount()):
            field_defn = layer_defn.GetFieldDefn(index)
            key = field_defn.GetName()
            value = item.GetFieldAsString(index)
            attributes[key] = value
        feature = {
            "type": "Feature",
            "geometry": {
                "type": type,
                "coordinates": item.GetGeometryRef().ExportToWkt()},
            "properties": attributes}
        features.append(feature)
    return features


def open_vector_file(file_path):
    """Opens an vector file compatible with OGR or a GPX file.
    Returns a list of features and informations about the file.

    :param str file_path: The full path to the file.
    """
    datasource = ogr.Open(file_path)
    # Check if the file was opened.
    if not datasource:
        if not os.path.isfile(file_path):
            message = "Wrong path."
        else:
            message = "File format is invalid."
        raise IOError('Error opening the file {}\n{}'.format(file_path, message))

    metadata = get_datasource_information(datasource)
    file_name, file_extension = os.path.splitext(file_path)
    # Check if it's a GPX and read it if so.
    if file_extension in ['.gpx', '.GPX']:
        features = read_gpx_file(file_path)
    # If not, use OGR to get the features.
    else:
        features = read_ogr_features(datasource.GetLayerByIndex(0))
    return features, metadata


def create_transform(src_epsg, dst_epsg):
    """Creates an OSR tranformation.

    :param src_epsg: EPSG code for the source geometry.
    :param dst_epsg: EPSG code for the destination geometry.
    :return: osr.CoordinateTransformation
    """
    src_srs = osr.SpatialReference()
    src_srs.ImportFromEPSG(src_epsg)
    dst_srs = osr.SpatialReference()
    dst_srs.ImportFromEPSG(dst_epsg)
    return osr.CoordinateTransformation(src_srs, dst_srs)


def transform_geometries(datasource, src_epsg, dst_epsg):
    """Transform the coordinates of all geometries in
    the first layer.
    """
    transformation = create_transform(src_epsg, dst_epsg)
    layer = datasource.GetLayerByIndex(0)
    geoms = []
    layer.ResetReading()
    for feature in layer:
        geom = feature.GetGeometryRef().Clone()
        geom.Transform(transformation)
        geoms.append(geom)
    return geoms


def transform_points(points, src_epsg=4326, dst_epsg=3857):
    """Transform the coordinate reference system of a list of
     coordinates (a list of points)

    :param src_epsg: EPSG code for the source geometry.
    :param dst_epsg: EPSG code for the destination geometry.
    """
    transform = create_transform(src_epsg, dst_epsg)
    points = transform.TransformPoints(points)
    return points


def transform_geometry(wkt_geom, src_epsg=4326, dst_epsg=3857):
    """Transforms a single wkt geometry.

    :param wkt_geom: wkt geom.
    :param src_epsg: EPSG code for the source geometry.
    :param dst_epsg: EPSG code for the destination geometry.
    """
    geom = ogr.CreateGeometryFromWkt(wkt_geom)
    transform = create_transform(src_epsg, dst_epsg)
    geom.Transform(transform)
    return geom.ExportToWkt()


def calculate_areas(geometries, unity='km2'):
    """Calculate the area for a list of ogr geometries."""
    conversion_factor = {
        'sqmi': 2589988.11,
        'km2': 1000000,
        'm': 1}
    if unity not in conversion_factor:
        raise ValueError("This unity is not defined: {}".format(unity))
    areas = []
    for geom in geometries:
        area = geom.Area()
        areas.append(area / conversion_factor[unity])
    return areas


def convert_length_unit(value, unit='km', decimal_places=2):
    """Convert the leng unit of a given value.
     The input is in meters and the output is set by the unity
      argument.

    :param value: Input value in meters.
    :param unit: The desired output unit.
    :param decimal_places: Number of decimal places of the output.
    """
    conversion_factor = {
        'mi': 0.000621371192,
        'km': 0.001,
        'm': 1.0}

    if unit not in conversion_factor:
        raise ValueError("This unit is not defined: {}".format(unit))
    return round(value * conversion_factor[unit], decimal_places)


def get_region_extents(regions, pois, extents):
    buff = 4000
    transform1 = create_transform(4326, 3857)
    transform2 = create_transform(3857, 4326)

    for region in regions:
        if region['properties']['iso_a2'].upper() != 'US':
            continue
        state_name = region['properties']['postal'].lower()
        if state_name not in extents:
            extents[state_name] = []

        geom = ogr.CreateGeometryFromWkt(region['geometry']['coordinates'])
        geom.Transform(transform1)
        regbuff = geom.Buffer(buff)
        for poi in pois:
            geom2 = ogr.CreateGeometryFromWkt(poi['geometry']['coordinates'])
            geom2.Transform(transform1)
            if not regbuff.Contains(geom2):
                continue
            poibuff = geom2.Buffer(buff, 1)
            poibuff.Transform(transform2)
            e = poibuff.GetEnvelope()
            extents[state_name].append((e[0], e[2], e[1], e[3]))


if __name__ == "__main__":
    gdal.PushErrorHandler('CPLQuietErrorHandler')

    fname = os.path.join(NATURAL_EARTH_DIR, "50m_cultural/ne_50m_admin_1_states_provinces.shp")
    # fname = os.path.join(NATURAL_EARTH_DIR, "10m_cultural/ne_10m_admin_1_states_provinces.shp")
    states, states_metadata = open_vector_file(fname)

    fname = os.path.join(NATURAL_EARTH_DIR, "50m_cultural/ne_50m_airports.shp")
    # fname = os.path.join(NATURAL_EARTH_DIR, "10m_cultural/ne_10m_airports.shp")
    airports, airports_metadata = open_vector_file(fname)

    fname = os.path.join(NATURAL_EARTH_DIR, "50m_cultural/ne_50m_ports.shp")
    # fname = os.path.join(NATURAL_EARTH_DIR, "10m_cultural/ne_10m_ports.shp")
    ports, airports_metadata = open_vector_file(fname)

    print 'done loading vector files'
    extents = {}
    get_region_extents(states, ports, extents)
    print 'done loading port extents'
    get_region_extents(states, airports, extents)
    print 'done loading airport extents'
    print 'done'
