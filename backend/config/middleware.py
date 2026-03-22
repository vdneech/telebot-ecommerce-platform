import logging
import time

logger = logging.getLogger('gfs')

class APILoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        try:
            response = self.get_response(request)
            duration = time.time() - start
            
            user_id = getattr(getattr(request, 'user', None), 'id', 'Anonymous')
            
            logger.info(
                f'{request.method} {request.path} '
                f'{response.status_code} {duration:.2f}s '
                f'user={user_id}'
            )
            return response
        except Exception as e:
            duration = time.time() - start
            

            logger.error(
                f'{request.method} {request.path} '
                f'ERROR 500 {duration:.2f}s - {str(e)}',
                exc_info=True
            )
            raise