from django.urls import path
from .views import home, remove_bg_api, robots_txt, sitemap_xml

urlpatterns = [
    path('', home, name='home'),
    path('api/remove-bg/', remove_bg_api, name='remove_bg_api'),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap_xml, name='sitemap_xml'),
]