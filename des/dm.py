#!/usr/bin/env python
# encoding: utf-8
"""
dm.py

Created by Jakub Konka on 2012-08-22.
Copyright (c) 2012 University of Strathclyde. All rights reserved.
"""
import csv
import logging
import matplotlib.pyplot as plt
import numpy as np
import os
import des.sim as sim
import unittest


class NumericalToolbox:
  """
  Helper class; provides numerical routines.
  """
  @classmethod
  def estimate_bid_hat_function(cls, w, reps, granularity=1000):
    """
    Estimates myopic bidding function when there are 
    two network operators.
    
    Keyword arguments:
    cls -- Class instance
    w -- Price weight
    reps -- List of reputation ratings
    granularity -- (Optional) Sampling granularity
    """
    # Calculate params
    v1 = [(1-w)*reps[0], (1-w)*reps[0] + w]
    v2 = [(1-w)*reps[1], (1-w)*reps[1] + w]
    # Check whether nontrivial NE
    if (v2[1] >= v1[1]):
      if (v1[1] <= 2*v2[0] - v2[1]):
        graph_vf = np.linspace(v1[0], v1[1], granularity)
        bids = list(map(lambda x: v2[0], graph_vf))
      else:
        # Bid bounds
        b = [(4 * v1[0] * v2[0] - (v1[1] + v2[1])**2) / (4 * (v1[0] - v1[1] + v2[0] - v2[1])), (v1[1] + v2[1]) / 2]
        # Constants of integration
        c1 = ((v2[1]-v1[1])**2 + 4*(b[0]-v2[1])*(v1[0]-v1[1])) / (-2*(b[0]-b[1])*(v1[0]-v1[1])) * np.exp((v2[1]-v1[1]) / (2*(b[0]-b[1])))
        c2 = ((v1[1]-v2[1])**2 + 4*(b[0]-v1[1])*(v2[0]-v2[1])) / (-2*(b[0]-b[1])*(v2[0]-v2[1])) * np.exp((v1[1]-v2[1]) / (2*(b[0]-b[1])))
        # Inverse bid function
        vf = lambda x: v1[1] + (v2[1]-v1[1])**2 / (c1*(v2[1]+v1[1]-2*x)*np.exp((v2[1]-v1[1])/(v2[1]+v1[1]-2*x)) + 4*(v2[1]-x))
        # Sampling
        bids = np.linspace(b[0], b[1], granularity)
        graph_vf = list(map(vf, bids))
    else:
      if (v2[1] <= 2*v1[0] - v1[1]):
        graph_vf = np.linspace(v1[0], v1[1], granularity)
        bids = graph_vf
      else:
        # Bid bounds
        b = [(4 * v1[0] * v2[0] - (v1[1] + v2[1])**2) / (4 * (v1[0] - v1[1] + v2[0] - v2[1])), (v1[1] + v2[1]) / 2]
        # Constants of integration
        c1 = ((v2[1]-v1[1])**2 + 4*(b[0]-v2[1])*(v1[0]-v1[1])) / (-2*(b[0]-b[1])*(v1[0]-v1[1])) * np.exp((v2[1]-v1[1]) / (2*(b[0]-b[1])))
        c2 = ((v1[1]-v2[1])**2 + 4*(b[0]-v1[1])*(v2[0]-v2[1])) / (-2*(b[0]-b[1])*(v2[0]-v2[1])) * np.exp((v1[1]-v2[1]) / (2*(b[0]-b[1])))
        # Inverse bid functions
        vf = lambda x: v1[1] + (v2[1]-v1[1])**2 / (c1*(v2[1]+v1[1]-2*x)*np.exp((v2[1]-v1[1])/(v2[1]+v1[1]-2*x)) + 4*(v2[1]-x)) \
              if x <= b[1] else x
        # Sampling
        bids = np.linspace(b[0], v1[1], granularity)
        graph_vf = list(map(vf, bids))
    return bids, graph_vf
  

