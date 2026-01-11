"""
URL configuration for coreiesuai project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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

from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.urls import URLPattern, URLResolver, include, path


def chrome_devtools_handler(request: HttpRequest) -> HttpResponse:
    """Handle Chrome DevTools debugging requests to prevent 404 errors.

    Args:
        request: The HTTP request object from Chrome DevTools.

    Returns:
        HttpResponse with 204 No Content status to acknowledge the request.
    """
    return HttpResponse(status=204)


urlpatterns: list[URLPattern | URLResolver] = [
    path("i18n/", include("django.conf.urls.i18n")),
    # API endpoints - language independent
    path("api/", include("adoration.api_urls")),
    # Chrome DevTools debugging endpoint
    path(".well-known/appspecific/com.chrome.devtools.json", chrome_devtools_handler),
]

# Add language-prefixed patterns
urlpatterns = urlpatterns + list(
    i18n_patterns(
        path("admin/", admin.site.urls),
        path("accounts/", include("django.contrib.auth.urls")),
        path("", include("adoration.urls")),
        prefix_default_language=False,
    )
)
