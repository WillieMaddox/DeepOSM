"""Methods for working with geo/raster data."""

from osgeo import osr
from pyproj import Proj, transform


def lon_lat_to_pixel(raster_dataset, location):
    """From zacharybears.com/using-python-to-translate-latlon-locations-to-pixels-on-a-geotiff/."""
    ds = raster_dataset
    gt = ds.GetGeoTransform()
    srs = osr.SpatialReference()
    srs.ImportFromWkt(ds.GetProjection())

    srs_lon_lat = srs.CloneGeogCS()
    ct = osr.CoordinateTransformation(srs_lon_lat, srs)
    new_location = [None, None]
    # Change the point locations into the GeoTransform space
    (new_location[0], new_location[1], holder) = ct.TransformPoint(location[0], location[1])
    # Translate the x and y coordinates into pixel values
    x = (new_location[0] - gt[0]) / gt[1]
    y = (new_location[1] - gt[3]) / gt[5]
    return int(x), int(y)


def pixel_to_lon_lat(raster_dataset, col, row):
    """From zacharybears.com/using-python-to-translate-latlon-locations-to-pixels-on-a-geotiff/."""
    ds = raster_dataset
    gt = ds.GetGeoTransform()
    srs = osr.SpatialReference()
    srs.ImportFromWkt(ds.GetProjection())

    srs_lon_lat = srs.CloneGeogCS()
    ct = osr.CoordinateTransformation(srs, srs_lon_lat)

    ulon = col * gt[1] + gt[0]
    ulat = row * gt[5] + gt[3]

    (lon, lat, holder) = ct.TransformPoint(ulon, ulat)
    return lon, lat


def pixel_to_web_mercator(raster_dataset, col, row):
    """Convert a pixel on the raster_dataset to web mercator (epsg:3857)."""
    ds = raster_dataset
    gt = ds.GetGeoTransform()
    srs = osr.SpatialReference()
    srs.ImportFromWkt(ds.GetProjection())

    srs_web_merc = osr.SpatialReference()
    srs_web_merc.ImportFromEPSG(3857)
    ct = osr.CoordinateTransformation(srs, srs_web_merc)

    ulon = col * gt[1] + gt[0]
    ulat = row * gt[5] + gt[3]

    (lon, lat, holder) = ct.TransformPoint(ulon, ulat)
    return lon, lat


def pixel_to_lat_lon_web_mercator(raster_dataset, col, row):
    """Convert a pixel on the raster_dataset to web mercator (epsg:3857)."""
    ds = raster_dataset
    gt = ds.GetGeoTransform()
    srs = osr.SpatialReference()
    srs.ImportFromWkt(ds.GetProjection())

    ds_spatial_reference_proj_string = srs.ExportToProj4()
    in_proj = Proj(ds_spatial_reference_proj_string)
    out_proj = Proj(init='epsg:3857')

    ulon = col * gt[1] + gt[0]
    ulat = row * gt[5] + gt[3]

    x2, y2 = transform(in_proj, out_proj, ulon, ulat)
    # x2, y2 = out_proj(x2, y2, inverse=True)
    return x2, y2

