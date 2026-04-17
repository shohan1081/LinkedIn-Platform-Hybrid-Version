from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from jwt import decode as jwt_decode
from django.conf import settings
from users.models import User
from business_account.models import BusinessAccount
from urllib.parse import parse_qs

@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        try:
            return BusinessAccount.objects.get(id=user_id)
        except BusinessAccount.DoesNotExist:
            return AnonymousUser()

class JWTAuthMiddleware:
    """
    Custom middleware to authenticate WebSockets using JWT in query string.
    """
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # Extract token from query string
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]

        if not token:
            scope['user'] = AnonymousUser()
        else:
            try:
                # This validates the token signature
                UntypedToken(token)
                # This decodes the payload
                decoded_data = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                user_id = decoded_data.get('user_id')
                scope['user'] = await get_user(user_id)
            except Exception as e:
                print(f"WebSocket Auth Error: {str(e)}")
                scope['user'] = AnonymousUser()

        return await self.inner(scope, receive, send)
