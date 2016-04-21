"""This file contains the models and ProtoRPC messages used by the API"""
from protorpc import messages
from google.appengine.ext import ndb

import random
from datetime import datetime


class User(ndb.Model):
    """
    Object for implementing a single user.
    Authentication is not yet implemented
    """
    username = ndb.StringProperty(required=True)
    email = ndb.StringProperty()
    # Average of user's scores. Updated via task queue
    performance = ndb.FloatProperty(default=0.0)


class Game(ndb.Model):
    """Game object"""
    cards = ndb.IntegerProperty(repeated=True, indexed=False)
    uncovered_pairs = ndb.IntegerProperty(repeated=True, indexed=False)
    # the index of number first shown in a pair of numbers to check matches
    previous_choice = ndb.IntegerProperty(indexed=False, default=-1)
    attempts = ndb.IntegerProperty(default=0)
    game_over = ndb.BooleanProperty(default=False)
    start_time = ndb.DateTimeProperty(required=True)
    end_time = ndb.DateTimeProperty()
    history = ndb.IntegerProperty(repeated=True, indexed=False)
    end_time = ndb.DateTimeProperty()
    user = ndb.KeyProperty(required=True, kind='User')

    # Computed properties
    moves = ndb.ComputedProperty(lambda self: len(self.history) / 2)
    num_pairs = ndb.ComputedProperty(lambda self: len(self.cards) / 2)
    num_uncovered_pairs \
            = ndb.ComputedProperty(lambda self: len(self.uncovered_pairs))
    # Set by make_move, this stores whether the current card is the first card
    # in a move, which contains two cards
    is_first_card = ndb.BooleanProperty(default=True)

    # Only stored temporarily to track current move
    current_choice = None

    @classmethod
    def new_game(cls, user, num_pairs):
        """Creates a new game"""
        # Ensure the number of pairs are within limits
        if num_pairs < 2:
            raise ValueError('Game must have >= 2 pairs of values')
        if num_pairs > 64:
            raise ValueError('Game must have <= 64 pairs of values')

        # Make a shuffled list of pairs for the game
        cards = range(num_pairs) * 2
        random.shuffle(cards)
        game = Game(user=user, cards=cards, start_time=datetime.now())

        return game

    def _uncovered_pairs_to_uncovered_list(self):
        """
        For use in GameForm.
        Generates a list where cards that have been uncovered are shown as
        their value and cards that have not been uncovered are shown as -1
        """
        uncovered = [-1] * len(self.cards)

        for index, card in enumerate(self.cards):
            if card in self.uncovered_pairs:
                uncovered[index] = card

        return uncovered

    def _get_matching_card_mapping(self):
        """
        Returns a list where the value of one card is the index of the other
        card with the same value
        """
        value_mapping = [[] for i in xrange(self.num_pairs)]
        for index, value in enumerate(self.cards):
            value_mapping[value].append(index)

        matching_card_mapping = [None] * len(self.cards)

        for pair in value_mapping:
            matching_card_mapping[pair[0]] = pair[1]
            matching_card_mapping[pair[1]] = pair[0]

        return matching_card_mapping

    def _get_paired_history(self):
        history = self.history
        paired_history = []
        for i in xrange(0, len(history), 2):
            history_pair = (history[i], history[i + 1])
            paired_history.append(history_pair)

        return paired_history

    def _calculate_score(self):
        """
        Uses history to generate a score
        Each successful match is worth 20 points
        If you fail to match a matching tile which was previously shown,
        the score is subtracted by 5 times the number of times the tile has
        been shown.
        At the end, if there has not been any failed matches, a bonus score of
        5 times the number of pairs in the level is added.
        Scoring system from this page: http://dkmgames.com/memory/pairs.php
        """
        if not self.game_over:
            raise ValueError('Cannot caluculate score as game is not over!')

        score = 0
        perfect_match = True
        cards = self.cards
        matching_card_mapping = self._get_matching_card_mapping()

        # The number of times a card has been shown, ordered by index.
        view_count = [0] * len(self.cards)

        paired_history = self._get_paired_history()

        for move in paired_history:
            # Check if match
            if cards[move[0]] == cards[move[1]]:
                score += 20
            else:
                # Get the index of the 'correct' match of the first card
                correct_match = matching_card_mapping[move[0]]

                # if the correct match has been previously seen by the player
                if view_count[correct_match] > 0:
                    score -= view_count[correct_match] * 5
                    perfect_match = False

                view_count[move[0]] += 1
                view_count[move[1]] += 1

        if perfect_match:
            score += self.num_pairs * 5

        # Make sure the score is not negative
        return max(score, 0)

    def get_history(self):
        paired_history = self._get_paired_history()
        moves = self.moves
        history_move_form_list = []
        cards = self.cards

        for move in paired_history:
            matched = cards[move[0]] == cards[move[1]]
            moveform = HistoryMoveForm(card_1=CardForm(index=move[0],
                                                       value=cards[move[0]]),
                                       card_2=CardForm(index=move[1],
                                                       value=cards[move[1]]),
                                       matched=matched)

            history_move_form_list.append(moveform)

        return HistoryForm(moves=history_move_form_list)

    def to_form(self, message=None):
        form = GameForm()
        form.urlsafe_key = self.key.urlsafe()
        form.username = self.user.get().username

        form.moves = self.moves
        form.num_pairs = self.num_pairs

        previous_choice = self.previous_choice
        current_choice = self.current_choice

        cards = self.cards

        # Only add the previous choice if this is the second card in a move
        if not self.is_first_card:
            form.previous_choice = CardForm(index=previous_choice,
                                            value=cards[previous_choice])
        if self.current_choice is not None:
            form.current_choice = CardForm(index=current_choice,
                                           value=cards[current_choice])

        form.shown_cards = self._uncovered_pairs_to_uncovered_list()
        form.game_over = self.game_over
        if message is not None:
            form.message = message
        return form

    def end_game(self):
        self.game_over = True
        self.end_time = datetime.now()
        score = self._calculate_score()

        self.put()

        score_entity = Score(user=self.user, datetime=self.end_time,
                             score=score, moves=self.moves)
        score_entity.put()


