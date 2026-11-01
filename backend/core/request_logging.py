import json
import logging
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, UTC

request_context = ContextVar('request_context', default=None)
logger = logging.getLogger('django.request')


class RequestContextFilter(logging.Filter):
	def filter(self, record):
		for key, value in (request_context.get() or {}).items():
			setattr(record, key, value)

		return True


class JsonFormatter(logging.Formatter):
	def format(self, record):
		payload = {
			'timestamp': datetime.now(UTC).isoformat(),
			'level': record.levelname,
			'logger': record.name,
			'message': record.getMessage(),
		}

		for key in ('request_id', 'request_method', 'request_path', 'status_code', 'duration_ms'):
			value = getattr(record, key, None)

			if value is not None:
				payload[key] = value

		if record.exc_info:
			payload['exception'] = self.formatException(record.exc_info)

		return json.dumps(payload, ensure_ascii=False)


class RequestLoggingMiddleware:
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		request_id = request.headers.get('X-Request-ID') or uuid.uuid4().hex
		token = request_context.set(
			{
				'request_id': request_id,
				'request_method': request.method,
				'request_path': request.path,
			}
		)
		started_at = time.monotonic()

		try:
			response = self.get_response(request)
			duration_ms = round((time.monotonic() - started_at) * 1000, 2)
			response['X-Request-ID'] = request_id
			logger.info('request.complete', extra={'duration_ms': duration_ms, 'status_code': response.status_code})

			return response
		finally:
			request_context.reset(token)
