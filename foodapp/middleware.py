from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url


class LoginOnlyAccessMiddleware:
    """
    Allow public pages (home, available, signup, signin).
    Redirect others to signin if user is not logged in.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # If user already logged in → allow সব
        if request.user.is_authenticated:
            return self.get_response(request)

        # URLs
        signin_path = resolve_url(settings.LOGIN_URL)
        signup_path = resolve_url('signup')
        home_path = resolve_url('home')
        available_path = resolve_url('available')
        available_food_path = resolve_url('available_food')
        password_reset_path = resolve_url('password_reset')

        static_path = '/' + settings.STATIC_URL.lstrip('/')

        # Public URLs (login ছাড়াই ঢুকতে পারবে)
        public_paths = (
            signin_path,
            signup_path,
            home_path,
            available_path,
            available_food_path,
            password_reset_path,
            '/reset/',
            static_path,
            '/favicon.ico',
        )

        # Allow public pages
        if request.path == '/' or request.path.startswith(public_paths):
            return self.get_response(request)

        # Otherwise redirect to signin
        query_string = urlencode({'next': request.get_full_path()})
        return HttpResponseRedirect(f'{signin_path}?{query_string}')