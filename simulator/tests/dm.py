#!/usr/bin/env python
# encoding: utf-8

import numpy as np
from simulator.models.dm import *
from simulator.models.sim import SimulationEngine, Event

class BidderTests(unittest.TestCase):
  def setUp(self):
    self.bidder = Bidder(1000)

  def test_init(self):
    self.assertEqual(self.bidder.costs, {})
    self.assertEqual(self.bidder.reputation, 0.5)
    self.assertEqual(self.bidder._total_bitrate, 1000)

  def test_init_with_optionals(self):
    bidder = Bidder(100, costs={DMEventHandler.WEB_BROWSING: 0.5, DMEventHandler.EMAIL: 0.25}, reputation=0.75)
    self.assertEqual(bidder.costs, {DMEventHandler.WEB_BROWSING: 0.5, DMEventHandler.EMAIL: 0.25})
    self.assertEqual(bidder.reputation, 0.75)
    self.assertEqual(bidder._total_bitrate, 100)

  def test_reputation_update(self):
    Bidder.reputation_window_size = 5 
    self.bidder._success_list = [1,0,1,0,1]
    self.bidder._update_reputation()
    self.assertEqual(self.bidder.reputation, 0.4)
    self.assertEqual(self.bidder._success_list, [0,1,0,1])

  def test_available_bitrate_update(self):
    sr_numbers = list(range(2))
    available_bitrates = [488, 0, 512, 1000]
    # Test bitrate usage
    for sr_number in sr_numbers:
      self.bidder._update_available_bitrate(sr_number, DMEventHandler.WEB_BROWSING)
      self.assertEqual(self.bidder.available_bitrate, available_bitrates[sr_number])
    # Test bitrate reclaim
    for sr_number in sr_numbers:
      self.bidder._update_available_bitrate(sr_number)
      self.assertEqual(self.bidder.available_bitrate, available_bitrates[sr_number + 2])

  def test_success_list_update(self):
    sr_bitrate = DMEventHandler.WEB_BROWSING
    self.bidder._update_success_list(sr_bitrate)
    self.bidder._update_available_bitrate(0, sr_bitrate)
    self.bidder._update_success_list(sr_bitrate)
    self.assertEqual(self.bidder.success_list, [1, 0])

  def test_submit_bid(self):
    service_type = DMEventHandler.WEB_BROWSING
    # 1. Price weight 0.0
    bidder = Bidder(1000)
    bid = bidder.submit_bid(service_type, 0.0, 0.25)
    self.assertEqual(bid, "Inf")
    # 2. Price weight 1.0
    bidder = Bidder(1000, costs={service_type: 0.5})
    bid = bidder.submit_bid(service_type, 1.0, 1.0)
    self.assertEqual(bid, (1+0.5)/2)
    # 3. Equal reputation ratings
    bidder = Bidder(1000, costs={service_type: 0.5}, reputation=0.5)
    bid = bidder.submit_bid(service_type, 0.5, 0.5)
    self.assertEqual(bid, (1+0.5)/2)
    # 4. Remaining cases
    bidder = Bidder(1000, costs={service_type: 0.5}, reputation=0.5)
    bid = bidder.submit_bid(service_type, 0.5, 0.75)
    def th_cost(bid):
      if bid == 13/16:
        return 0.75
      else:
        return 0.75 + 1 / ((13*8 - 128*bid) * (-(81*2)/63) * np.exp(-16/63 + 1/(13-16*bid)) + 4*(7*8 - 64*bid))
    th_bids = np.linspace(145/(32*8), 13/16, 1000)
    diff = list(map(lambda x: np.abs(x-0.5), map(th_cost, th_bids)))
    th_bid = th_bids[diff.index(min(diff))]
    self.assertEqual(bid, (th_bid - 0.5*0.5)/0.5)


class DMEventHandlerTests(unittest.TestCase):
  def setUp(self):
    self.se = SimulationEngine()
    self.seed = 0
    self.se.prng = np.random.RandomState(self.seed)
    self.dmeh = DMEventHandler(self.se)
    self.dmeh.interarrival_rate = 0.5
    self.dmeh.duration = 2.5

  def test_init(self):
    self.assertEqual(self.dmeh.interarrival_rate, 0.5)
    self.assertEqual(self.dmeh.duration, 2.5)

  def test_generate_sr_event(self):
    event = self.dmeh._generate_sr_event(1.5)
    prng = np.random.RandomState(self.seed)
    bundle = (float(prng.choice(self.dmeh._w_space, 1)[0]),
              prng.choice(list(DMEventHandler.BITRATES.keys()), 1)[0])
    self.assertEqual(event.identifier, DMEventHandler.SR_EVENT)
    self.assertEqual(event.time, 1.5 + prng.exponential(1/self.dmeh.interarrival_rate))
    self.assertEqual(event.kwargs.get('bundle', None), bundle)

  def test_generate_st_event(self):
    event = self.dmeh._generate_st_event(1.5, None)
    self.assertEqual(event.identifier, DMEventHandler.ST_EVENT)
    self.assertEqual(event.time, 1.5 + self.dmeh.duration)
    self.assertEqual(event.kwargs.get('bundle', None), None)

if __name__ == '__main__':
  unittest.main()

