# catalogue_app/forms.py
from django import forms
from django.forms.widgets import ClearableFileInput
from .models import Produit, Catalogue, Enseigne
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import SetPasswordForm
class EmployeCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username']
        labels = {'username': "Nom d'utilisateur"}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'  

class EmployePasswordChangeForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control form-control-sm'

class AdminCreationForm(UserCreationForm):
    code_secret = forms.CharField(
        label="Code administrateur",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Code fourni par la direction'})
    )

    class Meta:
        model = User
        fields = ['username']
        labels = {'username': "Nom d'utilisateur"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'code_secret':
                field.widget.attrs['class'] = 'form-control'

    def clean_code_secret(self):
        from django.conf import settings
        code = self.cleaned_data.get('code_secret')
        if code != settings.ADMIN_SIGNUP_CODE:
            raise forms.ValidationError("Code administrateur incorrect.")
        return code
     
class MultipleFileInput(ClearableFileInput):
    allow_multiple_selected = True

class UploadForm(forms.Form):
    enseigne = forms.ModelChoiceField(
        queryset=Enseigne.objects.all(), 
        empty_label="Sélectionnez une enseigne",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_debut = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_fin = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    note = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: Saint Valentin, Noël, Eid, Promotion été...'
        }),
        label="Note"
    )
    # Champ pour plusieurs images
    images = forms.FileField(
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'multiple': True,
            'accept': 'image/*'
        }),
        required=True,
        label="Images du catalogue (sélectionnez plusieurs)"
    )
    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        
        # VALIDATION : date_debut doit être < date_fin
        if date_debut and date_fin:
            if date_debut >= date_fin:
                raise forms.ValidationError(
                    "La date de début doit être antérieure à la date de fin."
                )
        
        return cleaned_data   
    
class ProduitForm(forms.ModelForm):
    class Meta:
        model = Produit
        fields = [
            'nom', 'nom_fr', 'nom_ar', 'marque',
            'prix', 'prix_avant', 'pourcentage', 'remise',
            'desc_1', 'desc_2', 'desc_3',
            'note_1', 'note_2',
            'extrait_texte'
        ]
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du produit (affiché)'}),
            'nom_fr': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom en français'}),
            'nom_ar': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الاسم بالعربية'}),
            'marque': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Marque'}),
            'prix': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'placeholder': '0.000'}),
            'prix_avant': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'placeholder': '0.000'}),
            'pourcentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.0'}),
            'remise': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'placeholder': '0.000'}),
            'desc_1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Desc 1'}),
            'desc_2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Desc 2'}),
            'desc_3': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Desc 3'}),
            'note_1': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Note 1 (saisie manuelle)'}),
            'note_2': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Note 2 (saisie manuelle)'}),
            'extrait_texte': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Texte extrait par OCR'}),
        }
        labels = {
            'nom': 'Nom du produit (affiché)',
            'nom_fr': 'Nom (Français)',
            'nom_ar': 'Nom (Arabe)',
            'marque': 'Marque',
            'prix': 'Prix (DT)',
            'prix_avant': 'Prix avant (DT)',
            'pourcentage': 'Pourcentage (%)',
            'remise': 'Remise (DT)',
            'desc_1': 'Desc 1',
            'desc_2': 'Desc 2',
            'desc_3': 'Desc 3',
            'note_1': 'Note 1',
            'note_2': 'Note 2',
            'extrait_texte': 'Texte extrait',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        prix = cleaned_data.get('prix')
        prix_avant = cleaned_data.get('prix_avant')
        pourcentage = cleaned_data.get('pourcentage')
        remise = cleaned_data.get('remise')
        
        #  Logique de validation et calcul
        # 1. Si remise est fournie mais prix_avant est vide -> le déduire (sans écraser une valeur déjà saisie)
        if remise and remise > 0:
            if prix is not None and prix > 0 and prix_avant is None:
                cleaned_data['prix_avant'] = prix + remise
                prix_avant = cleaned_data['prix_avant']
                if pourcentage is None:
                    cleaned_data['pourcentage'] = round((remise / (prix + remise)) * 100)
        
        # 2. Validation prix vs prix_avant
        if prix is not None and prix_avant is not None:
            if prix >= prix_avant:
                raise forms.ValidationError(
                    "Le prix doit être inférieur au prix avant remise (prix < prix_avant)"
                )
            if pourcentage is None:
                cleaned_data['pourcentage'] = round(((prix_avant - prix) / prix_avant) * 100)
            if remise is None:
                cleaned_data['remise'] = prix_avant - prix
        
        # 3. Si prix et pourcentage -> prix_avant
        if prix is not None and pourcentage is not None and pourcentage > 0 and pourcentage <= 100:
            if prix_avant is None:
                cleaned_data['prix_avant'] = prix / (1 - pourcentage / 100)
                cleaned_data['remise'] = cleaned_data['prix_avant'] - prix
        
        # 4. Si prix_avant et pourcentage -> prix
        if prix_avant is not None and pourcentage is not None and pourcentage > 0 and pourcentage <= 100:
            if prix is None:
                cleaned_data['prix'] = prix_avant * (1 - pourcentage / 100)
                cleaned_data['remise'] = prix_avant - cleaned_data['prix']
        
        # 5. Validation du pourcentage
        pourcentage = cleaned_data.get('pourcentage')
        if pourcentage is not None:
            if pourcentage < 0:
                cleaned_data['pourcentage'] = 0
            elif pourcentage > 100:
                cleaned_data['pourcentage'] = 100
        
        return cleaned_data