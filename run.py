#!/usr/bin/env python
# encoding: utf-8
"""
run.py

Created by Jakub Konka on 2012-10-05.
Copyright (c) 2012 University of Strathclyde. All rights reserved.
"""
import argparse
import csv
import numpy as np
import os
import os.path
import re
import scipy.stats as stats
import subprocess as sub


### Parse command line arguments
parser = argparse.ArgumentParser(description="DM simulation helper script")
parser.add_argument('reps', metavar='repetitions',
                    type=int, help='number of repetitions')
parser.add_argument('sim_duration', metavar='simulation_duration',
                    type=int, help='duration of each simulation stage in seconds')
parser.add_argument('--batch_size', dest='batch_size', default=4,
                    type=int, help='batch size for multiprocessing')
parser.add_argument('--save_dir', dest='save_dir', default='out',
                    help='output directory')
parser.add_argument('--initial_seed', dest='init_seed', default=0,
                    type=int, help='base for seed values')
parser.add_argument('--confidence', dest='confidence', default=0.99,
                    type=float, help='confidence value (default: 0.99)')
args = parser.parse_args()
repetitions = args.reps
sim_duration = args.sim_duration
batch_size = args.batch_size
save_dir = args.save_dir
init_seed = args.init_seed
confidence = args.confidence

### Run simulations
try:
  # One process at a time
  if batch_size == 1:
    for n in range(repetitions):
      sub.call("python main.py {} --seed={} --id={} --save_dir={}".format(sim_duration, n+init_seed, n, save_dir), shell=True)
  # In batches
  else:
    # Split num of repetitions into batches
    quotient = repetitions // batch_size
    remainder = repetitions % batch_size
    # Run the simulations in parallel as subprocesses
    num_proc = batch_size if batch_size <= repetitions else remainder
    procs = [sub.Popen("python main.py {} --seed={} --id={} --save_dir={}".format(sim_duration, n+init_seed, n, save_dir), shell=True) for n in range(num_proc)]
    while True:
      procs_poll = list(map(lambda x: x.poll() != None, procs))
      if not all(procs_poll):
        procs[procs_poll.index(False)].wait()
      elif num_proc < repetitions:
        temp_num = batch_size if num_proc + batch_size <= repetitions else remainder
        for n in range(num_proc, num_proc + temp_num):
          procs += [sub.Popen("python main.py {} --seed={} --id={} --save_dir={}".format(sim_duration, n+init_seed, n, save_dir), shell=True)]
        num_proc += temp_num
      else:
        break
except OSError as e:
  print("Execution failed: ", e)

### Merge results from files
# Get files (as strings)
extension = ".out"
file_names = set([f[:f.find(extension)] for _, _, files in os.walk(save_dir) for f in files if f.endswith(extension)])
file_paths = [os.path.join(root, f) for root, _, files in os.walk(save_dir) for f in files if f.endswith(extension)]
dirs = map(lambda x: save_dir + '/' + x, os.listdir(save_dir))
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

### Save initial conditions to a file (reference)
stream = []
phrase = '### Create simulation-specific scenario'
record_flag = False
with open('main.py', encoding='utf-8') as f:
  for line in f:
    if phrase in line:
      record_flag = True
    if record_flag:
      stream += [line]
    if re.match('^\s$', line):
      record_flag = False
with open(save_dir + '/initial.out', mode='w', encoding='utf-8') as f:
  for line in stream:
    f.write(line)
