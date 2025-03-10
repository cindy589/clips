from django import forms

class VideoURLForm(forms.Form):
    url = forms.URLField(label='Ingresa la URL del video', required=True)
