#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
load 
"""

import psycopg2
from geojson import loads, Feature, FeatureCollection


# Database Connection Info
db_host = "localhost"
db_user = "maddoxw"
db_passwd = "stars"
db_database = "gis"
db_port = "5432"

# connect to DB
# conn = psycopg2.connect(host=db_host, user=db_user, port=db_port, password=db_passwd, database=db_database)
conn = psycopg2.connect(host=db_host, user=db_user, port=db_port, database=db_database)

# create a cursor
cur = conn.cursor()
# delaware
# (-75.62500231633156, 39.00035728805054)
# (-75.68750264376517, 38.93714312569639)
# huntsville
# (-86.68892, 34.71330)
# (-86.65935, 34.73118)
# (-9665042.027558949, 3960324.7225557305)
# (-9660978.921774164, 3967934.984184373)
# the PostGIS buffer query
# buffer_query = """SELECT ST_AsGeoJSON(ST_Transform(ST_Buffer(wkb_geometry, 100,'quad_segs=8'),4326)) AS geom, name FROM buildings.way"""

# buffer_query = """SELECT ST_Extent(the_geom) As wgs_84, ST_Extent(ST_Transform(the_geom,900913)) as web_merc
# FROM tiger.states WHERE stusps = 'MA';"""

# buffer_query = """SELECT gid, name_en, ST_AsText(way) FROM buildings WHERE way && ST_SetSRID(ST_MakeBox2D(ST_Point(-86.68892, 34.71330), ST_Point(-86.65935, 34.73118)), 4326)"""
buffer_query = """SELECT gid, name_en, ST_AsText(way) AS polygon FROM buildings WHERE way && ST_SetSRID(ST_MakeBox2D(ST_Point(-9665042.027558949, 3960324.7225557305), ST_Point(-9660978.921774164, 3967934.984184373)), 3857)"""
buffer_query = """SELECT name_en, ST_AsText(way) FROM buildings WHERE way && ST_MakeEnvelope(-9665042.02755895, 3960324.72255573, -9660978.921774164, 3967934.984184373, 3857);"""
buffer_query = """SELECT name_en, ST_AsText(way) FROM buildings WHERE way && ST_MakeEnvelope(-9650965.50434266, 4125521.30132196, -9646923.896472085, 4126127.5629506027, 3857);"""
# execute the query
cur.execute(buffer_query)

# return all the rows, we expect more than one
dbRows = cur.fetchall()

# an empty list to hold each feature of our feature collection
new_geom_collection = []

# loop through each row in result query set and add to my feature collection
# assign name field to the GeoJSON properties
for each_poly in dbRows:
    geom = each_poly[0]
    name = each_poly[1]
    geoj_geom = loads(geom)
    myfeat = Feature(geometry=geoj_geom, properties={'name': name})
    new_geom_collection.append(myfeat)

# use the geojson module to create the final Feature Collection of features created from for loop above
my_geojson = FeatureCollection(new_geom_collection)

# define the output folder and GeoJSon file name
output_geojson_buf = "../geodata/out_buff_100m.geojson"

# close cursor
cur.close()

# close connection
conn.close()
