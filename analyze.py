#!/usr/bin/env python
# encoding: utf-8
"""
analyze.py

Created by Jakub Konka on 2012-10-23.
Copyright (c) 2012 University of Strathclyde. All rights reserved.
"""
import argparse
import csv
import numpy as np
import os
import os.path
import scipy.stats as stats
import sys


### Parse command line arguments
parser = argparse.ArgumentParser(description="DM simulation -- Statistical analysis script")
parser.add_argument('input_dir', help='directory with simulation results')
parser.add_argument('context', help='data context; e.g., price, or reputation')
parser.add_argument('mode', help='transient or steady-state')
parser.add_argument('--confidence', dest='confidence', default=0.99,
                    type=float, help='confidence value (default: 0.99)')
args = parser.parse_args()
input_dir = args.input_dir
context = args.context
mode = args.mode.lower()
confidence = args.confidence

### Common params
# Ask for warm-up period index (if mode is steady-state)
if mode == 'steady-state':
  warmup = int(input('Warm-up period index: '))
elif mode == 'transient':
  warmup = 0
  window_size = int(input('Window size: '))
else:
  sys.exit('Unknown mode specified.')
# File names and paths
extension = ".out"
file_names = set([f[:f.find(extension)] for root, _, files in os.walk(input_dir) for f in files \
                  if f.endswith(extension) \
                  and context in f \
                  and 'transient' not in root \
                  and 'steady-state' not in root])
file_paths = [os.path.join(root, f) for root, _, files in os.walk(input_dir) for f in files \
              if f.endswith(extension) \
              and context in f \
              and 'transient' not in root \
              and 'steady-state' not in root]
# Reference column
ref_column = 'sr_number'

### Merge results from files
for name in file_names:
  # Read data from files
  data_in = []
  for fp in file_paths:
    if name in fp:
      with open(fp, 'rt') as f:
        reader = csv.DictReader(f)
        dct = {}
        for row in reader:
          # Exclude data with index lower than specified warm-up period
          if int(row[ref_column]) > warmup:
            for key in row:
              val = float(row[key]) if key != ref_column else int(row[key])
              dct.setdefault(key, []).append(val)
        data_in.append(dct)
  # Map and reduce...
  if mode == 'steady-state':
    # Compute steady-state mean average
    averages = [sum(dct[key]) / len(dct[key]) for dct in data_in for key in dct.keys() if key != ref_column]
    mean = sum(averages) / len(averages)
    # Compute standard deviation
    sd = np.sqrt(sum(map(lambda x: (x-mean)**2, averages)) / (len(averages)-1))
    # Compute standard error for the mean
    se = sd / np.sqrt(len(averages))
    # Compute confidence intervals for the mean
    ci = se * stats.t.ppf(0.5 + confidence/2, len(averages)-1)
    # Save to a file
    # Create save dir if doesn't exist already
    save_dir = input_dir + '/' + mode
    if not os.path.exists(save_dir):
      os.makedirs(save_dir)
    with open(save_dir + '/' + name + extension, 'w', newline='', encoding='utf-8') as f:
      writer = csv.writer(f, delimiter=',')
      writer.writerow(['mean', 'sd', 'se', 'ci'])
      writer.writerow([mean, sd, se, ci])
  else:
    # Compute mean
    zipped = zip(*[dct[key] for dct in data_in for key in dct.keys() if key != ref_column])
    init_means = list(map(lambda x: sum(x)/len(data_in), zipped))
    means = []
    if window_size == 0:
      means = init_means
    else:
      for i in range(len(init_means) - window_size):
        if i < window_size:
          means += [sum([init_means[i+s] for s in range(-i, i+1)]) / (2*(i+1) - 1)]
        else:
          means += [sum([init_means[i+s] for s in range(-window_size, window_size+1)]) / (2*window_size + 1)]
    # Compute standard deviation
    zipped = zip(*[dct[key] for dct in data_in for key in dct.keys() if key != ref_column])
    sds = [np.sqrt(sum(map(lambda x: (x-mean)**2, tup)) / (len(means) - 1)) for (tup, mean) in zip(zipped, means)]
    # Compute standard error for the mean
    ses = list(map(lambda x: x/np.sqrt(len(means)), sds))
    # Compute confidence intervals for the mean
    cis = list(map(lambda x: x * stats.t.ppf(0.5 + confidence/2, len(means)-1), ses))
    # Save to a file
    # Create save dir if doesn't exist already
    save_dir = input_dir + '/' + mode + '_{}'.format(window_size)
    if not os.path.exists(save_dir):
      os.makedirs(save_dir)
    with open(save_dir + '/' + name + extension, 'w', newline='', encoding='utf-8') as f:
      writer = csv.writer(f, delimiter=',')
      zip_input = [data_in[0][ref_column], means, sds, ses, cis]
      out_headers = [ref_column, 'mean', 'sd', 'se', 'ci']
      writer.writerow(out_headers)
      for tup in zip(*zip_input):
        writer.writerow(tup)
