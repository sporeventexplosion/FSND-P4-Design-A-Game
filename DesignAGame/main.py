import webapp2
from google.appengine.api import mail, app_identity
from api import GamesApi

from models import User


class SendReminderEmail(webapp2.RequestHandler):
    def get(self):
        """Send a reminder email to each User with an email about games.
        Called every hour using a cron job"""
        games = GamesApi._get_reminder_games()
        app_id = app_identity.get_application_id()
        for game in games:
            user = game.user.get()
            if user.email:
                subject = 'You have not made a move in a game in over 12 hours'
                body = 'Hello {}, try out Guess A Number!' \
                    .format(user.username)
                mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
                               user.email,
                               subject,
                               body)


class CacheAverageMoves(webapp2.RequestHandler):
    def post(self):
        """Update game listing announcement in memcache."""
        a = GamesApi._cache_average_moves()
        self.response.set_status(204)


app = webapp2.WSGIApplication([
    ('/crons/send_reminder', SendReminderEmail),
    ('/tasks/cache_average_moves', CacheAverageMoves),
], debug=True)
