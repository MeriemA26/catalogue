from django.db import models
from django.utils import timezone
from decimal import Decimal, InvalidOperation 
from django.contrib.auth.models import User 
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
    note = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="Note (ex: Saint Valentin, Noël, Eid...)"
    )
    class Meta:
        unique_together = ['enseigne', 'date_debut', 'date_fin']
        verbose_name = "Catalogue"
        verbose_name_plural = "Catalogues"
        ordering = ['-date_upload']
    def __str__(self):
        note_str = f" - {self.note}" if self.note else ""
        return f"{self.enseigne.get_nom_display()} - {self.date_debut} à {self.date_fin}{note_str}"


class CatalogueImage(models.Model):
    """Une ligne par image/page appartenant à un catalogue (persistant en base)."""
    catalogue = models.ForeignKey(
        Catalogue, on_delete=models.CASCADE, related_name='images', verbose_name="Catalogue"
    )
    chemin = models.CharField(max_length=255, verbose_name="Chemin de l'image")
    ordre = models.PositiveIntegerField(default=0, verbose_name="Ordre (page)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ordre', 'created_at']
        verbose_name = "Image du catalogue"
        verbose_name_plural = "Images du catalogue"

    def __str__(self):
        return f"{self.catalogue} - page {self.ordre + 1}"
    
class Produit(models.Model):
    catalogue = models.ForeignKey(Catalogue, on_delete=models.CASCADE, related_name='produits', verbose_name="Catalogue")

    cree_par = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='produits_crees', verbose_name="Créé par"
    )
    modifie_par = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='produits_modifies', verbose_name="Modifié par"
    )

    # Champs extraits par YOLO
    nom = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nom (Affiché)")
    nom_fr = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nom (FR)")
    nom_ar = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nom (AR)")
    marque = models.CharField(max_length=255, blank=True, null=True, verbose_name="Marque")
    prix = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Prix (TND)")
    prix_avant = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Prix avant (TND)")
    pourcentage = models.DecimalField(max_digits=5, decimal_places=0, null=True, blank=True, verbose_name="%")
    desc_1 = models.TextField(blank=True, null=True, verbose_name="Desc 1")
    desc_2 = models.TextField(blank=True, null=True, verbose_name="Desc 2")
    desc_3 = models.TextField(blank=True, null=True, verbose_name="Desc 3")
    note_1 = models.TextField(blank=True, null=True, verbose_name="Note 1")
    note_2 = models.TextField(blank=True, null=True, verbose_name="Note 2")
    
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
                # Si la valeur est négative, on retourne None
                if value < 0:
                    return None
                return value
            if isinstance(value, (int, float)):
                #  Si la valeur est négative, on retourne None
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
                #  Si la valeur est négative, on retourne None
                if dec < 0:
                    return None
                return dec
        except (ValueError, TypeError, InvalidOperation):
            return None
        return None
    
    def save(self, *args, **kwargs):
        #  Nettoyer TOUS les champs décimaux avant la sauvegarde
        self.prix = self.clean_decimal(self.prix)
        self.prix_avant = self.clean_decimal(self.prix_avant)
        self.pourcentage = self.clean_decimal(self.pourcentage)
        self.remise = self.clean_decimal(self.remise)
        
        #  Le calcul automatique des champs manquants ne s'applique QU'À LA CRÉATION
        # (juste après l'extraction OCR/YOLO, quand certains champs sont encore vides).
        # Lors d'une modification (edit_product), on enregistre EXACTEMENT ce qui a été
        # saisi/validé dans le formulaire, sans recalcul automatique derrière.
        est_creation = self.pk is None
        if est_creation:
            try:
                self.calculer_champs()
            except:
                pass
        
        super().save(*args, **kwargs)
    
    def calculer_champs(self):
        """Calcule automatiquement les champs manquants - NE JAMAIS PLANTER
         Ne remplace JAMAIS une valeur déjà saisie/présente : ne calcule QUE ce qui est None.
        """
        try:
            prix = self.prix
            prix_avant = self.prix_avant
            pourcentage = self.pourcentage
            remise = self.remise
            
            if prix is None and prix_avant is None and pourcentage is None and remise is None:
                return
            
            if remise and not prix and not prix_avant:
                return
            
            # Cas 1 : prix + prix_avant connus -> déduire remise/pourcentage SEULEMENT s'ils sont vides
            if prix is not None and prix_avant is not None and prix_avant > 0:
                if remise is None:
                    calc_remise = prix_avant - prix
                    if calc_remise > 0:
                        self.remise = calc_remise
                        if pourcentage is None:
                            self.pourcentage = round((self.remise / prix_avant) * 100)
                # Si remise était déjà fournie par l'utilisateur, on n'y touche pas
                
            # Cas 2 : prix + pourcentage connus, prix_avant manquant -> le déduire
            elif prix is not None and pourcentage is not None and pourcentage > 0:
                if prix_avant is None:
                    self.prix_avant = prix / (1 - pourcentage / 100)
                    if remise is None:
                        self.remise = self.prix_avant - prix
                        
            # Cas 3 : prix_avant + pourcentage connus, prix manquant -> le déduire
            elif prix_avant is not None and pourcentage is not None and pourcentage > 0:
                if prix is None:
                    self.prix = prix_avant * (1 - pourcentage / 100)
                    if remise is None:
                        self.remise = prix_avant - self.prix
        except:
            pass
    
    def __str__(self):
        return self.nom or f"Produit #{self.id}"

class JournalAction(models.Model):
    ACTION_CHOICES = [
        ('ajout', 'Ajout'),
        ('modification', 'Modification'),
        ('suppression', 'Suppression'),
    ]
    utilisateur = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='actions',
        verbose_name="Utilisateur"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    produit_nom = models.CharField(max_length=255, blank=True, null=True)
    catalogue_info = models.CharField(max_length=255, blank=True, null=True)
    catalogue = models.ForeignKey(
        Catalogue, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='actions_journal', verbose_name="Catalogue"
    )
    date_action = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_action']

    def __str__(self):
        return f"{self.get_action_display()} - {self.produit_nom} par {self.utilisateur}"