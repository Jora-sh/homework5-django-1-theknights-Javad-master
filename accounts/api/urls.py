from django.urls import path
from .views import RegisterView, UserDetailView, ObtainTokenPairView, LogoutView
from rest_framework_simplejwt.views import TokenRefreshView

app_name = 'accounts_api'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', ObtainTokenPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', UserDetailView.as_view(), name='me'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
