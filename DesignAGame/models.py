"""This file contains the models and ProtoRPC messages used by the API"""
from protorpc import messages
from google.appengine.ext import ndb


class User(ndb.Model):
    """
    Object for implementing a single user.
    Authentication is not yet implemented
    """
    username = ndb.StringProperty(required=True)
    email = ndb.StringProperty()


class StringMessage(messages.Message):
    """
    A ProtoRPC message class containing a string
    Use to pass simple text responses
    """
    message = messages.StringField(1, required=True)
