from django import urls
from django.contrib import admin

urlpatterns = [
    urls.path("admin/", admin.site.urls),
]
