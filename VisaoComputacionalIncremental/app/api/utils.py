from django.core.exceptions import ObjectDoesNotExist
from django.apps import apps
from django.db import models
from django.db.models.fields.reverse_related import ManyToOneRel, OneToOneRel, ManyToManyRel
from app.api.exceptions import (
    RelatedObjectNotFoundError, ModelNotFoundError, OperationError
)
import logging

logger = logging.getLogger(__name__)

APP_LABEL = "app"


def get_model_from_names(app_label, model_name):
    try:
        return apps.get_model(app_label=app_label, model_name=model_name)
    except LookupError:
        raise ModelNotFoundError(model_name, app_label)


def resolve_foreign_keys(model, data):
    resolved_data = data.copy()
    try:
        for field in model._meta.get_fields():
            if field.is_relation and not field.auto_created and field.many_to_one:
                field_name = field.name
                if field_name in resolved_data and resolved_data[field_name] is not None:
                    related_model = field.related_model
                    related_id = resolved_data[field_name]
                    try:
                        resolved_data[field_name] = related_model.objects.get(pk=related_id)
                    except ObjectDoesNotExist:
                        raise RelatedObjectNotFoundError(
                            model_name=related_model.__name__,
                            object_id=related_id,
                            field_name=field_name,
                        )
        return resolved_data
    except RelatedObjectNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Erro ao resolver chaves estrangeiras: {str(e)}")
        raise OperationError(
            detail="Erro ao processar relacionamentos",
            operation="resolve_foreign_keys",
            reason=str(e),
            source="app.api.utils",
        )


def build_nested_results(queryset, group_by_fields):
    try:
        results = []
        for item in queryset:
            current_level = results
            for i, field in enumerate(group_by_fields):
                value = item[field]
                found = False
                for entry in current_level:
                    if entry.get(field) == value:
                        if i == len(group_by_fields) - 1:
                            entry["count"] = item["count"]
                        current_level = entry.setdefault("children", [])
                        found = True
                        break
                if not found:
                    new_entry = {field: value}
                    if i == len(group_by_fields) - 1:
                        new_entry["count"] = item["count"]
                    else:
                        new_entry["children"] = []
                    current_level.append(new_entry)
                    current_level = new_entry.get("children", [])
        return results
    except Exception as e:
        logger.error(f"Erro ao construir resultados aninhados: {str(e)}")
        raise OperationError(
            detail="Erro ao construir resultados aninhados",
            operation="build_nested_results",
            reason=str(e),
            source="app.api.utils",
        )


def get_schema_info(app_name=None, model_name=None, obj_id=None, include_related=None, related_depth=1):
    try:
        result = {}
        if app_name and not model_name:
            app_models = apps.get_app_config(app_name).get_models()
            for model in app_models:
                result[model.__name__] = _get_model_schema(model, include_related, related_depth)
        elif app_name and model_name:
            model = get_model_from_names(app_name, model_name)
            result = _get_model_schema(model, include_related, related_depth)
            if obj_id:
                try:
                    obj = model.objects.get(pk=obj_id)
                    result['instance_values'] = {
                        field.name: getattr(obj, field.name)
                        for field in model._meta.fields
                    }
                except ObjectDoesNotExist:
                    raise ObjectDoesNotExist(f"Objeto {model_name} com id={obj_id} não encontrado")
        else:
            raise OperationError(
                detail="Parâmetros insuficientes",
                operation="get_schema_info",
                reason="É necessário fornecer pelo menos o nome do app",
                source="app.api.utils",
            )
        return result
    except (ModelNotFoundError, ObjectDoesNotExist):
        raise
    except Exception as e:
        logger.error(f"Erro ao obter schema: {str(e)}")
        raise OperationError(
            detail="Erro ao obter informações de schema",
            operation="get_schema_info",
            reason=str(e),
            source="app.api.utils",
        )


