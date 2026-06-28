# catalogue_app/forms.py
from django import forms
from .models import Produit, Catalogue, Enseigne

class UploadForm(forms.Form):
    enseigne = forms.ModelChoiceField(
        queryset=Enseigne.objects.all(), 
        empty_label="Sélectionnez une enseigne",
        widget=forms.Select(attrs={'class': 'form-control'})
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
        fields = ['nom', 'prix', 'prix_avant', 'pourcentage', 'remise', 'description', 'extrait_texte']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du produit'}),
            'prix': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'prix_avant': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'pourcentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'remise': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Description'}),
            'extrait_texte': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Texte extrait par OCR'}),
        }
        labels = {
            'nom': 'Nom du produit',
            'prix': 'Prix',
            'prix_avant': 'Prix avant remise',
            'pourcentage': 'Pourcentage (%)',
            'remise': 'Remise (€)',
            'description': 'Description',
            'extrait_texte': 'Texte extrait',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        prix = cleaned_data.get('prix')
        prix_avant = cleaned_data.get('prix_avant')
        pourcentage = cleaned_data.get('pourcentage')
        remise = cleaned_data.get('remise')
        
        # Si remise est directement fournie, on la garde
        if remise and not prix and not prix_avant:
            return cleaned_data
        
        # Validation des données
        if prix is not None and prix_avant is not None:
            if prix >= prix_avant:
                raise forms.ValidationError("Le prix doit être inférieur au prix avant remise")
        
        return cleaned_data