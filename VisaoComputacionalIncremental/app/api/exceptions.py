from rest_framework.exceptions import NotFound, ValidationError, APIException
from rest_framework import status
import re


class ModelNotFoundError(NotFound):
    default_detail = "O modelo especificado não foi encontrado."
    default_code = "model_not_found"

    def __init__(self, model_name, app_label):
        detail = f"Modelo '{model_name}' não encontrado no app '{app_label}'."
        super().__init__(detail)


class InvalidRelationshipError(ValidationError):
    def __init__(self, field_name, model_name):
        detail = f"O campo '{field_name}' não é um relacionamento válido para o modelo '{model_name}'."
        super().__init__({field_name: detail})


class RelatedObjectNotFoundError(ValidationError):
    default_code = 'related_object_not_found'

    def __init__(self, model_name, object_id, field_name=None):
        context = {"model": model_name, "id": str(object_id), "code": self.default_code}
        if field_name:
            message = f"Não foi possível encontrar {model_name} com ID {object_id} para o campo '{field_name}'."
            context["field"] = field_name
        else:
            message = f"Não foi possível encontrar {model_name} com ID {object_id}."
        super().__init__({"detail": message, "context": context})


class NestedObjectError(ValidationError):
    default_code = 'nested_object_error'

    def __init__(self, relation_field, index=None, field=None, message=None, errors=None):
        path = relation_field
        if index is not None:
            path += f"[{index}]"
        if field:
            path += f".{field}"

        error_message = message or "Erro ao processar objeto aninhado"

        missing_fields = []
        if message and "violates not-null constraint" in message:
            match = re.search(r'null value in column "(\w+)" of relation', message)
            if match:
                missing_fields.append(match.group(1))
                error_message = f"Campo obrigatório faltando: {match.group(1)}"

        context = {"path": path, "relation_field": relation_field, "code": self.default_code}
        if index is not None:
            context["index"] = index
        if field:
            context["field"] = field
        if errors:
            context["errors"] = errors
        if missing_fields:
            context["missing_fields"] = missing_fields

        super().__init__({relation_field: {"message": error_message, "path": path, "context": context}})


class OperationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Ocorreu um erro durante a operação."
    default_code = "operation_error"

    def __init__(self, detail=None, operation=None, reason=None, source=None, data=None, code=None):
        self.detail = detail or self.default_detail
        self.code = code or self.default_code
        error_context = {}
        if operation:
            error_context["operation"] = operation
        if reason:
            error_context["reason"] = reason
        if source:
            error_context["source"] = source
        if data:
            error_context["data"] = data
        if error_context:
            self.detail = {"message": self.detail, "context": error_context, "code": self.code}
        super().__init__(self.detail)


class InvalidFilterError(ValidationError):
    def __init__(self, filter_name, reason):
        super().__init__({"filter": f"Filtro inválido '{filter_name}': {reason}"})


class InvalidDepthError(ValidationError):
    def __init__(self, depth_value, reason):
        super().__init__({"depth": f"Valor de profundidade inválido '{depth_value}': {reason}"})
