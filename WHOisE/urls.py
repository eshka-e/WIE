
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static
from django.conf import settings
from django.conf.urls import handler404, handler403, handler500
from WIEapp.views import error_404, error_403, error_500  # <--- ДОБАВИТЬ ЭТУ СТРОКУ

handler404 = 'WIEapp.views.error_404'
handler403 = 'WIEapp.views.error_403'
handler500 = 'WIEapp.views.error_500'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('WIEapp.urls')),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG is False:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# ↓↓↓ ВОТ ЭТО ДОБАВИТЬ В САМЫЙ КОНЕЦ ↓↓↓
urlpatterns += [
    path('test404/', error_404, {'exception': None}),
    path('test403/', error_403, {'exception': None}),
    path('test500/', error_500),
]