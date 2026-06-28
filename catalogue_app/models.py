# catalogue_app/models.py
from django.db import models
from django.utils import timezone

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

# catalogue_app/models.py

class Produit(models.Model):
    catalogue = models.ForeignKey(Catalogue, on_delete=models.CASCADE, related_name='produits', verbose_name="Catalogue")
    
    # Champs extraits par YOLO
    nom = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nom (Affiché)")  # null=True ajouté
    nom_fr = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nom (FR)")  # null=True ajouté
    nom_ar = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nom (AR)")  # null=True ajouté
    marque = models.CharField(max_length=255, blank=True, null=True, verbose_name="Marque")  # null=True ajouté
    prix = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Prix (TND)")
    prix_avant = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Prix avant (TND)")
    pourcentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="%")
    description = models.TextField(blank=True, null=True, verbose_name="Description")  # null=True ajouté
    description_2 = models.TextField(blank=True, null=True, verbose_name="Description 2")  # null=True ajouté
    description_3 = models.TextField(blank=True, null=True, verbose_name="Description 3")  # null=True ajouté
    
    # Champs supplémentaires
    remise = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Remise (TND)")
    extrait_texte = models.TextField(blank=True, null=True, verbose_name="Texte extrait")  # null=True ajouté
    image_produit = models.ImageField(upload_to='produits/', null=True, blank=True, verbose_name="Image du produit")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de mise à jour")
    est_sauvegarde = models.BooleanField(default=False, verbose_name="Sauvegardé")
    class Meta:
        verbose_name = "Produit"
        verbose_name_plural = "Produits"
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        self.calculer_champs()
        super().save(*args, **kwargs)
    
    def calculer_champs(self):
        """Calcule automatiquement les champs manquants"""
        if self.remise and not self.prix and not self.prix_avant:
            return
            
        if self.prix is not None and self.prix_avant is not None and self.prix_avant > 0:
            self.remise = self.prix_avant - self.prix
            if self.prix_avant > 0:
                self.pourcentage = (self.remise / self.prix_avant) * 100
        elif self.prix is not None and self.pourcentage is not None and self.pourcentage > 0:
            self.prix_avant = self.prix / (1 - self.pourcentage / 100)
            self.remise = self.prix_avant - self.prix
        elif self.prix_avant is not None and self.pourcentage is not None and self.pourcentage > 0:
            self.prix = self.prix_avant * (1 - self.pourcentage / 100)
            self.remise = self.prix_avant - self.prix
    
    def __str__(self):
        return self.nom or f"Produit #{self.id}"