#!/usr/bin/env python
# encoding: utf-8
"""
dm.py

Created by Jakub Konka on 2012-08-22.
Copyright (c) 2012 University of Strathclyde. All rights reserved.
"""
import csv
import functools
import logging
import matplotlib.pyplot as plt
import numpy as np
import os
import re
import simulator.errors as errors
import simulator.modules.sim as sim
import unittest
import warnings


class BidderHelper:
  """
  Helper class which implements:
  - bidding behaviors;
  - reputation rating update mechanisms.
  """
  def __init__(self):
    """
    Constructs BidderHelper instance.
    """
    self.implemented_methods = {
        'lebodic': {
          'method': self.lebodics_reputation_update,
          'params': ['window_size']
          },
        'mcdiarmid': {
          'method': self.mcdiarmids_reputation_update,
          'params': ['commitment']
          },
        'myopic': {
          'method': self.myopic_bidding,
          'params': []
          },
        }

  def method(self, params):
    """
    Returns a method inferred from the specified
    params.

    Arguments:
    params -- Passed in params as dict
    """
    if 'method' not in params:
      raise errors.UnknownMethodError(params)
    elif params['method'] not in self.implemented_methods:
      raise errors.UnknownMethodError(params)
    else:
      method_name = params['method']
      for param in self.implemented_methods[method_name]['params']:
        if param not in params:
          raise errors.UnknownMethodError(params)
      args = [params[p] for p in self.implemented_methods[method_name]['params']]
      return functools.partial(self.implemented_methods[method_name]['method'], *args)

  def myopic_bidding(self, price_weight, cost, reputation, enemy_reputation):
    """
    Returns bid calculated using myopic bidding approach.

    Arguments:
    price_weight -- Subscriber's price weight
    cost -- Network operator's cost
    reputation -- Network operator's reputation
    enemy_reputation -- Other network operator's reputation
    """
    def estimate_bid_hat_function(w, reps, granularity=1000):
      warnings.simplefilter('error', RuntimeWarning)
      # Calculate params
      v1 = [(1-w)*reps[0], (1-w)*reps[0] + w]
      v2 = [(1-w)*reps[1], (1-w)*reps[1] + w]
      # Account for numerical imprecission
      my_round = lambda x: round(x, 6)
      v1 = list(map(my_round, v1))
      v2 = list(map(my_round, v2))
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
          def vf(x):
            try:
              return v1[1] + (v2[1]-v1[1])**2 / (c1*(v2[1]+v1[1]-2*x)*np.exp((v2[1]-v1[1])/(v2[1]+v1[1]-2*x)) + 4*(v2[1]-x))
            except RuntimeWarning as e:
              if (re.search('.*overflow encountered in exp.*', str(e)) or
                 re.search('.*divide by zero encountered in double_scalars.*', str(e))):
                return v1[1]
              else:
                raise RuntimeWarning(e)
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
          vf = lambda x: (v1[1] + (v2[1]-v1[1])**2 / (c1*(v2[1]+v1[1]-2*x)*np.exp((v2[1]-v1[1])/(v2[1]+v1[1]-2*x)) + 4*(v2[1]-x))
                if x <= b[1] else x)
          # Sampling
          bids = np.linspace(b[0], v1[1], granularity)
          graph_vf = list(map(vf, bids))
      return bids, graph_vf

    if price_weight != 0.0 and price_weight != 1.0 and reputation != enemy_reputation:
      # Estimate equilibrium bidding strategy functions (bids-hat)
      bids_hat, costs_hat = estimate_bid_hat_function(price_weight, [reputation, enemy_reputation])
      # Calculate bid
      dist = list(map(lambda x: np.abs(x - ((1-price_weight)*reputation + cost*price_weight)), costs_hat))
      return (bids_hat[dist.index(min(dist))] - (1-price_weight)*reputation) / price_weight
    elif price_weight == 0.0:
      # Return the highest possible bid
      return float('inf')
    else:
      # Calculate bid
      return (1 + cost) / 2

  def lebodics_reputation_update(self, window_size, reputation, success_list):
    """
    Returns reputation rating update calculated according to
    LeBodic's algorithm.

    Arguments:
    window_size -- Window size
    reputation -- Current reputation rating
    success_list -- Current user's success report list
    """
    if len(success_list) >= window_size:
      return 1 - (sum(success_list[len(success_list)-window_size:]) / window_size)
    else:
      return reputation

  def mcdiarmids_reputation_update(self, commitment, reputation, success_list):
    """
    Returns reputation rating update calculated according to
    McDiarmid's algorithm.

    Arguments:
    commitment -- Commitment of network operator (ranges from 0.0 to 1.0)
    reputation -- Current reputation rating
    success_list -- Current user's success report list
    """
    if success_list[-1]:
      return reputation - 0.01 if reputation >= 0.01 else 0.0
    else:
      penalty = commitment / 100 / (1-commitment)
      return reputation + penalty if reputation + penalty <= 1.0 else 1.0


