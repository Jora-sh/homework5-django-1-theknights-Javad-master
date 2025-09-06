from rest_framework_simplejwt.authentication import JWTAuthentication


class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.auth = JWTAuthentication()

    def __call__(self, request):
        access = request.COOKIES.get('access_token')
        if access:
            if 'HTTP_AUTHORIZATION' not in request.META:
                request.META['HTTP_AUTHORIZATION'] = f'Bearer {access}'
            try:
                user_auth_tuple = self.auth.authenticate(request)
                if user_auth_tuple is not None:
                    user, validated_token = user_auth_tuple
                    request.user = user
            except Exception:
                pass

        response = self.get_response(request)
        return response
