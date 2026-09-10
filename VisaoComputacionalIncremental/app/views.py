from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
from django.contrib import messages

from .models import Classe, Inferencia, Modelo, Projeto


@login_required
def home(request):
    context = {
        'user': request.user,
        'service_name': 'VisaoComputacionalIncremental',
        'total_projetos': Projeto.objects.filter(usuario=request.user).count(),
        'total_modelos': Modelo.objects.count(),
        'total_classes': Classe.objects.count(),
        'total_inferencias': Inferencia.objects.filter(projeto__usuario=request.user).count(),
    }
    return render(request, 'app/home.html', context)


def logout_view(request):
    auth_logout(request)
    messages.success(request, "Você saiu com sucesso.")
    return redirect('login')
