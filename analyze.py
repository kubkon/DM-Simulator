#!/usr/bin/env python
# encoding: utf-8
"""
analyze.py

Created by Jakub Konka on 2012-10-23.
Copyright (c) 2012 University of Strathclyde. All rights reserved.
"""
import argparse
import csv
from itertools import cycle
import matplotlib.pyplot as plt
import numpy as np
import os
import os.path
import scipy.stats as stats


### Parse command line arguments
parser = argparse.ArgumentParser(description="DM simulation -- Analysis script")
parser.add_argument('save_dir', help='output directory')
parser.add_argument('--confidence', dest='confidence', default=0.99,
                    type=float, help='confidence value (default: 0.99)')
args = parser.parse_args()
save_dir = args.save_dir
confidence = args.confidence

### Merge results from files
# Get files (as strings)
extension = ".out"
file_names = set([f[:f.find(extension)] for _, _, files in os.walk(save_dir) for f in files if f.endswith(extension)])
file_paths = [os.path.join(root, f) for root, _, files in os.walk(save_dir) for f in files if f.endswith(extension)]
# Initial processing of data (includes warm-up period)
ref_column = 'sr_number'
for name in file_names:
  # Read data from files
  data_in = []
  for fp in file_paths:
    if name in fp:
      with open(fp, 'rt') as f:
        reader = csv.DictReader(f)
        dct = {}
        for row in reader:
          for key in row:
            val = float(row[key]) if key != ref_column else int(row[key])
            dct.setdefault(key, []).append(val)
        data_in.append(dct)
  # Reduce...
  # Get number of replications (equal to number of dictionaries in data_in)
  repetitions = len(data_in)
  # Compute mean
  zipped = zip(*[dct[key] for dct in data_in for key in dct.keys() if key != ref_column])
  means = list(map(lambda x: sum(x)/repetitions, zipped))
  # Compute standard deviation
  zipped = zip(*[dct[key] for dct in data_in for key in dct.keys() if key != ref_column])
  sds = [np.sqrt(sum(map(lambda x: (x-mean)**2, tup)) / (repetitions - 1)) for (tup, mean) in zip(zipped, means)]
  # Compute standard error for the mean
  ses = list(map(lambda x: x/np.sqrt(repetitions), sds))
  # Compute confidence intervals for the mean
  cis = list(map(lambda x: x * stats.t.ppf(0.5 + confidence/2, repetitions-1), ses))
  # Save to a file
  with open(save_dir + '/' + name + extension, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f, delimiter=',')
    zip_input = [data_in[0][ref_column], means, sds, ses, cis]
    out_headers = [ref_column, 'mean', 'sd', 'se', 'ci']
    writer.writerow(out_headers)
    for tup in zip(*zip_input):
      writer.writerow(tup)
