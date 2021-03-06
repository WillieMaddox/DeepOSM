#!/usr/bin/env python

"""Post test results to S3. This class is probably not relevant to you, it's for deeposm.org."""

import pickle
from src.config import METADATA_FILE, RASTER_DATAPATHS_FILE
from src.s3_client_deeposm import post_findings_to_s3
from src.single_layer_network import load_model, MODEL_METADATA_FILE


def main():
    """Post test results to an S3 bucket."""
    with open(RASTER_DATAPATHS_FILE, 'r') as infile:
        raster_data_paths = pickle.load(infile)

    with open(METADATA_FILE, 'r') as infile:
        training_info = pickle.load(infile)

    with open(MODEL_METADATA_FILE, 'r') as infile:
        model_info = pickle.load(infile)

    model = load_model(model_info['neural_net_type'], model_info['tile_size'],
                       len(model_info['bands']))
    post_findings_to_s3(raster_data_paths, model, training_info, model_info['bands'], False)


if __name__ == "__main__":
    main()
