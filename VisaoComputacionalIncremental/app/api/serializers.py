from rest_framework import serializers
from django.core.exceptions import FieldDoesNotExist, ValidationError as DjangoValidationError
from django.core.validators import MaxLengthValidator
from django.db import transaction
import logging

from app.api.exceptions import ModelNotFoundError, OperationError
from app.api.utils import get_model_from_names

logger = logging.getLogger(__name__)


class DynamicSerializer(serializers.ModelSerializer):
    def __init__(self, *args, model_name=None, app_label=None, depth=0, fields=None, **kwargs):
        if not model_name:
            raise OperationError(detail="Nome do modelo é obrigatório", operation="DynamicSerializer.__init__", code="missing_model_name")
        if not app_label:
            raise OperationError(detail="Nome do aplicativo é obrigatório", operation="DynamicSerializer.__init__", code="missing_app_label")

        model = get_model_from_names(app_label, model_name)
        model_fields = fields if fields is not None else "__all__"

        Meta = type("Meta", (object,), {"model": model, "fields": model_fields, "depth": depth})
        self.Meta = Meta
        self.model_name = model_name
        self.app_label = app_label
        self.depth_value = depth
        self.selected_fields = fields

        super().__init__(*args, **kwargs)
        self._add_field_validations()

    def build_nested_field(self, field_name, relation_info, nested_depth):
        from django.contrib.auth import get_user_model
        UserModel = get_user_model()
        if relation_info.related_model == UserModel:
            class SafeUserSerializer(serializers.ModelSerializer):
                class Meta:
                    model = UserModel
                    fields = ['id', 'username', 'first_name', 'last_name']
                    read_only_fields = fields

            return SafeUserSerializer, {'read_only': True}
        return super().build_nested_field(field_name, relation_info, nested_depth)

    def _add_field_validations(self):
        model = self.Meta.model
        for field_name, field in self.fields.items():
            try:
                model_field = model._meta.get_field(field_name)
                if hasattr(model_field, 'max_length') and model_field.max_length:
                    field.validators.append(MaxLengthValidator(model_field.max_length))
                if hasattr(model_field, 'validators'):
                    field.validators.extend(model_field.validators)
            except FieldDoesNotExist:
                pass

    @classmethod
    def create_inline_serializer(cls, related_model_name, app_label=None, depthParam=0, fields=None):
        try:
            from django.contrib.auth import get_user_model
            UserModel = get_user_model()
            related_model = get_model_from_names(app_label, related_model_name)

            if related_model == UserModel:
                model_fields = ['id', 'username', 'first_name', 'last_name']
            else:
                model_fields = fields if fields is not None else "__all__"

            class InlineSerializer(serializers.ModelSerializer):
                class Meta:
                    model = related_model
                    fields = model_fields
                    depth = depthParam or 0

            return InlineSerializer
        except ModelNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Erro ao criar serializer inline para {related_model_name}: {str(e)}")
            raise OperationError(detail="Erro ao criar serializer para modelo relacionado", operation="create_inline_serializer", reason=str(e))

    def create(self, validated_data):
        model_name = self.Meta.model.__name__
        try:
            with transaction.atomic():
                return self.Meta.model.objects.create(**validated_data)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else {"non_field_errors": [str(e)]})
        except Exception as e:
            logger.error(f"Erro ao criar {model_name}: {str(e)}")
            raise OperationError(detail="Erro ao criar objeto", operation="create", reason=str(e))

    def update(self, instance, validated_data):
        model_name = self.Meta.model.__name__
        try:
            with transaction.atomic():
                for attr, value in validated_data.items():
                    setattr(instance, attr, value)
                instance.save()
                return instance
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict if hasattr(e, 'message_dict') else {"non_field_errors": [str(e)]})
        except Exception as e:
            logger.error(f"Erro ao atualizar {model_name}: {str(e)}")
            raise OperationError(detail="Erro ao atualizar objeto", operation="update", reason=str(e))

    def to_representation(self, instance):
        try:
            representation = super().to_representation(instance)
            if getattr(self, 'include_meta', False):
                representation['_meta'] = {'model': self.model_name, 'app': self.app_label}
                if hasattr(self, 'selected_fields') and self.selected_fields is not None:
                    representation['_meta']['selected_fields'] = self.selected_fields
            return representation
        except Exception as e:
            logger.error(f"Erro ao serializar {self.model_name}: {str(e)}")
            return {'error': f"Erro ao serializar {self.model_name}", 'id': getattr(instance, 'pk', None)}