class Bidder:
  """
  Represents network operator in the Digital Marketplace.
  """
  # ID counter
  _id_counter = 0
  
  def __init__(self, total_bitrate=None, costs=None, bidding_params=None,
      reputation=None, reputation_params=None):
    """
    Constructs Bidder instance.
    
    Keyword arguments:
    total_bitrate -- Total available bit-rate
    costs -- Costs per service type
    bidding_params -- Bidding parameters
    reputation -- Initial reputation value
    reputation_params -- Reputation update specific params
    """
    # Check if arguments were specified
    if None in (total_bitrate, costs, bidding_params, reputation, reputation_params):
      raise errors.UninitializedArgumentError() 
    # Create ID for this instance
    self._id = Bidder._id_counter
    # Increment ID counter
    Bidder._id_counter += 1
    # Initialize costs dictionary (key: service type)
    self._costs = costs
    # Assign bidding method
    self._bidder_helper = BidderHelper()
    self._bidding_method = self._bidder_helper.method(bidding_params)
    # Initialize reputation
    self._reputation = reputation
    # Assign total available bitrate of the network operator
    self._total_bitrate = total_bitrate
    # Initialize available bitrate
    self._available_bitrate = total_bitrate
    # Assign reputation rating update method
    self._reputation_update_method = self._bidder_helper.method(reputation_params)
    # Initialize reputation history list
    self._reputation_history = []
    # Initialize winnings history list
    self._winning_history = []
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
  def total_bitrate(self):
    """
    Returns total bit-rate.
    """
    return self._total_bitrate

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
    
    Arguments:
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
    
    Arguments:
    service_type -- Type of requested service
    price_weight -- Price weight requested by the buyer
    enemy_reputation -- Reputation of the other bidder
    """
    # Generate cost for service type
    self._generate_cost(service_type)
    # Save current reputation
    self._reputation_history += [self._reputation]
    # Submit bid
    return self._bidding_method(price_weight, self.costs[service_type], self.reputation, enemy_reputation)
  
  def update_winning_history(self, has_won):
    """
    Updates winning history list.
    
    Arguments:
    has_won -- True if won current auction; false otherwise
    """
    value = 1 if has_won else 0
    if self._winning_history:
      self._winning_history += [self._winning_history[-1] + value]
    else:
      self._winning_history += [value]
 
  def _update_available_bitrate(self, sr_number, service_type=None):
    """
    Updates available bitrate.

    Arguments:
    sr_number -- Auction (SR) number
    
    Keyword arguments:
    service_type -- Type of the requested service
    """
    if service_type:
      sr_bitrate = DMEventHandler.BITRATES[service_type]
      if self._available_bitrate >= sr_bitrate:
        self._dedicated_bitrates[sr_number] = sr_bitrate
        self._available_bitrate -= sr_bitrate
      else:
        self._dedicated_bitrates[sr_number] = self._available_bitrate
        self._available_bitrate = 0
      logging.debug("{} => service no. {} dedicated bit-rate: {}".format(self, sr_number, self._dedicated_bitrates[sr_number]))
    else:
      sr_bitrate = self._dedicated_bitrates[sr_number]
      del self._dedicated_bitrates[sr_number]
      self._available_bitrate += sr_bitrate
      logging.debug("{} => service no. {} dedicated bit-rate: {}".format(self, sr_number, sr_bitrate))
    logging.debug("{} => available bit-rate: {}".format(self, self._available_bitrate))

  def _update_success_list(self, service_type):
    """
    Updates user success report list.

    Arguments:
    service_type -- Type of the requested service
    """
    if self._available_bitrate >= DMEventHandler.BITRATES[service_type]:
      self._success_list += [1]
    else:
      self._success_list += [0]
    logging.debug("{} => latest user success report: {}".format(self, self._success_list[-1]))
    logging.debug("{} => user success report list: {}".format(self, self._success_list))

  def service_request(self, sr_number, service_type):
    """
    Updates params as if network operator has serviced buyer's service request.
    
    Arguments:
    sr_number -- Auction (SR) number
    service_type -- Type of the requested service
    """ 
    logging.debug("{} => service type: {}".format(self, service_type))
    # Store user success report
    self._update_success_list(service_type)
    # Update available bitrate
    self._update_available_bitrate(sr_number, service_type=service_type)
    # Compute reputation rating update
    self._reputation = self._reputation_update_method(self._reputation, self._success_list)
    logging.debug("{} => reputation: {}".format(self, self._reputation))
  
  def finish_servicing_request(self, sr_number):
    """
    Updates params when finished servicing buyer's service request.
    
    Arguments:
    sr_number -- Auction (SR) number
    """
    # Update available bitrate
    self._update_available_bitrate(sr_number)
  

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
 
  def __init__(self, simulation_engine):
    """
    Constructs DMEventHandler instance

    Arguments:
    simulation_engine -- SimulationEngine instance
    """
    super().__init__(simulation_engine)
    ### Simulation building blocks and params
    # Initialize list of bidders
    self.bidders = []
    # Initialize service requests mean interarrival rate
    self.interarrival_rate = 0
    # Initialize service requests duration
    self.duration = 0
    # Initialize save directory
    self.save_dir = ""
    # Initialize simulation id
    self.sim_id = -1
    # Initialize service request counter
    self._sr_count = 0
    # Initialize prices history dictionary
    self._prices = {service_type: {} for service_type in DMEventHandler.BITRATES.keys()}
    # Initialize price weight space (discretized interval [0,1])
    self._w_space = np.linspace(0.01, 1, 100)
 
  def handle_start(self):
    """
    Overriden
    """
    self._schedule_sr_event(self._simulation_engine.simulation_time)
 
  def handle_stop(self):
    """
    Overriden
    """
    # Save results of the simulation
    self._save_results()
 
  def handle_event(self, event):
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

  def _generate_sr_event(self, base_time):
    """
    Returns next service request (SR) event.

    Arguments:
    base_time -- Base time for the next event to occur
    """
    prng = self._simulation_engine.prng
    # Generate buyer (service type & price weight pair)
    price_weight = float(prng.choice(self._w_space, 1)[0])
    service_type = prng.choice(list(DMEventHandler.BITRATES.keys()), 1)[0]
    # Calculate interarrival time
    delta_time = prng.exponential(1 / self.interarrival_rate)
    # Generate next service request event
    return sim.Event(DMEventHandler.SR_EVENT, base_time + delta_time, bundle=(price_weight, service_type))

  def _schedule_sr_event(self, base_time):
    """
    Schedules next service request event.

    Arguments:
    base_time -- Base time for the next event to occur
    """
    event = self._generate_sr_event(base_time)
    # Schedule the event
    self._simulation_engine.schedule(event)

  def _generate_st_event(self, base_time, bundle):
    """
    Returns next service termination (ST) event.

    Arguments:
    base_time -- Base time for the next event to occur
    bundle -- Passed in Event bundle
    """
    return sim.Event(DMEventHandler.ST_EVENT, base_time + self.duration, bundle=bundle)

  def _schedule_st_event(self, base_time, bundle):
    """
    Schedules next service request termination event.

    Arguments:
    base_time -- Base time for the next event to occur
    bundle -- Passed in Event bundle
    """
    event = self._generate_st_event(base_time, bundle) 
    # Schedule the event
    self._simulation_engine.schedule(event)
 
  def _run_auction(self, event):
    """
    Runs DM auction.

    Arguments:
    event -- Event which triggered the auction
    """
    # Increment service request counter
    self._sr_count += 1
    # Get requested price weight and service type
    price_weight, service_type = event.kwargs.get('bundle', None)
    # Select the winner
    winner = self._select_winner(service_type, price_weight)
    loser = functools.reduce(lambda acc, x: acc + [x] if x is not winner else acc, self.bidders, [])
    # Collect statistics & update system state
    win_bid = winner.submit_bid(service_type, price_weight, loser[0].reputation)
    self._prices[service_type].setdefault(price_weight, []).append(win_bid)
    for b in self.bidders:
      b.update_winning_history(True if b == winner else False)
    winner.service_request(self._sr_count, service_type)
    # Schedule termination event
    self._schedule_st_event(event.time, (winner, self._sr_count))

  def _select_winner(self, service_type, price_weight):
    """
    Returns winner of an auction characterized by parameters
    service_type and price_weight.

    Arguments:
    service_type -- Type of the requested service
    price_weight -- Requested price weight
    """
    # Get bids from bidders
    bids = [self.bidders[0].submit_bid(service_type, price_weight, self.bidders[1].reputation)]
    bids += [self.bidders[1].submit_bid(service_type, price_weight, self.bidders[0].reputation)]
    # Select the winner
    compound_bids = [price_weight*bids[i] + (1-price_weight)*self.bidders[i].reputation for i in range(2)]
    if compound_bids[0] < compound_bids[1]:
      # Bidder 1 wins
      winner = 0
      return self.bidders[0]
    elif compound_bids[0] > compound_bids[1]:
      # Bidder 2 wins
      return self.bidders[1]
    else:
      # Tie
      return self.bidders[self._simulation_engine.prng.randint(2)]

  def _save_results(self):
    """
    Saves results of the simulation.
    """
    # Create output directory if doesn't exist already
    path = self.save_dir + '/' + str(self.sim_id)
    if not os.path.exists(path):
      os.makedirs(path)
    # Write output data to files
    for b in self.bidders:
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
    # 3. Prices per service type and price weight
    logging.debug("Price dict: {}".format(self._prices))
    path += '/prices'
    if not os.path.exists(path):
      os.makedirs(path)
    for st_dct in self._prices:
      for w in self._prices[st_dct]:
        with open(path + '/price_{}_{}.out'.format(st_dct, w), mode='w', newline='', encoding='utf-8') as f:
          writer = csv.writer(f, delimiter=',')
          writer.writerow(['sr_number', 'price'])
          for tup in zip(range(1, len(self._prices[st_dct][w]) + 1), self._prices[st_dct][w]):
            writer.writerow(tup)

