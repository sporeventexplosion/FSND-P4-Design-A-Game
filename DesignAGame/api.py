import endpoints
from protorpc import remote, messages

from models import StringMessage
from models import User

USER_REQUEST = endpoints.ResourceContainer(username=messages.StringField(1),
                                           email=messages.StringField(2))


@endpoints.api(name='games', version='v1')
class GamesApi(remote.Service):
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='create_user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a user"""
        # Check that username and email lengths do not exceed maximum
        # Without this, the endpoint will fail with a 500, which is not robust
        if len(request.username) > 500:
            raise endpoints.BadRequestException('Username exceeds max length')
        if len(request.email) > 500:
            raise endpoints.BadRequestException('Email exceeds max length')

        # Find if a user with this username is already registered
        if User.query(User.username == request.username).get():
            raise endpoints.ConflictException('Username is already taken!')

        # Register the user
        User(username=request.username, email=request.email).put()
        return StringMessage(message='User %s created!' % request.username)

api = endpoints.api_server([GamesApi])