class Bidder:
  """
  Represents network operator in the Digital Marketplace.
  """
  # ID counter
  _id_counter = 0
  # Default reputation window size
  reputation_window_size = 5
  
  def __init__(self, total_bitrate, costs=None, reputation=0.5):
    """
    Constructs Bidder instance.
    
    Keyword arguments:
    total_bitrate -- Total available bit-rate
    costs -- (Optional) Costs per service type
    reputation -- (Optional) Initial reputation value
    """
    # Create ID for this instance
    self._id = Bidder._id_counter
    # Increment ID counter
    Bidder._id_counter += 1
    # Initialize costs dictionary (key: service type)
    self._costs = {} if costs is None else costs
    # Initialize reputation to default value
    self._reputation = reputation
    # Initialize reputation history list
    self._reputation_history = []
    # Initialize winnings history list
    self._winning_history = []
    # Initialize profit history dict (key: auction number)
    self._profit_history = {}
    # Assign total available bitrate of the network operator
    self._total_bitrate = total_bitrate
    # Initialize available bitrate
    self._available_bitrate = total_bitrate
    # Initialize user success report list
    self._success_list = []
    # Initialize dictionary of service dedicated bitrates
    self._dedicated_bitrates = {}
  
  def __str__(self):
    """
    Returns string representation of the object.
    """
    return "Bidder_" + str(self._id)
  
  @property
  def id(self):
    """
    Returns unique ID of the object.
    """
    return self._id
  
  @property
  def costs(self):
    """
    Returns dictionary of costs (key: service type).
    """
    return self._costs
  
  @property
  def reputation(self):
    """
    Returns current reputation.
    """
    return self._reputation
  
  @property
  def reputation_history(self):
    """
    Returns reputation history.
    """
    return self._reputation_history
  
  @property
  def winning_history(self):
    """
    Returns winning history.
    """
    return self._winning_history
  
  @property
  def profit_history(self):
    """
    Returns profit history.
    """
    return self._profit_history
  
  @property
  def available_bitrate(self):
    """
    Returns available bit-rate.
    """
    return self._available_bitrate
  
  @property
  def success_list(self):
    """
    Returns user success list.
    """
    return self._success_list
  
  def _generate_cost(self, service_type):
    """
    Generates cost for each requested service type.
    
    Keyword arguments:
    service_type -- Type of requested service
    """
    # Check if service type already exists in dict
    if service_type not in self._costs:
      # Get SimulationEngine instance
      se = sim.SimulationEngine()
      # Generate new cost for service type
      self._costs[service_type] = se.prng.uniform(0,1)
  
  def submit_bid(self, service_type, price_weight, enemy_reputation):
    """
    Returns bid for the specified parameters.
    
    Keyword arguments:
    service_type -- Type of requested service
    price_weight -- Price weight requested by the buyer
    enemy_reputation -- Reputation of the other bidder
    """
    # Generate cost for service type
    self._generate_cost(service_type)
    # Save current reputation
    self._reputation_history += [self._reputation]
    # Submit bid
    bid = 0.0
    if price_weight != 0.0 and price_weight != 1.0 and self._reputation != enemy_reputation:
      # Estimate equilibrium bidding strategy functions (bids-hat)
      bids_hat, costs_hat = NumericalToolbox.estimate_bid_hat_function(price_weight, [self._reputation, enemy_reputation])
      # Calculate bid
      dist = list(map(lambda x: np.abs(x - ((1-price_weight)*self._reputation + self._costs[service_type]*price_weight)), costs_hat))
      bid = (bids_hat[dist.index(min(dist))] - (1-price_weight)*self._reputation) / price_weight
    elif price_weight == 0.0:
      bid = "Inf"
      logging.warning("Bid value equal to Inf")
    else:
      # Calculate bid
      bid = (1 + self._costs[service_type]) / 2
    # Temporarily, assuming a win, save bid as profit
    self._current_profit = bid - self._costs[service_type] if price_weight != 0.0 else "Inf"
    return bid
  
  def update_winning_history(self, has_won):
    """
    Updates winning history list.
    
    Keyword arguments:
    has_won -- True if won current auction; false otherwise
    """
    value = 1 if has_won else 0
    if self._winning_history:
      self._winning_history += [self._winning_history[-1] + value]
    else:
      self._winning_history += [value]
  
  def service_request(self, sr_number, service_type):
    """
    Updates params as if network operator has serviced buyer's service request.
    
    Keyword arguments:
    sr_number -- Auction (SR) number
    service_type -- Type of the requested service
    """
    # Save current profit in a profit history dict
    self._profit_history[sr_number] = self._current_profit
    # Update bitrate & reputation
    sr_bitrate = DMEventHandler.BITRATES[service_type]
    # Update available bitrate and store user success report
    if self._available_bitrate >= sr_bitrate:
      self._dedicated_bitrates[sr_number] = sr_bitrate
      self._available_bitrate -= sr_bitrate
      self._success_list += [1]
    else:
      self._dedicated_bitrates[sr_number] = self._available_bitrate
      self._available_bitrate = 0
      self._success_list += [0]
    logging.debug("{} => user success report list: {}".format(self, self._success_list))
    logging.debug("{} => latest user success report: {}".format(self, self._success_list[-1]))
    # Compute reputation rating update
    if len(self._success_list) == Bidder.reputation_window_size:
      self._reputation = 1 - (sum(self._success_list) / len(self._success_list))
      self._success_list.pop(0)
    logging.debug("{} => reputation: {}".format(self, self._reputation))
    logging.debug("{} => service type: {}".format(self, service_type))
    logging.debug("{} => available bitrate: {}".format(self, self._available_bitrate))
    logging.debug("{} => service no. {} dedicated bitrate: {}".format(self, sr_number, self._dedicated_bitrates[sr_number]))
  
  def finish_servicing_request(self, sr_number):
    """
    Updates params when finished servicing buyer's service request.
    
    Keyword arguments:
    sr_number -- Auction (SR) number
    """
    # Update available bitrate
    sr_bitrate = self._dedicated_bitrates[sr_number]
    del self._dedicated_bitrates[sr_number]
    self._available_bitrate += sr_bitrate
    logging.debug("{} => available bit-rate: {}".format(self, self._available_bitrate))
    logging.debug("{} => service no. {} dedicated bit-rate: {}".format(self, sr_number, sr_bitrate))
  

