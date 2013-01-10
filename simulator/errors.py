#!/usr/bin/env python
# encoding: utf-8


class Error(Exception):
  """
  Base class for exceptions in this package.
  """
  pass


class BiddingMethodError(Error):
  """
  Exception raised for errors in inferring the bidding
  method from the specified params.

  Attributes:
  params -- Params for which the error occurred
  """
  def __init__(self, params):
    super().__init__("Cannot infer bidding method from params: {}".format(params))
    self.params = params


class ReputationUpdateMethodError(Error):
  """
  Exception raised for errors in inferring the reputation
  rating update method from the specified params.

  Attributes:
  params -- Params for which the error occurred
  """
  def __init__(self, params):
    super().__init__("Cannot infer reputation update method from params: {}".format(params))
    self.params = params


class UninitializedArgumentError(Error):
  """
  Exception raised for uninitialized keyword arguments
  in a method.
  """
  def __init__(self):
    super().__init__("Uninitialized argument found")


