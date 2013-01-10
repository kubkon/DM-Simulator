#!/usr/bin/env python
# encoding: utf-8
"""
errors.py

Created by Jakub Konka on 2013-01-09.
Copyright (c) 2013 University of Strathclyde. All rights reserved.
"""

class Error(Exception):
  """
  Base class for exceptions in this package.
  """
  pass


class UnknownMethodError(Error):
  """
  Exception raised for errors in inferring a method
  by an instance of BidderHelper class from the specified
  params.

  Attributes:
  params -- Params for which the error occurred
  """
  def __init__(self, params):
    super().__init__(
        "Cannot infer the method from params: {}".format(params)
        )
    self.params = params


class UninitializedArgumentError(Error):
  """
  Exception raised for uninitialized keyword arguments
  in a method.
  """
  def __init__(self):
    super().__init__("Uninitialized argument found")

