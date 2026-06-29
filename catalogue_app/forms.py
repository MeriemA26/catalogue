# catalogue_app/forms.py
from django import forms
from .models import Produit, Catalogue, Enseigne

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
    image = forms.ImageField(
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )


class ProduitForm(forms.ModelForm):
    class Meta:
        model = Produit
        fields = [
            'nom_fr', 'nom_ar', 'marque',
            'prix', 'prix_avant', 'pourcentage', 'remise',
            'description', 'description_2', 'description_3',
        ]
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du produit (affiché)'}),
            'nom_fr': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom en français'}),
            'nom_ar': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الاسم بالعربية'}),
            'marque': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Marque'}),
            'prix': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'placeholder': '0.000'}),
            'prix_avant': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'placeholder': '0.000'}),
            'pourcentage': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01',  # ✅ Permet des valeurs comme 11.0
                'min': '0',
                'max': '100'
            }),
            'remise': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'placeholder': '0.000'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Description'}),
            'description_2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Description 2'}),
            'description_3': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Description 3'}),
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
            'description': 'Description',
            'description_2': 'Description 2',
            'description_3': 'Description 3',
            'extrait_texte': 'Texte extrait',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        prix = cleaned_data.get('prix')
        prix_avant = cleaned_data.get('prix_avant')
        pourcentage = cleaned_data.get('pourcentage')
        remise = cleaned_data.get('remise')
        
        # 🔥 Logique de validation et calcul
        # 1. Si remise est directement fournie, on la garde
        if remise and remise > 0:
            if prix is not None and prix > 0:
                # Si on a prix et remise, on peut calculer prix_avant
                cleaned_data['prix_avant'] = prix + remise
                if pourcentage is None:
                    cleaned_data['pourcentage'] = (remise / (prix + remise)) * 100
        
        # 2. Validation prix vs prix_avant
        if prix is not None and prix_avant is not None:
            if prix >= prix_avant:
                raise forms.ValidationError(
                    "Le prix doit être inférieur au prix avant remise (prix < prix_avant)"
                )
            # Calcul automatique du pourcentage
            if pourcentage is None:
                cleaned_data['pourcentage'] = ((prix_avant - prix) / prix_avant) * 100
            # Calcul automatique de la remise
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
            # Au lieu de bloquer, on arrondit ou on accepte
            if pourcentage < 0:
                cleaned_data['pourcentage'] = 0
            elif pourcentage > 100:
                cleaned_data['pourcentage'] = 100
        
        return cleaned_data