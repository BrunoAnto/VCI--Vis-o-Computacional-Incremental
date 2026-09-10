from django.contrib import admin
from .models import (
    Classe, SinonimoClasse, Projeto, Dataset, Modelo,
    Treinamento, EstrategiaComposicao, Inferencia, Metrica,
)


@admin.register(Classe)
class ClasseAdmin(admin.ModelAdmin):
    list_display = ['id', 'nome_canonico']
    search_fields = ['nome_canonico']


@admin.register(SinonimoClasse)
class SinonimoClasseAdmin(admin.ModelAdmin):
    list_display = ['id', 'termo_sinonimo', 'classe', 'data_cadastro']
    search_fields = ['termo_sinonimo', 'classe__nome_canonico']
    list_filter = ['classe']


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ['id', 'nome', 'usuario', 'status', 'data_cadastro']
    search_fields = ['nome']
    list_filter = ['status']


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ['id', 'nome', 'projeto', 'split', 'quantidade_imagens', 'data_cadastro']
    search_fields = ['nome']
    list_filter = ['split']


@admin.register(Modelo)
class ModeloAdmin(admin.ModelAdmin):
    list_display = ['id', 'nome', 'origem', 'acuracia_geral', 'data_cadastro']
    search_fields = ['nome']
    list_filter = ['origem']


@admin.register(Treinamento)
class TreinamentoAdmin(admin.ModelAdmin):
    list_display = ['id', 'dataset', 'status', 'epocas', 'batch_size', 'data_cadastro']
    list_filter = ['status']


@admin.register(EstrategiaComposicao)
class EstrategiaComposicaoAdmin(admin.ModelAdmin):
    list_display = ['id', 'projeto', 'classe', 'estrategia', 'data_cadastro']
    list_filter = ['estrategia']
    search_fields = ['projeto__nome', 'classe__nome_canonico']


@admin.register(Inferencia)
class InferenciaAdmin(admin.ModelAdmin):
    list_display = ['id', 'projeto', 'confianca_media', 'data_cadastro']
    search_fields = ['projeto__nome']


@admin.register(Metrica)
class MetricaAdmin(admin.ModelAdmin):
    list_display = ['id', 'escopo', 'tipo', 'valor', 'modelo', 'treinamento']
    list_filter = ['escopo', 'tipo']
