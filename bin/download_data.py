
import os
import argparse
import gdal
from src.config import NATURAL_EARTH_DIR
from src.training_data import download_and_serialize
from src.naip_images import NAIPDownloader

from src.natural_earth import open_vector_file, get_region_extents

def create_parser():
    """Create the argparse parser."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--randomize-naips",
                        default=False,
                        action='store_false',
                        help="turn on this arg if you don't want to get NAIPs in order from the bucket path")
    parser.add_argument("--number-of-naips",
                        default=64,
                        type=int,
                        help="the number of naip images to analyze, 30+ sq. km each")
    parser.add_argument("--naip-year",
                        default='2013',
                        type=str,
                        help="specify the year for the NAIPs to analyze"
                             "--naip-year 2013 (defaults to 2013)")
    parser.add_argument("--extract-type",
                        default='airport',
                        choices=['airport', 'port'],
                        help="the type of feature to identify")
    parser.add_argument("--save-clippings",
                        action='store_true',
                        help="save the training data tiles to /data/naip")
    return parser


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

    state_extents = {}
    get_region_extents(states, ports, state_extents)
    print 'done loading port extents'
    get_region_extents(states, airports, state_extents)
    print 'done loading airport extents'

    args = create_parser().parse_args()

    for naip_state, naip_extents in state_extents.iteritems():
        prenaips = NAIPDownloader(args.number_of_naips,
                                  args.randomize_naips,
                                  naip_state,
                                  args.naip_year,
                                  naip_extents)

        raster_data_paths = prenaips.download_naips()
        print naip_state, len(naip_extents), len(raster_data_paths)

    print 'done'
