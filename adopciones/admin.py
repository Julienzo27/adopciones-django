from django import forms
from django.contrib import admin, messages
from django.forms import BaseModelFormSet

from .models import Adoptante, Criterio, Perro, Solicitud
from .services.solicitudes import ReglaSolicitud, aprobar_solicitud, rechazar_solicitud

MENSAJE_SIN_CRITERIOS = "Tiene que quedar al menos un criterio activo con peso mayor que 0."


@admin.register(Perro)
class PerroAdmin(admin.ModelAdmin):
    list_display = ("nombre", "edad", "nivel_energia", "estado")
    list_filter = ("estado", "nivel_energia")
    search_fields = ("nombre",)


@admin.register(Adoptante)
class AdoptanteAdmin(admin.ModelAdmin):
    list_display = ("nombre", "email", "tipo_vivienda", "perfil_completo")
    search_fields = ("nombre", "email")

    @admin.display(boolean=True, description="Perfil completo")
    def perfil_completo(self, obj):
        return obj.perfil_completo


class CriterioAdminForm(forms.ModelForm):
    """Formulario de edición de un criterio: no deja la configuración sin criterios útiles."""

    class Meta:
        model = Criterio
        fields = "__all__"

    def clean(self):
        datos = super().clean()
        activo, peso = datos.get("activo"), datos.get("peso")
        if activo is None or peso is None:
            return datos
        if not (activo and peso > 0):
            otros = Criterio.objects.filter(activo=True, peso__gt=0).exclude(pk=self.instance.pk)
            if not otros.exists():
                raise forms.ValidationError(MENSAJE_SIN_CRITERIOS)
        return datos


class CriteriosFormSet(BaseModelFormSet):
    """Validación de la lista editable: mira todos los criterios juntos."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        utiles = [
            f for f in self.forms
            if f.cleaned_data.get("activo") and (f.cleaned_data.get("peso") or 0) > 0
        ]
        if not utiles:
            raise forms.ValidationError(MENSAJE_SIN_CRITERIOS)


@admin.register(Criterio)
class CriterioAdmin(admin.ModelAdmin):
    form = CriterioAdminForm
    list_display = ("nombre", "peso", "activo", "peso_relativo")
    list_editable = ("peso", "activo")
    ordering = ("id",)

    def get_changelist_formset(self, request, **kwargs):
        return super().get_changelist_formset(request, formset=CriteriosFormSet, **kwargs)

    @admin.display(description="Peso relativo (%)")
    def peso_relativo(self, obj):
        if not obj.activo:
            return "—"
        total = sum(c.peso for c in Criterio.objects.filter(activo=True))
        return f"{obj.peso / total * 100:.1f} %" if total else "—"


@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    list_display = ("adoptante", "perro", "estado", "porcentaje_compatibilidad", "fecha", "personal")
    list_filter = ("estado", "perro")
    ordering = ("perro__nombre", "-porcentaje_compatibilidad")   # mayor % primero, por perro
    readonly_fields = ("porcentaje_compatibilidad", "detalle_calculo", "fecha", "personal")
    actions = ["aprobar_seleccionadas", "rechazar_seleccionadas"]

    @admin.action(description="Aprobar solicitudes seleccionadas")
    def aprobar_seleccionadas(self, request, queryset):
        for solicitud in queryset:
            try:
                aprobar_solicitud(solicitud, request.user)
                self.message_user(request, f"Aprobada: {solicitud}", messages.SUCCESS)
            except ReglaSolicitud as error:
                self.message_user(request, f"{solicitud}: {error}", messages.WARNING)

    @admin.action(description="Rechazar solicitudes seleccionadas")
    def rechazar_seleccionadas(self, request, queryset):
        for solicitud in queryset:
            try:
                rechazar_solicitud(solicitud, request.user)
                self.message_user(request, f"Rechazada: {solicitud}", messages.SUCCESS)
            except ReglaSolicitud as error:
                self.message_user(request, f"{solicitud}: {error}", messages.WARNING)
