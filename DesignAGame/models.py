"""This file contains the models and ProtoRPC messages used by the API"""
from protorpc import messages
from google.appengine.ext import ndb

import random


class User(ndb.Model):
    """
    Object for implementing a single user.
    Authentication is not yet implemented
    """
    username = ndb.StringProperty(required=True)
    email = ndb.StringProperty()


class Game(ndb.Model):
    """Game object"""
    pairs = ndb.IntegerProperty(repeated=True, indexed=False)
    uncovered_pairs = ndb.IntegerProperty(repeated=True, indexed=False)
    # the index of number first shown in a pair of numbers to check matches
    number_shown = ndb.IntegerProperty(indexed=False)
    attempts = ndb.IntegerProperty(required=True, default=0)
    game_over = ndb.BooleanProperty(required=True, default=False)
    start_time = ndb.DateTimeProperty(required=True)
    click_history = ndb.IntegerProperty(repeated=True)
    end_time = ndb.DateTimeProperty()
    user = ndb.KeyProperty(required=True, kind='User')

    @classmethod
    def new_game(cls, user, num_pairs):
        """Creates a new game"""
        # Ensure the number of pairs are within limits
        if num_pairs < 2:
            raise ValueError('Game must have >= 2 pairs of values')
        if num_pairs > 64:
            raise ValueError('Game must have <= 64 pairs of values')

        # Make a shuffled list of pairs for the game
        pairs = range(num_pairs) + range(num_pairs)
        random.shuffle(pairs)
        game = Game(user=user, pairs=pairs, attempts=0, game_over=False)
        game.put()
        return game


class StringMessage(messages.Message):
    """
    A ProtoRPC message class containing a string
    Use to pass simple text responses
    """
    message = messages.StringField(1, required=True)
