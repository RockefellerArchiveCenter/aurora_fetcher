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
from transformer.views import *
from rest_framework import routers
from rest_framework.schemas import get_schema_view

router = routers.DefaultRouter()
router.register(r'packages', PackageViewSet, 'package')

schema_view = get_schema_view(
      title="Aquarius API",
      description="Endpoints for Aquarius microservice application."
)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^accessions/', ProcessAccessionsView.as_view(), name="accessions"),
    url(r'^grouping-components/', ProcessGroupingComponentsView.as_view(), name="grouping-components"),
    url(r'^transfer-components/', ProcessTransferComponentsView.as_view(), name="transfer-components"),
    url(r'^digital-objects/', ProcessDigitalObjectsView.as_view(), name="digital-objects"),
    url(r'^send-update/', UpdateRequestView.as_view(), name="send-update"),
    url(r'^send-accession-update/', AccessionUpdateRequestView.as_view(), name="send-accession-update"),
    url(r'^status/', include('health_check.api.urls')),
    url(r'^admin/', admin.site.urls),
    url(r'^schema/', schema_view, name='schema'),
]
