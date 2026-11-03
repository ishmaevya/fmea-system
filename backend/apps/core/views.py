from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

SERVICE_NAME = "fmea-backend"
SERVICE_VERSION = "0.1.0"


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health(request):
    checks = {}
    healthy = True

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        healthy = False

    try:
        cache.set("fmea:healthcheck", "ok", timeout=5)
        checks["cache"] = "ok" if cache.get("fmea:healthcheck") == "ok" else "error"
        healthy = healthy and checks["cache"] == "ok"
    except Exception:
        checks["cache"] = "error"
        healthy = False

    payload = {
        "status": "ok" if healthy else "degraded",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "checks": checks,
        "timestamp": timezone.now().isoformat(),
    }
    http_status = status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return Response(payload, status=http_status)