class DMEventHandler(sim.EventHandler):
  """
  Digital Marketplace event handler.
  """
  # Event types
  SR_EVENT = "service_request"
  ST_EVENT = "service_termination"
  # Modeled services and bit-rate requirements
  WEB_BROWSING = 1
  EMAIL = 2
  # Default bit-rates
  BITRATES = {WEB_BROWSING: 512, EMAIL: 256}
  
  def __init__(self):
    """
    Constructs DMEventHandler instance
    """
    super().__init__()
    ### Simulation building blocks and params
    # Initialize list of bidders
    self._bidders = []
    # Initialize service requests mean interarrival rate
    self._interarrival_rate = 0
    # Initialize service requests duration
    self._duration = 0
    # Initialize save directory
    self._save_dir = ""
    # Initialize simulation id
    self._sim_id = -1
    # Initialize service request counter
    self._sr_count = 0
    # Initialize price per service type history list
    self._prices = {}
  
  @property
  def bidders(self):
    """
    Returns list of bidders.
    """
    return self._bidders
  
  @bidders.setter
  def bidders(self, bidders):
    """
    Adds Bidder instances.
    """
    self._bidders = bidders
  
  @property
  def interarrival_rate(self):
    """
    Returns the mean interarrival rate of service requests.
    """
    return self._interarrival_rate
  
  @interarrival_rate.setter
  def interarrival_rate(self, interarrival_rate):
    """
    Sets the mean interarrival rate of service requests.
    """
    self._interarrival_rate = interarrival_rate
  
  @property
  def duration(self):
    """
    Returns the duration of service requests.
    """
    return self._duration
  
  @duration.setter
  def duration(self, duration):
    """
    Sets the duration of service requests.
    """
    self._duration = duration
  
  @property
  def save_dir(self):
    """
    Returns save directory.
    """
    return self._save_dir
  
  @save_dir.setter
  def save_dir(self, save_dir):
    """
    Sets save directory.
    """
    self._save_dir = save_dir
  
  @property
  def sim_id(self):
    """
    Returns simulation id.
    """
    return self._sim_id
  
  @sim_id.setter
  def sim_id(self, sim_id):
    """
    Sets simulation id.
    """
    self._sim_id = sim_id
  
  def _handle_start(self):
    """
    Overriden
    """
    self._schedule_sr_event(self._simulation_engine.simulation_time)
  
  def _handle_stop(self):
    """
    Overriden
    """
    # Save results of the simulation
    self._save_results()
  
  def _handle_event(self, event):
    """
    Overriden
    """
    logging.debug("{} @ Received event => {}".format(self._simulation_engine.simulation_time, event.identifier))
    if event.identifier == DMEventHandler.SR_EVENT:
      # Run auction
      self._run_auction(event)
      # Schedule next service request event
      self._schedule_sr_event(event.time)
    elif event.identifier == DMEventHandler.ST_EVENT:
      # A bidder finished handling request
      bidder, sr_number = event.kwargs.get('bundle', None)
      bidder.finish_servicing_request(sr_number)
    else:
      # End of simulation event
      pass
  
  def _schedule_sr_event(self, base_time):
    """
    Schedules next service request event.
    """
    prng = self._simulation_engine.prng
    # Generate buyer (service type & price weight pair)
    price_weight = prng.uniform(0, 1)
    service_type = prng.choice(list(DMEventHandler.BITRATES.keys()), 1)[0]
    # Calculate interarrival time
    delta_time = prng.exponential(1 / self._interarrival_rate)
    # Create next service request event
    event = sim.Event(DMEventHandler.SR_EVENT, base_time + delta_time, bundle=(price_weight, service_type))
    # Schedule the event
    self._simulation_engine.schedule(event)
  
  def _schedule_st_event(self, base_time, bundle):
    """
    Schedules next service request termination event.
    """
    prng = self._simulation_engine.prng
    # Calculate duration
    delta_time = prng.exponential(self._duration)
    # Create next service termination event
    event = sim.Event(DMEventHandler.ST_EVENT, base_time + delta_time, bundle=bundle)
    # Schedule the event
    self._simulation_engine.schedule(event)
  
  def _run_auction(self, event):
    """
    Runs DM auction.
    """
    # Increment service request counter
    self._sr_count += 1
    # Get requested price weight and service type
    w, service_type = event.kwargs.get('bundle', None)
    # Get bids from bidders
    bids = [self._bidders[0].submit_bid(service_type, w, self._bidders[1].reputation)]
    bids += [self._bidders[1].submit_bid(service_type, w, self._bidders[0].reputation)]
    # Elect the winner
    compound_bids = [w*bids[i] + (1-w)*self._bidders[i].reputation for i in range(2)]
    winner = 0
    if compound_bids[0] < compound_bids[1]:
      # Bidder 1 wins
      winner = 0
    elif compound_bids[0] > compound_bids[1]:
      # Bidder 2 wins
      winner = 1
    else:
      # Tie
      winner = self._simulation_engine.prng.randint(2)
    # Collect statistics & update system state
    self._prices.setdefault(service_type,([],[]))
    self._prices[service_type][0].append(self._sr_count)
    self._prices[service_type][1].append(bids[winner])
    winner = self._bidders[winner]
    for b in self._bidders:
      b.update_winning_history(True if b == winner else False)
    winner.service_request(self._sr_count, service_type)
    # Schedule termination event
    self._schedule_st_event(event.time, (winner, self._sr_count))
  
  def _save_results(self):
    """
    Saves results of the simulation.
    """
    # Create output directory if doesn't exist already
    path = self._save_dir + '/' + str(self._sim_id)
    if not os.path.exists(path):
      os.makedirs(path)
    # Write output data to files
    for b in self._bidders:
      # 1. Reputation history
      with open(path + '/reputation_{}.out'.format(str(b).lower()), mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=',')
        writer.writerow(['sr_number', 'reputation'])
        for tup in zip(range(1, self._sr_count+1), b.reputation_history):
          writer.writerow(tup)
      # 2. History of won auctions (market share)
      with open(path + '/winnings_{}.out'.format(str(b).lower()), mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=',')
        writer.writerow(['sr_number', 'winnings'])
        for tup in zip(range(1, self._sr_count+1), b.winning_history):
          writer.writerow(tup)
    # 3. Prices per service type
    for key in self._prices:
      with open(path + '/price_{}.out'.format(key), mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=',')
        writer.writerow(['sr_number', 'price'])
        for tup in zip(self._prices[key][0], self._prices[key][1]):
          writer.writerow(tup)
  

class BidderTests(unittest.TestCase):
  def setUp(self):
    pass
  

class DMEventHandlerTests(unittest.TestCase):
  def setUp(self):
    pass
  

if __name__ == '__main__':
  unittest.main()