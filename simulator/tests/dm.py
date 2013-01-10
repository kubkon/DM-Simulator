#!/usr/bin/env python
# encoding: utf-8
"""
dm.py

Created by Jakub Konka on 2013-01-07.
Copyright (c) 2013 University of Strathclyde. All rights reserved.
"""
import functools
import numpy as np
import simulator.errors as errors
from simulator.modules.dm import BidderHelper, Bidder, DMEventHandler
from simulator.modules.sim import SimulationEngine, Event
import unittest


class BidderHelperTests(unittest.TestCase):
  def setUp(self):
    self.helper = BidderHelper()
    self.window_size = 5
    self.commitment = 0.8
    self.reputation = 0.5
    self.long_success_list = [1,0,1,0,1,0,1]
    self.short_success_list = [1,0,1,0]
    self.cost = 0.5

  def test_method_returns_myopic_method(self):
    method = self.helper.method({'method': 'myopic'})
    self.assertEqual(method.func, self.helper.myopic_bidding)
    self.assertEqual(method.args, ())
  
  def test_method_returns_lebodics_method(self):
    method = self.helper.method({'method':'lebodic', 'window_size':self.window_size})
    self.assertEqual(method.func, self.helper.lebodics_reputation_update)
    self.assertEqual(method.args, (self.window_size,))
  
  def test_method_returns_mcdiarmids_method(self):
    method = self.helper.method({'method':'mcdiarmid', 'commitment':self.commitment})
    self.assertEqual(method.func, self.helper.mcdiarmids_reputation_update)
    self.assertEqual(method.args, (self.commitment,))
  
  def test_method_raises_unknown_method_error(self):
    with self.assertRaises(errors.UnknownMethodError):
      self.helper.method({'method': 'unknown'})
    with self.assertRaises(errors.UnknownMethodError):
      self.helper.method({'something': None})
    with self.assertRaises(errors.UnknownMethodError):
      self.helper.method({'method': 'lebodic'})

  def test_myopic_bidding_for_price_weight_0(self):
    bid = self.helper.myopic_bidding(0.0, 0.5, 0.25, 0.5)
    self.assertEqual(bid, float('inf'))
  
  def test_myopic_bidding_for_price_weight_1(self):
    bid = self.helper.myopic_bidding(1.0, self.cost, 0.25, 0.5)
    self.assertEqual(bid, (1 + self.cost)/2)

  def test_myopic_bidding_for_equal_reputations(self):
    bid = self.helper.myopic_bidding(0.5, self.cost, self.reputation, self.reputation)
    self.assertEqual(bid, (1 + self.cost)/2)
  
  def test_myopic_bidding_for_remaining_cases(self):
    price_weight = 0.5
    bid = self.helper.myopic_bidding(price_weight, self.cost, self.reputation, 0.75)
    def th_cost(bid):
      if bid == 13/16:
        return 0.75
      else:
        return 0.75 + 1 / ((13*8 - 128*bid) * (-(81*2)/63) * np.exp(-16/63 + 1/(13-16*bid)) + 4*(7*8 - 64*bid))
    th_bids = np.linspace(145/(32*8), 13/16, 1000)
    diff = list(map(lambda x: np.abs(x-0.5), map(th_cost, th_bids)))
    th_bid = th_bids[diff.index(min(diff))]
    self.assertEqual(bid, (th_bid - price_weight * self.cost)/price_weight)

  def test_lebodics_reputation_update(self):
    reputation = self.helper.lebodics_reputation_update(self.window_size,
        self.reputation,
        self.long_success_list)
    self.assertEqual(reputation, 0.4)
    reputation = self.helper.lebodics_reputation_update(self.window_size,
        self.reputation,
        self.short_success_list)
    self.assertEqual(reputation, self.reputation)

  def test_mcdiarmids_reputation_update(self):
    reputation = self.helper.mcdiarmids_reputation_update(self.commitment,
        self.reputation,
        self.long_success_list)
    self.assertEqual(reputation, self.reputation - 0.01)
    reputation = self.helper.mcdiarmids_reputation_update(self.commitment,
        self.reputation,
        self.short_success_list)
    self.assertEqual(reputation, self.reputation + self.commitment / 100 / (1-self.commitment))


