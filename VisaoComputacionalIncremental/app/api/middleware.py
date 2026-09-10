import logging
import traceback
from django.http import JsonResponse
from django.conf import settings
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.exceptions import APIException, ValidationError
from rest_framework import status

from app.api.exceptions import (
    ModelNotFoundError, OperationError, InvalidRelationshipError,
    RelatedObjectNotFoundError, NestedObjectError, InvalidFilterError, InvalidDepthError
)

logger = logging.getLogger(__name__)

EXCEPTION_STATUS_CODE_MAP = {
    ModelNotFoundError: status.HTTP_404_NOT_FOUND,
    RelatedObjectNotFoundError: status.HTTP_404_NOT_FOUND,
    InvalidRelationshipError: status.HTTP_400_BAD_REQUEST,
    NestedObjectError: status.HTTP_400_BAD_REQUEST,
    InvalidFilterError: status.HTTP_400_BAD_REQUEST,
    InvalidDepthError: status.HTTP_400_BAD_REQUEST,
    OperationError: status.HTTP_400_BAD_REQUEST,
    ValidationError: status.HTTP_400_BAD_REQUEST,
}


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    if isinstance(exc, Exception):
        status_code = EXCEPTION_STATUS_CODE_MAP.get(exc.__class__, status.HTTP_500_INTERNAL_SERVER_ERROR)
        error_data = {"message": str(exc), "type": exc.__class__.__name__}
        logger.error(f"Exceção não tratada: {exc.__class__.__name__}, Mensagem: {str(exc)}", exc_info=True)
        return JsonResponse(error_data, status=status_code)

    return None


class APIExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as exc:
            if not request.path.startswith('/api/'):
                raise
            return self.handle_exception(request, exc)

    def handle_exception(self, request, exc):
        if isinstance(exc, APIException):
            error_data = self._format_api_exception(exc)
            status_code = exc.status_code
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            error_data = self._format_unexpected_exception(exc, request)

        logger.error(
            f"API Error: {error_data.get('message')}",
            extra={'path': request.path, 'method': request.method},
            exc_info=True,
        )
        return JsonResponse(error_data, status=status_code)

    def _format_api_exception(self, exc):
        if hasattr(exc, 'get_full_details'):
            details = exc.get_full_details()
        elif hasattr(exc, 'detail'):
            details = exc.detail
        else:
            details = str(exc)

        error_data = {"message": str(exc), "type": exc.__class__.__name__, "details": details}
        if hasattr(exc, 'default_code'):
            error_data["code"] = exc.default_code

        if isinstance(exc, ValidationError) and hasattr(exc, 'detail') and isinstance(exc.detail, dict):
            formatted = {}
            for field, errors in exc.detail.items():
                formatted[field] = ", ".join([str(e) for e in errors]) if isinstance(errors, list) else errors
            error_data["fields"] = formatted

        return error_data

    def _format_unexpected_exception(self, exc, request):
        error_data = {"message": "Ocorreu um erro interno no servidor.", "type": exc.__class__.__name__}
        if settings.DEBUG:
            error_data.update({
                "detail": str(exc),
                "traceback": traceback.format_exc().split("\n"),
                "request": {"method": request.method, "path": request.path, "query_params": dict(request.GET)},
            })
        return error_data
