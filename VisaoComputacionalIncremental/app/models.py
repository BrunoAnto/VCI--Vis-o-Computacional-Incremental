from django.conf import settings
from django.db import models


class Classe(models.Model):
    nome_canonico = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['nome_canonico']
        verbose_name = 'Classe'
        verbose_name_plural = 'Classes'

    def __str__(self):
        return self.nome_canonico


class SinonimoClasse(models.Model):
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='sinonimos')
    termo_sinonimo = models.CharField(max_length=100, unique=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_cadastro']
        verbose_name = 'Sinônimo de Classe'
        verbose_name_plural = 'Dicionário de Sinônimos'

    def __str__(self):
        return f'{self.termo_sinonimo} → {self.classe.nome_canonico}'


class Projeto(models.Model):
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('verificando', 'Verificando conhecimento'),
        ('aguardando_dataset', 'Aguardando dataset'),
        ('treinando', 'Treinando'),
        ('pronto', 'Pronto'),
    ]

    nome = models.CharField(max_length=200)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='projetos')
    classes_desejadas = models.ManyToManyField(Classe, related_name='projetos')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='rascunho')
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_cadastro']
        verbose_name = 'Projeto'
        verbose_name_plural = 'Projetos'

    def __str__(self):
        return self.nome


class Dataset(models.Model):
    SPLIT_CHOICES = [
        ('train', 'Train'),
        ('valid', 'Valid'),
        ('test', 'Test'),
    ]

    nome = models.CharField(max_length=200)
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='datasets')
    quantidade_imagens = models.PositiveIntegerField(default=0)
    anotacoes = models.FileField(upload_to='datasets/anotacoes/')
    split = models.CharField(max_length=10, choices=SPLIT_CHOICES, default='train')
    classes_cobertas = models.ManyToManyField(Classe, related_name='datasets')
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_cadastro']
        verbose_name = 'Dataset'
        verbose_name_plural = 'Datasets'

    def __str__(self):
        return self.nome


class Modelo(models.Model):
    ORIGEM_CHOICES = [
        ('reutilizado', 'Reutilizado'),
        ('treinado', 'Treinado'),
    ]

    nome = models.CharField(max_length=200)
    origem = models.CharField(max_length=20, choices=ORIGEM_CHOICES)
    classes_suportadas = models.ManyToManyField(Classe, related_name='modelos')
    acuracia_geral = models.FloatField(null=True, blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_cadastro']
        verbose_name = 'Modelo'
        verbose_name_plural = 'Modelos (Registry)'

    def __str__(self):
        return self.nome


class Treinamento(models.Model):
    STATUS_CHOICES = [
        ('em_andamento', 'Em andamento'),
        ('concluido', 'Concluído'),
        ('falhou', 'Falhou'),
    ]

    dataset = models.ForeignKey(Dataset, on_delete=models.PROTECT, related_name='treinamentos')
    modelo_base = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='em_andamento')
    epocas = models.PositiveIntegerField()
    batch_size = models.PositiveIntegerField()
    modelo_resultante = models.ForeignKey(
        Modelo, on_delete=models.SET_NULL, null=True, blank=True, related_name='treinamento_origem'
    )
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_cadastro']
        verbose_name = 'Treinamento'
        verbose_name_plural = 'Treinamentos'

    def __str__(self):
        return f'Treinamento #{self.pk} ({self.status})'


class EstrategiaComposicao(models.Model):
    ESTRATEGIA_CHOICES = [
        ('reuso_exato', 'Reuso exato'),
        ('reuso_parcial', 'Reuso parcial'),
        ('vocabulario_aberto', 'Vocabulário aberto'),
        ('treino', 'Treino'),
    ]

    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='estrategias')
    classe = models.ForeignKey(Classe, on_delete=models.PROTECT, related_name='estrategias')
    estrategia = models.CharField(max_length=30, choices=ESTRATEGIA_CHOICES)
    modelos_envolvidos = models.ManyToManyField(Modelo, related_name='estrategias', blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_cadastro']
        verbose_name = 'Estratégia de Composição'
        verbose_name_plural = 'Estratégias de Composição'

    def __str__(self):
        return f'{self.classe.nome_canonico} → {self.estrategia}'


class Inferencia(models.Model):
    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name='inferencias')
    imagem_entrada = models.ImageField(upload_to='inferencias/entrada/')
    modelos_usados = models.ManyToManyField(Modelo, related_name='inferencias')
    caixas_detectadas = models.JSONField(default=list)
    confianca_media = models.FloatField(null=True, blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_cadastro']
        verbose_name = 'Inferência'
        verbose_name_plural = 'Inferências'

    def __str__(self):
        return f'Inferência #{self.pk} ({self.projeto.nome})'


class Metrica(models.Model):
    ESCOPO_CHOICES = [
        ('modelo', 'Modelo'),
        ('execucao', 'Execução'),
    ]

    escopo = models.CharField(max_length=20, choices=ESCOPO_CHOICES)
    tipo = models.CharField(max_length=50)
    valor = models.FloatField()
    modelo = models.ForeignKey(Modelo, on_delete=models.CASCADE, null=True, blank=True, related_name='metricas')
    treinamento = models.ForeignKey(
        Treinamento, on_delete=models.CASCADE, null=True, blank=True, related_name='metricas'
    )
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_cadastro']
        verbose_name = 'Métrica'
        verbose_name_plural = 'Métricas'

    def __str__(self):
        return f'{self.tipo} = {self.valor}'
