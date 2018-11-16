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
from transformer.models import Package
from transformer.views import PackageViewSet, ProcessAccessionsView, ProcessGroupingComponentsView, ProcessTransferComponentsView, ProcessDigitalObjectsView
from rest_framework import routers
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

router = routers.DefaultRouter()
router.register(r'packages', PackageViewSet, 'package')

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
    url(r'^accessions/', ProcessAccessionsView.as_view(), name="accessions"),
    url(r'^grouping-components/', ProcessGroupingComponentsView.as_view(), name="grouping-components"),
    url(r'^transfer-components/', ProcessTransferComponentsView.as_view(), name="transfer-components"),
    url(r'^digital-objects/', ProcessDigitalObjectsView.as_view(), name="digital-objects"),
    url(r'^status/', include('health_check.api.urls')),
    url(r'^admin/', admin.site.urls),
    url(r'^schema(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=None), name='schema-json'),
]
