from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .forms import CodigoForm, IngresarForm, PerfilForm, RegistroForm
from .models import Adoptante, Criterio, Perro, Solicitud
from .services.codigos import enviar_codigo, verificar_codigo
from .services.motor import RechazoMotor, calcular_compatibilidades
from .services.solicitudes import ReglaSolicitud, crear_solicitud

SESION = "adoptante_id"
PENDIENTE = "email_pendiente"      # email al que se le envió un código, todavía sin confirmar


def _adoptante_actual(request):
    pk = request.session.get(SESION)
    return Adoptante.objects.filter(pk=pk).first() if pk else None


def inicio(request):
    return render(request, "adopciones/inicio.html", {"adoptante": _adoptante_actual(request)})


def registro(request):
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        adoptante = form.save()
        enviar_codigo(adoptante)
        request.session[PENDIENTE] = adoptante.email
        messages.success(request, "Tu perfil quedó registrado. Para confirmar tu email, ingresá el código que te enviamos.")
        return redirect("ingresar_codigo")
    return render(request, "adopciones/registro.html", {"form": form})


def ingresar(request):
    """Paso 1: pedir el código. La respuesta es la misma exista o no el email,
    para no revelar qué emails están registrados."""
    form = IngresarForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip().lower()
        adoptante = Adoptante.objects.filter(email__iexact=email).first()
        if adoptante:
            enviar_codigo(adoptante)
        request.session[PENDIENTE] = email
        messages.info(request, "Si el email está registrado, te enviamos un código de 6 dígitos. Vence en 10 minutos.")
        return redirect("ingresar_codigo")
    return render(request, "adopciones/ingresar.html", {"form": form})


def ingresar_codigo(request):
    """Paso 2: ingresar el código recibido por email."""
    email = request.session.get(PENDIENTE)
    if not email:
        return redirect("ingresar")
    form = CodigoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        adoptante = Adoptante.objects.filter(email__iexact=email).first()
        if adoptante and verificar_codigo(adoptante, form.cleaned_data["codigo"]):
            request.session.cycle_key()             # sesión nueva al ingresar
            request.session.pop(PENDIENTE, None)
            request.session[SESION] = adoptante.pk
            return redirect("listado")
        messages.error(request, "El código es incorrecto o venció. Podés pedir uno nuevo.")
    return render(request, "adopciones/ingresar_codigo.html", {
        "form": form, "email": email, "en_desarrollo": settings.DEBUG,
    })


def salir(request):
    request.session.pop(SESION, None)
    return redirect("inicio")


def perfil(request):
    adoptante = _adoptante_actual(request)
    if adoptante is None:
        return redirect("ingresar")
    form = PerfilForm(request.POST or None, instance=adoptante)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Perfil actualizado.")
        return redirect("listado")
    return render(request, "adopciones/perfil.html", {"form": form, "adoptante": adoptante})


def listado(request):
    adoptante = _adoptante_actual(request)
    if adoptante is None:
        return redirect("ingresar")
    try:
        compatibles, _excluidos = calcular_compatibilidades(adoptante)
    except RechazoMotor as rechazo:
        if str(rechazo) == "perfil incompleto":
            messages.info(request, "Completá el cuestionario para ver los perros compatibles.")
            return redirect("perfil")
        messages.error(request, f"No se pudo calcular la compatibilidad: {rechazo}.")
        compatibles = []
    # Los perros excluidos por los filtros no se muestran.
    return render(request, "adopciones/listado.html",
                  {"adoptante": adoptante, "compatibles": compatibles})


def detalle_perro(request, pk):
    adoptante = _adoptante_actual(request)
    if adoptante is None:
        return redirect("ingresar")
    try:
        compatibles, _ = calcular_compatibilidades(adoptante)
    except RechazoMotor:
        return redirect("listado")
    elegido = next((c for c in compatibles if c.perro.pk == pk), None)
    if elegido is None:
        raise Http404("Este perro no está disponible para vos.")
    pesos = {c.nombre: c.peso for c in Criterio.objects.filter(activo=True)}
    desglose = [
        {"criterio": Criterio.Nombre(nombre).label, "puntos": puntos, "peso": pesos[nombre]}
        for nombre, puntos in elegido.puntos.items()
    ]
    solicitud_activa = Solicitud.objects.filter(
        adoptante=adoptante, perro=elegido.perro,
        estado__in=[Solicitud.Estado.PENDIENTE, Solicitud.Estado.APROBADA],
    ).first()
    return render(request, "adopciones/detalle_perro.html", {
        "adoptante": adoptante, "item": elegido, "desglose": desglose,
        "solicitud_activa": solicitud_activa,
    })


@require_POST
def solicitar(request, pk):
    adoptante = _adoptante_actual(request)
    if adoptante is None:
        return redirect("ingresar")
    perro = get_object_or_404(Perro, pk=pk)
    try:
        crear_solicitud(adoptante, perro)
        messages.success(request, f"Enviaste tu solicitud por {perro.nombre}. El personal la va a revisar.")
        return redirect("mis_solicitudes")
    except ReglaSolicitud as error:
        messages.error(request, str(error))
        return redirect("listado")


def mis_solicitudes(request):
    adoptante = _adoptante_actual(request)
    if adoptante is None:
        return redirect("ingresar")
    solicitudes = adoptante.solicitudes.select_related("perro")
    return render(request, "adopciones/mis_solicitudes.html",
                  {"adoptante": adoptante, "solicitudes": solicitudes})


@ensure_csrf_cookie
def listado_dinamico(request):
    """Listado que se arma en el navegador con JavaScript, consumiendo la API REST."""
    adoptante = _adoptante_actual(request)
    if adoptante is None:
        return redirect("ingresar")
    return render(request, "adopciones/listado_dinamico.html", {"adoptante": adoptante})
