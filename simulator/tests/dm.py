#!/usr/bin/env python
# encoding: utf-8

import numpy as np
import functools
from simulator.modules.dm import *
from simulator.modules.sim import SimulationEngine, Event


class ToolboxTests(unittest.TestCase):
  def setUp(self):
    self.window_size = 5
    self.commitment = 0.8
    self.reputation = 0.5
    self.long_success_list = [1,0,1,0,1,0,1]
    self.short_success_list = [1,0,1,0]

  def test_reputation_update_method(self):
    method = Toolbox.reputation_update_method({'window_size':self.window_size})
    self.assertIs(type(method), functools.partial)
    method = Toolbox.reputation_update_method({'commitment':self.commitment})
    self.assertIs(type(method), functools.partial)
    with self.assertRaisesRegexp(Exception, 'cannot infer reputation update method'):
      method = Toolbox.reputation_update_method({'param':10})

  def test_lebodics_reputation_update(self):
    reputation = Toolbox.lebodics_reputation_update(self.window_size,
        self.reputation,
        self.long_success_list)
    self.assertEqual(reputation, 0.4)
    reputation = Toolbox.lebodics_reputation_update(self.window_size,
        self.reputation,
        self.short_success_list)
    self.assertEqual(reputation, self.reputation)

  def test_alisdairs_reputation_update(self):
    reputation = Toolbox.alisdairs_reputation_update(self.commitment,
        self.reputation,
        self.long_success_list)
    self.assertEqual(reputation, self.reputation - 0.01)
    reputation = Toolbox.alisdairs_reputation_update(self.commitment,
        self.reputation,
        self.short_success_list)
    self.assertEqual(reputation, self.reputation + self.commitment / 100 / (1-self.commitment))


class BidderTests(unittest.TestCase):
  def setUp(self):
    self.total_bitrate = 1000
    self.costs = {DMEventHandler.WEB_BROWSING: 0.5}
    self.reputation = 0.5
    self.lebodic_params = {'window_size':5}
    self.alisdair_params = {'commitment':0.8}
    self.bidders = [
        # Bidder instance intialized with lebodic's reputation update
        Bidder(total_bitrate=self.total_bitrate,
        costs=self.costs,
        reputation=self.reputation,
        reputation_params=self.lebodic_params),
        # Bidder instace initialized with alisdair's reputation update
        Bidder(total_bitrate=self.total_bitrate,
        costs=self.costs,
        reputation=self.reputation,
        reputation_params=self.alisdair_params)]

  def test_init_raises_uninitialized_exception(self):
    with self.assertRaisesRegexp(Exception, "one of the arguments uninitialized!"):
      Bidder()

  def test_init_with_lebodic(self):
    for bidder in self.bidders:
      self.assertEqual(bidder.costs, self.costs)
      self.assertEqual(bidder.reputation, self.reputation)
      self.assertEqual(bidder._total_bitrate, self.total_bitrate)

  def test_reputation_update(self):
    for bidder in self.bidders:
      bidder._success_list = [1,0,1,0,1]
      bidder._update_reputation()
    self.assertEqual(self.bidders[0].reputation, 0.4)
    self.assertEqual(self.bidders[1].reputation, self.reputation - 0.01)

  def test_available_bitrate_update(self):
    for bidder in self.bidders:
      sr_numbers = list(range(2))
      available_bitrates = [488, 0, 512, 1000]
      # Test bitrate usage
      for sr_number in sr_numbers:
        bidder._update_available_bitrate(sr_number, DMEventHandler.WEB_BROWSING)
        self.assertEqual(bidder.available_bitrate, available_bitrates[sr_number])
      # Test bitrate reclaim
      for sr_number in sr_numbers:
        bidder._update_available_bitrate(sr_number)
        self.assertEqual(bidder.available_bitrate, available_bitrates[sr_number + 2])

  def test_success_list_update(self):
    for bidder in self.bidders:
      service_type = DMEventHandler.WEB_BROWSING
      bidder._update_success_list(service_type)
      bidder._update_available_bitrate(0, service_type)
      bidder._update_success_list(service_type)
      self.assertEqual(bidder.success_list, [1, 0])

  def test_submit_bid_for_price_weight_0(self):
    for bidder in self.bidders:
      service_type = DMEventHandler.WEB_BROWSING
      bid = bidder.submit_bid(service_type, 0.0, 0.25)
      self.assertEqual(bid, "Inf")
  
  def test_submit_bid_for_price_weight_1(self):
    for bidder in self.bidders:
      service_type = DMEventHandler.WEB_BROWSING
      bid = bidder.submit_bid(service_type, 1.0, 1.0)
      self.assertEqual(bid, (1 + self.costs[service_type])/2)

  def test_submit_bid_for_equal_reputations(self):
    for bidder in self.bidders:
      service_type = DMEventHandler.WEB_BROWSING
      bid = bidder.submit_bid(service_type, 0.5, bidder.reputation)
      self.assertEqual(bid, (1 + self.costs[service_type])/2)
  
  def test_submit_bid_for_remaining_cases(self):
    for bidder in self.bidders:
      service_type = DMEventHandler.WEB_BROWSING
      price_weight = 0.5
      bid = bidder.submit_bid(service_type, price_weight, 0.75)
      def th_cost(bid):
        if bid == 13/16:
          return 0.75
        else:
          return 0.75 + 1 / ((13*8 - 128*bid) * (-(81*2)/63) * np.exp(-16/63 + 1/(13-16*bid)) + 4*(7*8 - 64*bid))
      th_bids = np.linspace(145/(32*8), 13/16, 1000)
      diff = list(map(lambda x: np.abs(x-0.5), map(th_cost, th_bids)))
      th_bid = th_bids[diff.index(min(diff))]
      self.assertEqual(bid, (th_bid - price_weight * self.costs[service_type])/price_weight)


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
          reputation=0.25, reputation_params={'window_size':5}),
        Bidder(10000, costs={DMEventHandler.WEB_BROWSING: 0.25},
          reputation=0.75, reputation_params={'window_size':5})]
    self.dmeh.bidders = bidders
    self.assertEqual(self.dmeh._select_winner(DMEventHandler.WEB_BROWSING, 0.5),
                     bidders[1])
    self.assertEqual(self.dmeh._select_winner(DMEventHandler.WEB_BROWSING, 0.25),
                     bidders[0])
    self.assertEqual(self.dmeh._select_winner(DMEventHandler.WEB_BROWSING, 0.75),
                     bidders[1])


if __name__ == '__main__':
  unittest.main()

