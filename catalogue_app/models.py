# catalogue_app/models.py
from django.db import models
from django.utils import timezone
from decimal import Decimal, InvalidOperation  
import re

class Enseigne(models.Model):
    """Modèle pour un enseigne avec choix prédéfinis"""
    
    ENSEIGNE_CHOICES = [
        ('MG', 'MG'),
        ('Carrefour', 'Carrefour'),
        ('Carrefour Market', 'Carrefour Market'),
        ('Carrefour Express', 'Carrefour Express'),
        ('Aziza', 'Aziza'),
        ('Anouar', 'Anouar'),
        ('Géant', 'Géant'),
        ('Monoprix', 'Monoprix'),
        ('autre', 'Autre'),
    ]
    
    nom = models.CharField(
        max_length=50, 
        choices=ENSEIGNE_CHOICES,
        default='autre',
        verbose_name="Nom de l'enseigne"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Enseigne"
        verbose_name_plural = "Enseignes"
        ordering = ['nom']
    
    def __str__(self):
        return self.get_nom_display()

class Catalogue(models.Model):
    enseigne = models.ForeignKey(Enseigne, on_delete=models.CASCADE, verbose_name="Enseigne")
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin")
    date_upload = models.DateTimeField(auto_now_add=True, verbose_name="Date d'upload")
    image_path = models.CharField(max_length=255, blank=True, null=True, verbose_name="Chemin de l'image")
    
    class Meta:
        unique_together = ['enseigne', 'date_debut', 'date_fin']
        verbose_name = "Catalogue"
        verbose_name_plural = "Catalogues"
        ordering = ['-date_upload']
    
    def __str__(self):
        return f"{self.enseigne.get_nom_display()} - {self.date_debut} à {self.date_fin}"

class Produit(models.Model):
    catalogue = models.ForeignKey(Catalogue, on_delete=models.CASCADE, related_name='produits', verbose_name="Catalogue")
    
    # Champs extraits par YOLO
    nom = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nom (Affiché)")
    nom_fr = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nom (FR)")
    nom_ar = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nom (AR)")
    marque = models.CharField(max_length=255, blank=True, null=True, verbose_name="Marque")
    prix = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Prix (TND)")
    prix_avant = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Prix avant (TND)")
    pourcentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="%")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    description_2 = models.TextField(blank=True, null=True, verbose_name="Description 2")
    description_3 = models.TextField(blank=True, null=True, verbose_name="Description 3")
    
    # Champs supplémentaires
    remise = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Remise (TND)")
    extrait_texte = models.TextField(blank=True, null=True, verbose_name="Texte extrait")
    image_produit = models.ImageField(upload_to='produits/', null=True, blank=True, verbose_name="Image du produit")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de mise à jour")
    est_sauvegarde = models.BooleanField(default=False, verbose_name="Sauvegardé")
    
    class Meta:
        verbose_name = "Produit"
        verbose_name_plural = "Produits"
        ordering = ['-created_at']
    
    def clean_decimal(self, value):
        """Nettoie une valeur décimale avant sauvegarde - NE JAMAIS PLANTER"""
        if value is None:
            return None
        if value == '':
            return None
        try:
            if isinstance(value, Decimal):
                # 🔥 Si la valeur est négative, on retourne None
                if value < 0:
                    return None
                return value
            if isinstance(value, (int, float)):
                # 🔥 Si la valeur est négative, on retourne None
                if value < 0:
                    return None
                return Decimal(str(value))
            if isinstance(value, str):
                # Nettoyer la chaîne : remplacer virgule par point, enlever espaces
                cleaned = value.strip().replace(',', '.').replace('\xa0', '')
                # Garder seulement les chiffres, point et moins
                cleaned = re.sub(r'[^0-9.\-]', '', cleaned)
                if not cleaned or cleaned == '':
                    return None
                if not re.search(r'\d', cleaned):
                    return None
                dec = Decimal(cleaned)
                # 🔥 Si la valeur est négative, on retourne None
                if dec < 0:
                    return None
                return dec
        except (ValueError, TypeError, InvalidOperation):
            return None
        return None
    
    def save(self, *args, **kwargs):
        # 🔥 Nettoyer TOUS les champs décimaux avant la sauvegarde
        self.prix = self.clean_decimal(self.prix)
        self.prix_avant = self.clean_decimal(self.prix_avant)
        self.pourcentage = self.clean_decimal(self.pourcentage)
        self.remise = self.clean_decimal(self.remise)
        
        # Appeler le calcul des champs
        try:
            self.calculer_champs()
        except:
            pass
        
        super().save(*args, **kwargs)
    
    def calculer_champs(self):
        """Calcule automatiquement les champs manquants - NE JAMAIS PLANTER"""
        try:
            prix = self.prix
            prix_avant = self.prix_avant
            pourcentage = self.pourcentage
            remise = self.remise
            
            if prix is None and prix_avant is None and pourcentage is None and remise is None:
                return
            
            if remise and not prix and not prix_avant:
                return
                
            if prix is not None and prix_avant is not None and prix_avant > 0:
                self.remise = prix_avant - prix
                if prix_avant > 0 and self.remise > 0:
                    self.pourcentage = (self.remise / prix_avant) * 100
                else:
                    self.remise = None
                    self.pourcentage = None
            elif prix is not None and pourcentage is not None and pourcentage > 0:
                self.prix_avant = prix / (1 - pourcentage / 100)
                self.remise = self.prix_avant - prix
            elif prix_avant is not None and pourcentage is not None and pourcentage > 0:
                self.prix = prix_avant * (1 - pourcentage / 100)
                self.remise = prix_avant - self.prix
        except:
            pass
    
    def __str__(self):
        return self.nom or f"Produit #{self.id}"