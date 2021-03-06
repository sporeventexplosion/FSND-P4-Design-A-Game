import endpoints
import datetime
from protorpc import remote, messages
from google.appengine.api import taskqueue, memcache
from google.appengine.ext import ndb

from models import StringMessage, GameForm, NewGameForm, ScoreForms, \
        MakeMoveForm, GameForms, RankingForm, RankingForms, HistoryForm, \
        HistoryMoveForm
from models import User, Game, Score, Move

USER_REQUEST = endpoints.ResourceContainer(
        username=messages.StringField(1, required=True),
        email=messages.StringField(2))
NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
        urlsafe_game_key=messages.StringField(1))
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
        MakeMoveForm,
        urlsafe_game_key=messages.StringField(1))
HIGH_SCORE_REQUEST = endpoints.ResourceContainer(
        limit=messages.IntegerField(1))


MEMCACHE_AVERAGE_MOVES = 'AVERAGE_MOVES'


@endpoints.api(name='games', version='v1')
class ConcentrationGameApi(remote.Service):
    """Defines an Endpoints API for a Concentration game"""
    def _get_user(self, username):
        """Gets a user by username"""
        user = User.query(User.username == username).get()
        if not user:
            raise endpoints.NotFoundException(
                    'The requested user does not exist!')
        return user

    def _get_by_urlsafe(self, urlsafe, model):
        """This function was copied from utils.py in the skeleton project"""
        try:
            key = ndb.Key(urlsafe=urlsafe)
        except TypeError:
            raise endpoints.BadRequestException('Invalid Key')
        except Exception, e:
            if e.__class__.__name__ == 'ProtocolBufferDecodeError':
                raise endpoints.BadRequestException('Invalid Key')

        entity = key.get()
        if not entity:
            exception_message = 'Object [%s] cannot be found' % model.__name__
            raise endpoints.NotFoundException(exception_message)
        if not isinstance(entity, model):
            raise endpoints.BadRequestException('Incorrect kind')
        return entity

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a user"""
        # Check that username and email lengths do not exceed maximum
        # Without this, the endpoint will fail with a 500, which is not robust
        if len(request.username) > 500:
            raise endpoints.BadRequestException('Username exceeds max length')
        if request.email is None:
            raise endpoints.BadRequestException('Email must be specified')
        if len(request.email) > 500:
            raise endpoints.BadRequestException('Email exceeds max length')

        # Find if a user with this username is already registered
        if User.query(User.username == request.username).get():
            raise endpoints.ConflictException('Username is already taken!')

        # Register the user
        User(username=request.username, email=request.email).put()
        return StringMessage(message='User %s created!' % request.username)

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Start a new game"""
        user = self._get_user(request.username)
        try:
            game = Game.new_game(user.key, request.num_pairs)
            game.put()
        except ValueError as ex:
            raise endpoints.BadRequestException(str(ex))

        taskqueue.add(url='/tasks/cache_average_moves')
        return game.to_form('Good luck playing Concentration!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = self._get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            message = 'Time to make a move!'
            if game.game_over:
                message = 'Game has already been completed'
            return game.to_form(message)
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """
        Makes a move. Returns a game state with message

        First check for exceptional cases where the game is already over, an
        invalid card index was specified, the card chosen has already been
        uncovered, or that the second card in a move is the same as the first.

        If the card is the first card in a move, set this to the game entity's
        previous_choice.

        If the card is the second in a move, append the
        previous and current card to history and create a message containing
        whether the two cards have been matched. If all cards are matched, end
        the game.
        """
        game = self._get_by_urlsafe(request.urlsafe_game_key, Game)
        card = request.card

        if game.game_over:
            return game.to_form('Game already over!')
        if card not in xrange(len(game.cards)):
            raise endpoints.BadRequestException(
                    'Index is beyond bounds of the current game')
        if (game.cards[card] in game.uncovered_pairs):
            raise endpoints.BadRequestException(
                    'The card chosen has already been uncovered')
        if game.previous_choice is not None and card == game.previous_choice:
            raise endpoints.BadRequestException(
                    'Cannot choose the same card as the first card in a move')

        if game.previous_choice is None:
            message = 'You uncover a card'
            game.current_choice = card
            response = game.to_form('You uncover a card')
            # Set this after getting response to avoid intefering with the
            # previous_choice logic in Game.to_form
            game.previous_choice = card
        else:
            game.current_choice = card
            game.history.append(Move(card_1=game.previous_choice, card_2=card))

            if game.cards[game.previous_choice] == game.cards[card]:
                message = 'Matched!'
                game.uncovered_pairs.append(game.cards[card])
                if game.num_uncovered_pairs == game.num_pairs:
                    game.end_game()
                    message = 'You win!'
            else:
                message = 'Not matched'

            response = game.to_form(message)
            game.previous_choice = None

        # Sets the last_move time
        game.last_move = datetime.datetime.now()
        game.email_sent = False

        game.put()
        return response

    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Return all scores"""
        return ScoreForms(items=[score.to_form() for score in Score.query()])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=ScoreForms,
                      path='scores/user/{username}',
                      name='get_user_scores',
                      http_method='GET')
    def get_user_scores(self, request):
        """Get all scores of a user"""
        user = self._get_user(request.username)
        scores = Score.query(Score.user == user.key)
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(response_message=StringMessage,
                      path='games/average_moves',
                      name='get_average_moves',
                      http_method='GET')
    def get_average_moves(self, request):
        """Get the cached average moves elapsed"""
        message = memcache.get(MEMCACHE_AVERAGE_MOVES)
        if not message:
            message = 'Average moves has not been cached'
        return StringMessage(message=message)

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=GameForms,
                      path='game/user/{username}',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Get all games of a user with unfinished games first"""
        user = self._get_user(request.username)
        games = Game.query(Game.user == user.key).order(Game.game_over) \
            .fetch()
        return GameForms(items=[i.to_form() for i in games])

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=StringMessage,
                      path='game/cancel/{urlsafe_game_key}',
                      name='cancel_game',
                      http_method='DELETE')
    def cancel_game(self, request):
        """Cancels a game. Only works if game_over is false"""
        game = self._get_by_urlsafe(request.urlsafe_game_key, Game)
        if game.game_over:
            raise endpoints.BadRequestException(
                    'Completed games cannot be canceled')
        game.key.delete()
        return StringMessage(message='Game has been canceled')

    @endpoints.method(request_message=HIGH_SCORE_REQUEST,
                      response_message=ScoreForms,
                      path='/scores/highscores',
                      name='get_high_scores',
                      http_method='GET')
    def get_high_scores(self, request):
        """
        Gets high scores in descending order, optionally with a (positive)
        limit on the number of results
        """
        query = Score.query().order(-Score.score)
        if request.limit is not None:
            if request.limit <= 0:
                raise endpoints.BadRequestException('Limit must be positive')
            scores = query.fetch(request.limit)
        else:
            scores = query.fetch()
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(response_message=RankingForms,
                      path='/ranking',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        """Returns user rankings in descending order"""
        users = User.query().order(-User.performance).fetch()
        return RankingForms(
                items=[RankingForm(username=user.username,
                                   performance=user.performance)
                       for user in users])

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=HistoryForm,
                      path='/game/history/{urlsafe_game_key}',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """Get the history of a game as a list of moves"""
        game = self._get_by_urlsafe(request.urlsafe_game_key, Game)
        return game.get_history()

    @staticmethod
    def _cache_average_moves():
        """Populates memcache with the average moves elapsed Games"""
        games = Game.query(Game.game_over == False, projection=['moves']) \
            .fetch()

        if games:
            count = len(games)
            total_moves = sum([game.moves for game in games])
            average = float(total_moves) / count
            memcache.set(MEMCACHE_AVERAGE_MOVES,
                         'The average moves elapsed in active games is %.2f'
                         % average)

        return games

    @staticmethod
    def _get_reminder_games():
        """
        Gets a list of games that need email reminders.

        Only fetch those who have not made a move in the predefined reminder
        time of 12 hours.
        """

        time_before_reminder = datetime.timedelta(hours=12)
        remind_before = datetime.datetime.now() - time_before_reminder

        games = Game.query(Game.game_over == False, Game.email_sent == False,
                           Game.last_move < remind_before).fetch()
        return games

api = endpoints.api_server([ConcentrationGameApi])