def _get_model_schema(model, include_related=None, related_depth=1):
    schema = {
        'model_info': {
            'name': model.__name__,
            'app_label': model._meta.app_label,
            'verbose_name': model._meta.verbose_name,
            'verbose_name_plural': model._meta.verbose_name_plural,
            'db_table': model._meta.db_table,
        },
        'fields': {},
        'foreign_keys': {},
        'reverse_foreign_keys': {},
    }

    for field in model._meta.get_fields():
        if field.auto_created and not field.concrete:
            continue
        field_type = field.get_internal_type() if hasattr(field, 'get_internal_type') else type(field).__name__
        field_info = {
            'type': field_type,
            'null': getattr(field, 'null', False),
            'blank': getattr(field, 'blank', False),
            'unique': getattr(field, 'unique', False),
            'primary_key': getattr(field, 'primary_key', False),
        }
        if hasattr(field, 'max_length') and field.max_length:
            field_info['max_length'] = field.max_length
        if hasattr(field, 'choices') and field.choices:
            field_info['choices'] = field.choices
        if hasattr(field, 'default') and field.default is not models.NOT_PROVIDED:
            default = field.default
            field_info['default'] = f'<function: {default.__name__}>' if callable(default) else default
        schema['fields'][field.name] = field_info

        if field.is_relation and field.many_to_one:
            related_model = field.related_model
            schema['foreign_keys'][field.name] = {
                'model': related_model.__name__,
                'app': related_model._meta.app_label,
                'verbose_name': getattr(field, 'verbose_name', field.name),
                'related_name': getattr(field, 'related_name', None),
                'on_delete': getattr(field, 'on_delete', None).__name__ if hasattr(field, 'on_delete') else None,
            }

    for field in model._meta.get_fields():
        if field.auto_created and field.is_relation and hasattr(field, 'related_model'):
            related_model = field.related_model
            rel_type = 'unknown'
            if isinstance(field, ManyToOneRel):
                rel_type = 'one_to_many'
            elif isinstance(field, OneToOneRel):
                rel_type = 'one_to_one'
            elif isinstance(field, ManyToManyRel):
                rel_type = 'many_to_many'
            schema['reverse_foreign_keys'][field.get_accessor_name()] = {
                'model': related_model.__name__,
                'app': related_model._meta.app_label,
                'type': rel_type,
                'field_name': field.field.name if hasattr(field, 'field') else None,
                'verbose_name': getattr(field, 'verbose_name', field.get_accessor_name()),
            }

    if include_related:
        schema['related_models'] = _get_related_models_info(model, include_related, related_depth)

    return schema


def _get_related_models_info(model, include_related, depth, visited_models=None):
    if visited_models is None:
        visited_models = set()
    if depth <= 0 or model in visited_models:
        return {}
    visited_models.add(model)
    related_info = {}
    if include_related in ['parents', 'both']:
        parents = _get_parent_models(model, depth - 1, visited_models.copy())
        if parents:
            related_info['parents'] = parents
    if include_related in ['children', 'both']:
        children = _get_child_models(model, depth - 1, visited_models.copy())
        if children:
            related_info['children'] = children
    return related_info


def _get_parent_models(model, remaining_depth, visited_models):
    parents = {}
    for field in model._meta.get_fields():
        if field.is_relation and field.many_to_one and not field.auto_created:
            related_model = field.related_model
            if related_model not in visited_models:
                parent_info = {
                    'model': related_model.__name__,
                    'app_label': related_model._meta.app_label,
                    'field_name': field.name,
                    'verbose_name': related_model._meta.verbose_name,
                    'relationship_type': 'foreign_key',
                    'required': not field.null,
                    'on_delete': getattr(field, 'on_delete', None).__name__ if hasattr(field, 'on_delete') else None,
                }
                if remaining_depth > 0:
                    nested = _get_related_models_info(related_model, 'both', remaining_depth, visited_models)
                    if nested:
                        parent_info['related_models'] = nested
                parents[field.name] = parent_info
    return parents


def _get_child_models(model, remaining_depth, visited_models):
    children = {}
    for field in model._meta.get_fields():
        if field.auto_created and field.is_relation and hasattr(field, 'related_model'):
            related_model = field.related_model
            if related_model not in visited_models:
                relationship_type = 'unknown'
                if isinstance(field, ManyToOneRel):
                    relationship_type = 'reverse_foreign_key'
                elif isinstance(field, OneToOneRel):
                    relationship_type = 'one_to_one_reverse'
                elif isinstance(field, ManyToManyRel):
                    relationship_type = 'many_to_many_reverse'
                child_info = {
                    'model': related_model.__name__,
                    'app_label': related_model._meta.app_label,
                    'accessor_name': field.get_accessor_name(),
                    'verbose_name': related_model._meta.verbose_name,
                    'relationship_type': relationship_type,
                    'field_name': field.field.name if hasattr(field, 'field') else None,
                }
                if hasattr(field, 'field'):
                    child_info['original_field_info'] = {
                        'null': getattr(field.field, 'null', False),
                        'on_delete': getattr(field.field, 'on_delete', None).__name__ if hasattr(field.field, 'on_delete') else None,
                    }
                if remaining_depth > 0:
                    nested = _get_related_models_info(related_model, 'both', remaining_depth, visited_models)
                    if nested:
                        child_info['related_models'] = nested
                children[field.get_accessor_name()] = child_info
    return children
