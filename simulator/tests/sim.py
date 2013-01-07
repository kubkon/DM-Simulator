#!/usr/bin/env python
# encoding: utf-8

from simulator.models.sim import *

class SimulationEngineTests(unittest.TestCase):
  def setUp(self):
    self.sim = SimulationEngine()
  
  def test_singleton_behaviour(self):
    sim = SimulationEngine()
    self.assertEqual(self.sim, sim)
  
  def test_notify_start(self):
    def f(): print("Callback received")
    self.sim.register_callback(f, SimulationEngine.START_CALLBACK)
    self.sim.stop(1)
    self.sim.start()
  
  def test_notify_stop(self):
    def f(): print("Callback received")
    self.sim.register_callback(f, SimulationEngine.STOP_CALLBACK)
    self.sim.stop(1)
    self.sim.start()
  
  def test_notify_event(self):
    def f(e): print("Callback received. Event: {}@{}".format(e.identifier, e.time))
    self.sim.register_callback(f, SimulationEngine.EVENT_CALLBACK)
    self.sim.stop(2)
    self.sim.schedule(Event("Dummy", 1))
    self.sim.start()
  

class EventTests(unittest.TestCase):
  def setUp(self):
    self.e1 = Event("Arrival", 10)
    self.e2 = Event("Arrival", 10, special="Special")
  
  def test_properties(self):
    self.assertEqual(self.e1.identifier, "Arrival")
    self.assertEqual(self.e1.time, 10)
    self.assertEqual(self.e2.identifier, "Arrival")
    self.assertEqual(self.e2.time, 10)
    self.assertEqual(self.e2.kwargs.get('special', None), "Special")
  

if __name__ == '__main__':
  unittest.main()