class BidderTests(unittest.TestCase):
  def setUp(self):
    self.total_bitrate = 1000
    self.costs = {DMEventHandler.WEB_BROWSING: 0.5}
    self.reputation = 0.5
    # Bidder instance intialized with lebodic's reputation update
    self.lebodic_params = {'method':'lebodic', 'window_size':5}
    self.bidder1 = Bidder(total_bitrate=self.total_bitrate,
      costs=self.costs,
      bidding_params={'method':'myopic'},
      reputation=self.reputation,
      reputation_params=self.lebodic_params)
    # Bidder instace initialized with mcdiarmid's reputation update
    self.mcdiarmid_params = {'method':'mcdiarmid', 'commitment':0.8}
    self.bidder2 = Bidder(total_bitrate=self.total_bitrate,
    costs=self.costs,
    bidding_params={'method':'myopic'},
    reputation=self.reputation,
    reputation_params=self.mcdiarmid_params)

  def test_init_raises_uninitialized_argument_error(self):
    with self.assertRaises(errors.UninitializedArgumentError):
      Bidder()

  def test_init_properties(self):
    self.assertEqual(self.bidder1.costs, self.costs)
    self.assertEqual(self.bidder1.reputation, self.reputation)
    self.assertEqual(self.bidder1.total_bitrate, self.total_bitrate)

  def test_init_lebodics_reputation_update_method(self):
    self.assertEqual(self.bidder1._reputation_update_method.func, self.bidder1._bidder_helper.lebodics_reputation_update)
    self.assertEqual(self.bidder1._reputation_update_method.args, (self.lebodic_params['window_size'],))
 
  def test_init_alisdairs_reputation_update_method(self):
    self.assertEqual(self.bidder2._reputation_update_method.func, self.bidder2._bidder_helper.mcdiarmids_reputation_update)
    self.assertEqual(self.bidder2._reputation_update_method.args, (self.mcdiarmid_params['commitment'],))

  def test_init_myopic_bidding_method(self):
    self.assertEqual(self.bidder1._bidding_method.func, self.bidder1._bidder_helper.myopic_bidding)
    self.assertEqual(self.bidder1._bidding_method.args, ())

  def test_available_bitrate_update(self):
    usage_sr_numbers = [1, 2]
    usage_bitrates = [488, 0]
    reclaim_sr_numbers = [2, 1]
    reclaim_bitrates = [488, self.total_bitrate]
    # Test bitrate usage
    for i in range(2):
      self.bidder1._update_available_bitrate(usage_sr_numbers[i], DMEventHandler.WEB_BROWSING)
      self.assertEqual(self.bidder1.available_bitrate, usage_bitrates[i])
    # Test bitrate reclaim
    for i in range(2):
      self.bidder1._update_available_bitrate(reclaim_sr_numbers[i])
      self.assertEqual(self.bidder1.available_bitrate, reclaim_bitrates[i])

  def test_success_list_update(self):
    service_type = DMEventHandler.WEB_BROWSING
    self.bidder1._update_success_list(service_type)
    self.bidder1._update_available_bitrate(0, service_type)
    self.bidder1._update_success_list(service_type)
    self.assertEqual(self.bidder1.success_list, [1, 0])


class DMEventHandlerTests(unittest.TestCase):
  def setUp(self):
    self.se = SimulationEngine()
    self.se.prng = np.random.RandomState(0)
    self.dmeh = DMEventHandler(self.se)
    self.dmeh.interarrival_rate = 0.5
    self.dmeh.duration = 2.5

  def test_init(self):
    self.assertEqual(self.dmeh.interarrival_rate, 0.5)
    self.assertEqual(self.dmeh.duration, 2.5)

  def test_generate_sr_event(self):
    event_time = 1.5
    event = self.dmeh._generate_sr_event(event_time)
    prng = np.random.RandomState(0)
    bundle = (float(prng.choice(self.dmeh._w_space, 1)[0]),
              prng.choice(list(DMEventHandler.BITRATES.keys()), 1)[0])
    self.assertEqual(event.identifier, DMEventHandler.SR_EVENT)
    self.assertGreater(event.time, event_time)
    self.assertIsInstance(event.kwargs.get('bundle', None), tuple)
    self.assertIn(event.kwargs.get('bundle', None)[0], self.dmeh._w_space)
    self.assertIn(event.kwargs.get('bundle', None)[1], DMEventHandler.BITRATES.keys())

  def test_generate_st_event(self):
    event_time = 1.5
    event = self.dmeh._generate_st_event(event_time, None)
    self.assertEqual(event.identifier, DMEventHandler.ST_EVENT)
    self.assertGreater(event.time, event_time)
    self.assertEqual(event.kwargs.get('bundle', None), None)

  def test_select_winner(self):
    bidders = [
        Bidder(10000, costs={DMEventHandler.WEB_BROWSING: 0.75},
          bidding_params={'method':'myopic'}, reputation=0.25,
          reputation_params={'method':'lebodic', 'window_size':5}),
        Bidder(10000, costs={DMEventHandler.WEB_BROWSING: 0.25},
          bidding_params={'method':'myopic'}, reputation=0.75,
          reputation_params={'method':'lebodic', 'window_size':5})]
    self.dmeh.bidders = bidders
    self.assertEqual(self.dmeh._select_winner(DMEventHandler.WEB_BROWSING, 0.5),
                     bidders[1])
    self.assertEqual(self.dmeh._select_winner(DMEventHandler.WEB_BROWSING, 0.25),
                     bidders[0])
    self.assertEqual(self.dmeh._select_winner(DMEventHandler.WEB_BROWSING, 0.75),
                     bidders[1])


if __name__ == '__main__':
  unittest.main()

