#!/usr/bin/env python
# encoding: utf-8
"""
main.py

Created by Jakub Konka on 2012-07-23.
Copyright (c) 2012 University of Strathclyde. All rights reserved.
"""
import argparse
import simulator.modules.dm as dm
import simulator.modules.sim as sim
import logging
import numpy as np
import sys
import time


### Parse command line arguments
parser = argparse.ArgumentParser(description="DM simulation -- Main script")
parser.add_argument('sim_duration', metavar='simulation_duration',
                    type=int, help='simulation duration in seconds')
parser.add_argument('--id', dest='id', default=0,
                    type=int, help='simulation run id (default: 0)')
parser.add_argument('--seed', dest='seed', default=int(round(time.time())),
                    type=int, help='seed for the PRNG (default: current system timestamp)')
parser.add_argument('--save_dir', dest='save_dir', default='out',
                    help='output directory')
parser.add_argument('--log', dest='log_level', default='INFO',
                    help='set logging level (default: INFO)')
parser.add_argument('--logfile', dest='log_file', default=None,
                    help='set output log file (default: None)')
args = parser.parse_args()
sim_duration = args.sim_duration
sim_id = args.id
seed = args.seed
save_dir = args.save_dir
log_level = args.log_level
log_file = args.log_file

### Logging
numeric_level = getattr(logging, log_level.upper(), 'INFO')
if not isinstance(numeric_level, int):
  raise ValueError("Invalid log level: {}".format(log_level))
logging.basicConfig(filename=log_file, level=numeric_level)
logging.info("Simulation duration set to: {}".format(sim_duration))

### Create simulation-specific scenario
# Create Bidders
bidders = [
    dm.Bidder(10000, costs={dm.DMEventHandler.WEB_BROWSING: 0.5},
      bidding_params={'method': 'myopic'}, reputation=0.0,
      reputation_params={'method': 'lebodic', 'window_size': 5}),
    dm.Bidder(10000, costs={dm.DMEventHandler.WEB_BROWSING: 0.5},
      bidding_params={'method': 'myopic'}, reputation=0.0,
      reputation_params={'method': 'lebodic', 'window_size': 5})] 
# Service requests mean interarrival rate (per second)
interarrival_rate = 1
# Service requests constant duration (in seconds)
duration = 2.5 * 60
# Service types and bit-rates
bitrates = {dm.DMEventHandler.WEB_BROWSING: 512}

### Initialize
# Create new simulation engine
se = sim.SimulationEngine()
# Use NumPy PRNG with custom seed
prng = np.random.RandomState(seed)
se.prng = prng
logging.info("Seed value set to: {}".format(seed))
# Create simulation specific event handler, and connect
# it with the simulation engine
event_handler = dm.DMEventHandler(se)
se.event_handler = event_handler
# Add bidders to simulation engine
event_handler.bidders = bidders
# Set modeled service types
dm.DMEventHandler.BITRATES = bitrates
# Set params
event_handler.interarrival_rate = interarrival_rate
event_handler.duration = duration
event_handler.save_dir = save_dir
event_handler.sim_id = sim_id

### Simulate
# Schedule finishing event
se.stop(sim_duration)
# Start simulating
logging.info("Simulation started")
se.start()
logging.info("Simulation finished")

