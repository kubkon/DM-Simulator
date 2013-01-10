#!/usr/bin/env python
# encoding: utf-8
"""
test.py

Created by Jakub Konka on 2013-01-07.
Copyright (c) 2012 University of Strathclyde. All rights reserved.
"""
import unittest
import simulator.tests.dm as dm
import simulator.tests.sim as sim

# Run tests
# 1. BidderHelper class
unittest.TextTestRunner(verbosity=2).run(
    unittest.TestLoader().loadTestsFromTestCase(dm.BidderHelperTests))
# 2. Bidder class
unittest.TextTestRunner(verbosity=2).run(
    unittest.TestLoader().loadTestsFromTestCase(dm.BidderTests))
# 3. DMEventHandler class
unittest.TextTestRunner(verbosity=2).run(
    unittest.TestLoader().loadTestsFromTestCase(dm.DMEventHandlerTests))
# 4. SimulatorEngine class
unittest.TextTestRunner(verbosity=2).run(
    unittest.TestLoader().loadTestsFromTestCase(sim.SimulationEngineTests))
# 5. Event class
unittest.TextTestRunner(verbosity=2).run(
    unittest.TestLoader().loadTestsFromTestCase(sim.EventTests))

