"""A class to download NAIP imagery from the s3://aws-naip RequesterPays bucket."""

import boto3
import os
import subprocess
import sys
import time
from random import shuffle
from src.config import cache_paths, create_cache_directories, NAIP_DATA_DIR, LABELS_DATA_DIR


class NAIPDownloader:
    """Downloads NAIP images from S3, by state/year."""

    def __init__(self, number_of_naips, should_randomize, state, year, extent=None):
        """
        Download some arbitrary NAIP images from the aws-naip S3 bucket.
        
        extent (optional) should be a 4-tuple of decimal degrees (x_left, y_bottom, x_right, y_top)
        """
        self.number_of_naips = number_of_naips
        self.should_randomize = should_randomize

        self.state = state
        self.year = year
        self.resolution = '1m'
        self.spectrum = 'rgbir'
        self.bucket_url = 's3://aws-naip/'
        self.extent = extent

        self.url_base = '{}{}/{}/{}/{}/'.format(self.bucket_url, self.state, self.year, self.resolution, self.spectrum)

        self.make_directory(NAIP_DATA_DIR)

    def make_directory(self, new_dir):
        """Make a new directory tree if it doesn't already exist."""
        if not os.path.exists(new_dir):
            os.makedirs(new_dir)

    def download_naips(self):
        """Download self.number_of_naips of the naips for a given state."""
        create_cache_directories()
        self.configure_s3cmd()
        naip_filenames = self.list_naips()
        if self.should_randomize:
            shuffle(naip_filenames)
        naip_local_paths = self.download_from_s3(naip_filenames)
        cache_paths(naip_local_paths)
        return naip_local_paths

    def configure_s3cmd(self):
        """Configure s3cmd with AWS credentials."""
        file_path = os.environ.get("HOME") + '/.s3cfg'
        f = open(file_path, 'r')
        filedata = f.read()
        f.close()
        access = os.environ.get("AWS_ACCESS_KEY_ID")
        secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
        newdata = filedata.replace("AWS_ACCESS_KEY", access)
        newdata = newdata.replace("AWS_SECRET_KEY", secret)
        f = open(file_path, 'w')
        f.write(newdata)
        f.close()

    def list_naips(self):
        """Make a list of NAIPs based on the init parameters for the class."""
        # list the contents of the bucket directory
        bash_command = "s3cmd ls --recursive --skip-existing {} --requester-pays".format(self.url_base)
        process = subprocess.Popen(bash_command.split(" "), stdout=subprocess.PIPE)
        output = process.communicate()[0]
        naip_filenames = []
        print(output)
        for line in output.split('\n'):
            parts = line.split(self.url_base)
            # there may be subdirectories for each state, where directories need to be made
            if len(parts) == 2:
                naip_path = parts[1]
                if not self.naip_in_extent(naip_path):
                    continue
                print(parts)

                naip_filenames.append(naip_path)
                naip_subpath = os.path.join(NAIP_DATA_DIR, naip_path.split('/')[0])
                if not os.path.exists(naip_subpath):
                    os.mkdir(naip_subpath)
                labels_subpath = os.path.join(LABELS_DATA_DIR, naip_path.split('/')[0])
                if not os.path.exists(labels_subpath):
                    os.mkdir(labels_subpath)
            else:
                pass
                # skip non filename lines from response

        return naip_filenames

    def naip_in_extent(self, naip_path):
        """
        # Added by WMIV on 3/31/17
        :param naip_path: 
        :type naip_path: 
        :return: 
        :rtype: 
        """
        if self.extent is None:
            return True
        ns_map = {'n': 0, 's': 1}
        we_map = {'w': 0, 'e': 1}
        e_left, e_right = self.extent[0], self.extent[2]
        e_bottom, e_top = self.extent[1], self.extent[3]
        naip_fname = naip_path.split('/')[1]
        lat = (float(naip_fname[2:4]) + 1)
        lon = (float(naip_fname[4:7]) + 1) * -1
        pix = int(naip_fname[7:9])
        n_or_s = naip_fname[10]
        assert n_or_s in ns_map.keys()
        w_or_e = naip_fname[11]
        assert w_or_e in we_map.keys()
        col = (pix - 1) % 8
        row = (pix - 1) / 8

        n_left = lon + (col / 8.0 + we_map[w_or_e] / 16.0)
        n_top = lat - (row / 8.0 + ns_map[n_or_s] / 16.0)
        n_right = n_left + 1 / 16.0
        n_bottom = n_top - 1 / 16.0

        if n_left <= e_right and n_right >= e_left and n_top >= e_bottom and n_bottom <= e_top:
            return True

        return False

    def naip_in_extent_orig(self, naip_path):
        if self.extent is None:
            return True
        x_left, x_right = int(self.extent[0]), int(self.extent[2])
        y_bottom, y_top = int(self.extent[1]), int(self.extent[3])
        lat_lon_str = naip_path.split('/')[0]
        lat = int(lat_lon_str[:2])
        lon = int(lat_lon_str[2:]) * -1  # naip only in USA so it's safe to assume negative longitude.
        if x_left <= lon <= x_right and y_bottom <= lat <= y_top:
            return True
        return False

    def download_from_s3(self, naip_filenames):
        """Download the NAIPs and return a list of the file paths."""
        s3_client = boto3.client('s3')
        naip_local_paths = []
        max_range = self.number_of_naips
        if max_range == -1:
            max_range = len(naip_filenames)
        t0 = time.time()
        has_printed = False
        for filename in naip_filenames[0:max_range]:
            # for filename in ['m_3807708_ne_18_1_20130924.tif']:
            full_path = os.path.join(NAIP_DATA_DIR, filename)
            if os.path.exists(full_path):
                print("NAIP {} already downloaded".format(full_path))
            else:
                if not has_printed:
                    print("DOWNLOADING {} NAIPs...".format(max_range))
                    has_printed = True
                url_without_prefix = self.url_base.split(self.bucket_url)[1]
                s3_url = '{}{}'.format(url_without_prefix, filename)
                s3_client.download_file('aws-naip', s3_url, full_path, {'RequestPayer': 'requester'})
            naip_local_paths.append(full_path)
        if time.time() - t0 > 0.01:
            print("downloads took {0:.1f}s".format(time.time() - t0))
        return naip_local_paths


if __name__ == '__main__':
    parameters_message = "parameters are: download"
    if len(sys.argv) == 1:
        print(parameters_message)
    elif sys.argv[1] == 'download':
        extent = (-86.823, 34.505, -86.367, 34.927)
        naiper = NAIPDownloader(256, False, 'al', '2015', extent=extent)
        naiper.download_naips()
    else:
        print(parameters_message)
