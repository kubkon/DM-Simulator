#!/usr/bin/env python
# encoding: utf-8
"""
plot.py

Created by Jakub Konka on 2012-10-08.
Copyright (c) 2012 University of Strathclyde. All rights reserved.
"""
import argparse
from csv import DictReader
from itertools import cycle
import matplotlib.pyplot as plt
import os


def load_data(search_phrase, input_dir):
  dct = {}
  ext = '.out'
  file_names = [f[:f.find(ext)] for _, _, files in os.walk(input_dir) for f in files if f.endswith(ext)]
  for fn in filter(lambda x: search_phrase in x, file_names):
    dct[fn] = {}
    with open(input_dir + '/' + fn + ext, 'rt') as f:
      reader = DictReader(f)
      for row in reader:
        for key in row:
          val = float(row[key]) if key != 'sr_number' else int(row[key])
          dct[fn].setdefault(key,[]).append(val)
  return dct

def plot_with_ci(sub_dct, identifier, save_dir):
  plt.figure()
  plt.errorbar(sub_dct['sr_number'], sub_dct['mean'], yerr=sub_dct['ci'], fmt='ro')
  plt.xlabel('Service request')
  separator = identifier.find('_')
  ylabel = identifier[:separator] if separator != -1 else identifier
  plt.ylabel(ylabel[0].upper() + ylabel[1:])
  plt.grid()
  plt.savefig(save_dir + '/' + identifier + '.pdf')

def plot_overlaid(dct, save_dir):
  if len(dct.keys()) > 1:
    plt.figure()
    legend = []
    styles = cycle(['-', '--', '_', ':'])
    for key in dct:
      plt.plot(dct[key]['sr_number'], dct[key]['mean'], next(styles))
      separator = key.find('_')
      legend += [key[separator+1:]]
      ylabel = key[:separator] if separator != -1 else key
    plt.xlabel('Service request')
    plt.ylabel(ylabel[0].upper() + ylabel[1:])
    plt.legend(legend)
    plt.grid()
    plt.savefig(save_dir + '/' + ylabel + '.pdf')


### Parse command line arguments
parser = argparse.ArgumentParser(description='DM simulation plotting script')
parser.add_argument('input_dir', metavar='input_dir',
                    help='input directory')
parser.add_argument('context', metavar='context',
                    help='data context; e.g., price, or reputation')
args = parser.parse_args()
input_dir = args.input_dir
context = args.context

### Load and plot
# Load context data from files
dct = load_data(context, input_dir)
# Plot
# Figure 1..k=num of bidders: data with confidence intervals
for key in dct:
  plot_with_ci(dct[key], key, input_dir)
# Figure k+1: all data same plot
plot_overlaid(dct, input_dir)
