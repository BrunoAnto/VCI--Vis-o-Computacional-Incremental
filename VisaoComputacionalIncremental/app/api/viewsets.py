from django.db.models import Count
from django.core.exceptions import ObjectDoesNotExist, FieldError
from rest_framework import viewsets, response, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError
from django.conf import settings
import logging

from app.api.serializers import DynamicSerializer
from app.api.exceptions import (
    ModelNotFoundError, InvalidRelationshipError,
    RelatedObjectNotFoundError, OperationError,
    InvalidFilterError, InvalidDepthError, NestedObjectError,
)
from app.api.utils import resolve_foreign_keys, get_model_from_names, build_nested_results

logger = logging.getLogger(__name__)


class DynamicModelViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend]

    def get_model(self):
        model_name = self.kwargs.get("model")
        app_label = self.kwargs.get("app", "app")

        if not model_name:
            raise ValidationError({"model": "O nome do modelo é obrigatório."})

        try:
            return get_model_from_names(app_label, model_name)
        except Exception:
            raise ModelNotFoundError(model_name, app_label)

    def get_queryset(self):
        model = self.get_model()
        queryset = model.objects.all()

        for param, value in self.request.query_params.items():
            if param.startswith('filter_'):
                field_name = param[7:]
                try:
                    queryset = queryset.filter(**{field_name: value})
                except FieldError as e:
                    raise InvalidFilterError(field_name, str(e))
                except Exception as e:
                    raise InvalidFilterError(field_name, f"Erro inesperado: {str(e)}")

        return queryset

    def get_serializer_class(self):
        model_name = self.kwargs.get("model")
        app_label = self.kwargs.get("app", "app")
        model = self.get_model()

        depth_param = self.request.query_params.get("depth", "0")
        try:
            depth = int(depth_param)
            if depth < 0 or depth > 10:
                raise InvalidDepthError(depth, "A profundidade deve estar entre 0 e 10.")
        except ValueError:
            raise InvalidDepthError(depth_param, "Deve ser um número inteiro válido.")

        fields_param = self.request.query_params.get("fields", None)
        specific_fields = None
        if fields_param:
            fields_list = [f.strip() for f in fields_param.split(",")]
            model_fields = [f.name for f in model._meta.get_fields()]
            valid_fields = [f for f in fields_list if f == 'id' or f in model_fields]
            if valid_fields:
                if 'id' not in valid_fields:
                    valid_fields.insert(0, 'id')
                specific_fields = valid_fields

        include_meta = getattr(settings, 'API_INCLUDE_META', False)

        related_serializers = {}
        if depth > 0:
            for field in model._meta.get_fields():
                if field.one_to_many or field.one_to_one:
                    related_model_name = field.related_model._meta.model_name
                    related_app_label = field.related_model._meta.app_label
                    related_name = field.related_name or f"{related_model_name}_set"
                    try:
                        related_serializers[related_name] = DynamicSerializer.create_inline_serializer(
                            related_model_name, related_app_label, depthParam=max(depth - 1, 0)
                        )
                    except Exception as e:
                        logger.warning(f"Não foi possível criar serializer para {related_name}: {str(e)}")

        class CustomDynamicSerializer(DynamicSerializer):
            def __init__(self, *args, **kwargs):
                include_meta_value = kwargs.pop('include_meta', include_meta)
                kwargs["model_name"] = model_name
                kwargs["app_label"] = app_label
                kwargs["depth"] = depth
                kwargs["fields"] = specific_fields
                super().__init__(*args, **kwargs)
                self.include_meta = include_meta_value

            if depth > 0:
                for related_name, serializer in related_serializers.items():
                    locals()[related_name] = serializer(many=True, read_only=True)

        return CustomDynamicSerializer

    def get_object(self):
        try:
            return super().get_object()
        except Exception:
            model_name = self.kwargs.get("model", "")
            pk = self.kwargs.get("pk", "")
            raise RelatedObjectNotFoundError(model_name, pk)

    def list(self, request, *args, **kwargs):
        group_by = request.query_params.get("group_by", None)
        fields_param = request.query_params.get("fields", None)

        try:
            if group_by:
                group_by_fields = group_by.split(",")
                if fields_param:
                    fields_list = [f.strip() for f in fields_param.split(",")]
                    for gf in group_by_fields:
                        if gf not in fields_list:
                            fields_list.append(gf)
                    queryset = self.get_queryset().values(*fields_list).annotate(count=Count("id"))
                else:
                    queryset = self.get_queryset().values(*group_by_fields).annotate(count=Count("id"))
                results = build_nested_results(queryset, group_by_fields)
                return response.Response(results)
            else:
                return super().list(request, *args, **kwargs)
        except FieldError as e:
            raise ValidationError({"group_by": f"Erro ao agrupar por campos: {str(e)}"})
        except Exception as e:
            logger.error(f"Erro ao listar objetos: {str(e)}")
            raise OperationError(detail="Erro ao listar objetos", operation="list", reason=str(e))

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        model = self.get_model()
        try:
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)

            related_fields = {}
            for field_name, value in list(data.items()):
                if field_name.endswith('_set') and isinstance(value, list):
                    related_fields[field_name] = data.pop(field_name)

            resolved_data = resolve_foreign_keys(model, data)

            from django.db import transaction
            with transaction.atomic():
                instance = serializer.Meta.model.objects.create(**resolved_data)

                for field_name, values in related_fields.items():
                    child_model_name = field_name[:-4]
                    try:
                        child_model = get_model_from_names(model._meta.app_label, child_model_name)
                    except Exception:
                        raise InvalidRelationshipError(field_name, model.__name__)

                    fk_field = next(
                        (f.name for f in child_model._meta.fields if f.is_relation and f.related_model == model),
                        None,
                    )
                    if not fk_field:
                        raise NestedObjectError(relation_field=field_name, message=f"FK não encontrada para {field_name}.")

                    for index, item in enumerate(values):
                        try:
                            item[fk_field] = instance.pk
                            item = resolve_foreign_keys(child_model, item)
                            child_model.objects.create(**item)
                        except ValidationError as e:
                            raise NestedObjectError(relation_field=field_name, index=index, errors=e.detail if hasattr(e, 'detail') else {"error": str(e)})
                        except Exception as e:
                            raise NestedObjectError(relation_field=field_name, index=index, message=str(e))

            return response.Response(self.get_serializer(instance).data, status=status.HTTP_201_CREATED)
        except (ValidationError, InvalidRelationshipError, NestedObjectError):
            raise
        except Exception as e:
            logger.error(f"Erro ao criar objeto: {str(e)}")
            raise OperationError(detail="Erro ao criar objeto", operation="create", reason=str(e))

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            data = request.data.copy()

            related_fields = {}
            for field_name, value in list(data.items()):
                if field_name.endswith('_set') and isinstance(value, list):
                    related_fields[field_name] = data.pop(field_name)

            serializer = self.get_serializer(instance, data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            for field_name, values in related_fields.items():
                child_model_name = field_name[:-4]
                try:
                    child_model = get_model_from_names(instance._meta.app_label, child_model_name)
                except Exception:
                    raise InvalidRelationshipError(field_name, instance._meta.model_name)

                fk_field = next(
                    (f.name for f in child_model._meta.fields if f.is_relation and f.related_model == instance.__class__),
                    None,
                )
                if not fk_field:
                    raise NestedObjectError(relation_field=field_name, message=f"FK não encontrada para {field_name}.")

                child_model.objects.filter(**{fk_field: instance.pk}).delete()
                for index, item in enumerate(values):
                    try:
                        item[fk_field] = instance.pk
                        item = resolve_foreign_keys(child_model, item)
                        child_model.objects.create(**item)
                    except ValidationError as e:
                        raise NestedObjectError(relation_field=field_name, index=index, errors=e.detail if hasattr(e, 'detail') else {"error": str(e)})
                    except Exception as e:
                        raise NestedObjectError(relation_field=field_name, index=index, message=str(e))

            return response.Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)
        except (ValidationError, InvalidRelationshipError, NestedObjectError, RelatedObjectNotFoundError):
            raise
        except Exception as e:
            logger.error(f"Erro ao atualizar objeto: {str(e)}")
            raise OperationError(detail="Erro ao atualizar objeto", operation="update", reason=str(e))

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return response.Response(status=status.HTTP_204_NO_CONTENT)
        except (InvalidRelationshipError, RelatedObjectNotFoundError):
            raise
        except Exception as e:
            logger.error(f"Erro ao excluir objeto: {str(e)}")
            raise OperationError(detail="Erro ao excluir objeto", operation="delete", reason=str(e))
