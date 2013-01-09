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
# Toolbox class
unittest.TextTestRunner(verbosity=2).run( \
    unittest.TestLoader().loadTestsFromTestCase(dm.ToolboxTests))
# 1. Bidder class
unittest.TextTestRunner(verbosity=2).run( \
    unittest.TestLoader().loadTestsFromTestCase(dm.BidderTests))
# 2. DMEventHandler class
unittest.TextTestRunner(verbosity=2).run( \
    unittest.TestLoader().loadTestsFromTestCase(dm.DMEventHandlerTests))
# 3. SimulatorEngine class
unittest.TextTestRunner(verbosity=2).run( \
    unittest.TestLoader().loadTestsFromTestCase(sim.SimulationEngineTests))
# 4. Event class
unittest.TextTestRunner(verbosity=2).run( \
    unittest.TestLoader().loadTestsFromTestCase(sim.EventTests))

