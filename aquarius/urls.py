"""aquarius URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf.urls import url
from django.urls import include, re_path
from transformer.models import Transfer
from transformer.views import TransferViewSet, ProcessTransfersView
from rest_framework import routers
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

router = routers.DefaultRouter()
router.register(r'transfers', TransferViewSet, 'transfer')

schema_view = get_schema_view(
   openapi.Info(
      title="Aquarius API",
      default_version='v1',
      description="API for Aquarius.",
      contact=openapi.Contact(email="archive@rockarch.org"),
      license=openapi.License(name="MIT License"),
   ),
   validators=['flex', 'ssv'],
   public=True,
)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^process/', ProcessTransfersView.as_view(), name="process"),
    url(r'^status/', include('health_check.api.urls')),
    url(r'^admin/', admin.site.urls),
    url(r'^schema(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=None), name='schema-json'),
]
