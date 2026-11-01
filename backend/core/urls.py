from core import views
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

user_urlpatterns = [
	path('bootstrap/', views.AppBootstrapView.as_view(), name='user_bootstrap'),
	path('login/', views.LoginView.as_view(), name='user_login'),
	path('logout/', views.LogoutView.as_view(), name='user_logout'),
	path('register/', views.RegisterView.as_view(), name='user_register'),
	path('register/validate-user/', views.ValidateUserView.as_view(), name='user_register_validate_user'),
	path('change-password/', views.PasswordChangeView.as_view(), name='user_change_password'),
	path('auth-status/', views.AuthStatusView.as_view(), name='user_auth_status'),
	path('auth-methods/', views.AuthMethodsView.as_view(), name='user_auth_methods'),
]

urlpatterns = [
	path('api/worlds/', include('worlds.urls')),
	path('admin/', admin.site.urls),
	path('api/user/', include(user_urlpatterns)),
	path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
	path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='swagger-ui'),
	path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='api:schema'), name='redoc'),
]
