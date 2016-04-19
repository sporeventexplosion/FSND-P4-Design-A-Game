import endpoints
from protorpc import remote, messages
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from models import StringMessage, GameForm, NewGameForm, ScoreForms, \
        MakeMoveForm
from models import User, Game, Score

USER_REQUEST = endpoints.ResourceContainer(
        username=messages.StringField(1, required=True),
        email=messages.StringField(2))
NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
        urlsafe_game_key=messages.StringField(1))
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
        MakeMoveForm,
        urlsafe_game_key=messages.StringField(1))

MEMCACHE_TOTAL_MOVES = 'TOTAL_MOVES'


@endpoints.api(name='games', version='v1')
class GamesApi(remote.Service):
    def _get_user(self, username):
        user = User.query(User.username==username).get()
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
            else:
                raise

        entity = key.get()
        if not entity:
            raise endpoints.NotFoundException('Entity cannot be found')
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

        # TODO: implement task queues
        # taskqueue.add(url='/tasks/cache_average_moves')
        return game.to_form('Good luck playing Concentration!')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = _get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            return game.to_form('Time to make a move!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns a game state with message"""
        game = self._get_by_urlsafe(request.urlsafe_game_key, Game)
        card = request.card

        if game.game_over:
            return game.to_form('Game already over!')
        if request.card < 0 or card >= len(game.cards):
            raise endpoints.BadRequestException(
                    'Index is beyond bounds of the current game')
        # Check the card has not already been uncovered
        if (game.cards[card] in game.uncovered_pairs):
            raise endpoints.BadRequestException(
                    'The card chosen has already been uncovered')
        # Check that the card is not the the same as the previous card in a
        # pair of choices
        if game.previous_choice != -1 and card == game.previous_choice:
            raise endpoints.BadRequestException(
                    'Cannot choose the same card as the first card in a move')

        if game.previous_choice == -1:
            message = 'You uncover a card'
            game.is_first_card = True
            # Get the response first before setting previous_choice avoid
            # the need of more 'hacks' to get the correct game.previous_choice
            game.current_choice = card
            response = game.to_form('message')
            game.previous_choice = card
        else:
            game.current_choice = card
            game.history.extend([game.previous_choice, card])
            game.moves += 1
            game.is_first_card = False

            if game.cards[game.previous_choice] == game.cards[card]:
                message = 'Matched!'
                game.uncovered_pairs.append(game.cards[card])
                if len(game.uncovered_pairs) == len(game.cards) / 2:
                    game.end_game()
                    message = 'You win!'
            else:
                message = 'Not matched'

            response = game.to_form(message)
            game.previous_choice = -1


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
        scores = Score.query(Score.user==user.key)
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(response_message=StringMessage,
                      path='games/average_attempts',
                      name='get_average_attempts_remaining',
                      http_method='GET')
    def get_average_attempts(self, request):
        """Get the cached average moves remaining"""
        return StringMessage(
                message=memcache.get(MEMCACHE_MOVES_REMAINING) or '')

    @staticmethod
    def _cache_average_moves():
        """Populates memcache with the average moves remaining of Games"""
        games = Game.query(Game.game_over==False, projection=('movew')).fetch()
        if games:
            count = len(games)
            total_moves = sum([game.moves
                                        for game in games])
            average = float(total_moves)/count
            memcache.set(MEMCACHE_TOTAL_MOVES,
                         'The average moves remaining is %.2f'.format(average))

api = endpoints.api_server([GamesApi])