class Score(ndb.Model):
    """Score object"""
    user = ndb.KeyProperty(required=True, kind='User')
    # The time of finishing
    datetime = ndb.DateTimeProperty(required=True)
    moves = ndb.IntegerProperty(required=True)
    score = ndb.IntegerProperty(required=True)

    def to_form(self):
        return ScoreForm(username=self.user.get().username,
                         datetime=str(self.datetime), score=self.score,
                         moves=self.moves)


class CardForm(messages.Message):
    """Represents a single card in a move with index and value"""
    index = messages.IntegerField(1, required=True)
    value = messages.IntegerField(2, required=True)


class GameForm(messages.Message):
    """Game form for outbound data"""
    urlsafe_key = messages.StringField(1, required=True)
    username = messages.StringField(2, required=True)
    moves = messages.IntegerField(3, required=True)
    num_pairs = messages.IntegerField(4, required=True)
    # The index and value of the previously chosen card. This is not in the
    # list of shown cards to avoid confusion
    #
    # TODO: Update previous_choice and current_choice to CardForm
    previous_choice = messages.MessageField(CardForm, 5)
    # The index and value of the current choice
    current_choice = messages.MessageField(CardForm, 6)
    # Cards not shown are expressed as -1
    shown_cards = messages.IntegerField(7, repeated=True)
    game_over = messages.BooleanField(8, required=True)
    message = messages.StringField(9, default='')


class NewGameForm(messages.Message):
    """Create a new game"""
    username = messages.StringField(1, required=True)
    num_pairs = messages.IntegerField(2)


class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""
    card = messages.IntegerField(1, required=True)


class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""
    username = messages.StringField(1, required=True)
    datetime = messages.StringField(2, required=True)
    score = messages.IntegerField(3, required=True)
    moves = messages.IntegerField(4, required=True)


class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(ScoreForm, 1, repeated=True)


class GameForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(GameForm, 1, repeated=True)


class RankingForm(messages.Message):
    """Ranks a user based on their performance value"""
    username = messages.StringField(1, required=True)
    performance = messages.FloatField(2, required=True)


class RankingForms(messages.Message):
    """Return multiple RankingForms"""
    items = messages.MessageField(RankingForm, 1, repeated=True)


class HistoryMoveForm(messages.Message):
    """A single move for use in HistoryForm"""
    card_1 = messages.MessageField(CardForm, 1)
    card_2 = messages.MessageField(CardForm, 2)

    matched = messages.BooleanField(3, required=True)


class HistoryForm(messages.Message):
    """Holds a list of HistoryMove forms to show history step-by-step"""
    moves = messages.MessageField(HistoryMoveForm, 1, repeated=True)


class StringMessage(messages.Message):
    """
    A ProtoRPC message class containing a string
    Use to pass simple text responses
    """
    message = messages.StringField(1, required=True)
