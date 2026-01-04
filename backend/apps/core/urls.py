"""AgriSecure Core URLs - Health Check"""
from django.urls import path
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache


def health_check(request):
    """Endpoint per verificare lo stato del sistema"""
    status = {
        'status': 'healthy',
        'database': False,
        'cache': False,
    }
    
    # Test Database
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        status['database'] = True
    except Exception as e:
        status['status'] = 'unhealthy'
        status['database_error'] = str(e)
    
    # Test Cache (Redis)
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            status['cache'] = True
    except Exception as e:
        status['status'] = 'unhealthy'
        status['cache_error'] = str(e)
    
    http_status = 200 if status['status'] == 'healthy' else 503
    return JsonResponse(status, status=http_status)


def ready_check(request):
    """Readiness check per orchestratori"""
    return JsonResponse({'ready': True})


urlpatterns = [
    path('', health_check, name='health-check'),
    path('ready/', ready_check, name='ready-check'),
]
