from django import forms

from .models import Adoptante

SI_NO = [("True", "Sí"), ("False", "No")]


def _si_no(label):
    return forms.TypedChoiceField(
        label=label, choices=SI_NO, coerce=lambda v: v == "True", widget=forms.RadioSelect
    )


class IngresarForm(forms.Form):
    email = forms.EmailField(label="Tu email")


class PerfilForm(forms.ModelForm):
    """Cuestionario del adoptante. En el perfil, el email no se edita."""

    hay_ninos = _si_no("¿Hay niños en el hogar?")
    tiene_otras_mascotas = _si_no("¿Tenés otras mascotas?")

    class Meta:
        model = Adoptante
        fields = [
            "nombre", "tipo_vivienda", "espacio_exterior", "hay_ninos",
            "tiene_otras_mascotas", "experiencia_previa", "nivel_actividad",
            "edad_preferida", "pref_apto_ninos", "pref_apto_otras_mascotas",
            "pref_apto_departamento",
        ]
        labels = {
            "tipo_vivienda": "Tipo de vivienda",
            "espacio_exterior": "Espacio exterior (patio, terraza)",
            "experiencia_previa": "Experiencia previa con perros",
            "nivel_actividad": "Tu nivel de actividad",
            "edad_preferida": "Edad preferida del perro",
            "pref_apto_ninos": "Prefiero un perro apto para niños",
            "pref_apto_otras_mascotas": "Prefiero un perro apto para otras mascotas",
            "pref_apto_departamento": "Prefiero un perro apto para departamento",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Los campos del cuestionario son obligatorios en el formulario.
        for nombre in ("tipo_vivienda", "espacio_exterior", "experiencia_previa",
                       "nivel_actividad", "edad_preferida"):
            campo = self.fields[nombre]
            campo.required = True
            campo.choices = [c for c in campo.choices if c[0] != ""]
            campo.widget.choices = campo.choices
        # Valores iniciales de los campos Sí/No cuando se edita un perfil existente.
        for nombre in ("hay_ninos", "tiene_otras_mascotas"):
            valor = getattr(self.instance, nombre)
            if valor is not None:
                self.initial[nombre] = str(valor)


class RegistroForm(PerfilForm):
    class Meta(PerfilForm.Meta):
        fields = ["nombre", "email"] + PerfilForm.Meta.fields[1:]
