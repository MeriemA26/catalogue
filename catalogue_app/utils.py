# catalogue_app/utils.py
import os
import cv2
from decimal import Decimal
from django.conf import settings

# Importer les fonctions de pipeline
from .pipeline import process_catalogue_image, extract_price, extract_percentage, extract_text

class OCRProcessor:
    def __init__(self):
        self.models_dir = os.path.join(settings.BASE_DIR, 'catalogue_app', 'models')
        print(f"📁 Dossier des modèles: {self.models_dir}")
        
        # Vérifier que les modèles existent
        prod_model_path = os.path.join(self.models_dir, 'best_prod.pt')
        details_model_path = os.path.join(self.models_dir, 'best_details.pt')
        
        if os.path.exists(prod_model_path):
            print(f"✅ Modèle produit trouvé: {prod_model_path}")
        else:
            print(f"❌ Modèle produit non trouvé: {prod_model_path}")
            
        if os.path.exists(details_model_path):
            print(f"✅ Modèle détails trouvé: {details_model_path}")
        else:
            print(f"❌ Modèle détails non trouvé: {details_model_path}")
    
    def _clean_value(self, value):
        """Nettoie une valeur pour la conversion en Decimal"""
        if value is None:
            return None
        if isinstance(value, (int, float, Decimal)):
            return Decimal(str(value))
        if isinstance(value, str):
            # Enlever les caractères non numériques sauf le point et la virgule
            cleaned = ''.join(c for c in value if c.isdigit() or c in ['.', ','])
            if not cleaned:
                return None
            cleaned = cleaned.replace(',', '.')
            try:
                return Decimal(cleaned)
            except:
                return None
        return None
    
    def _clean_percentage(self, value):
        """Nettoie une valeur de pourcentage"""
        if value is None:
            return None
        if isinstance(value, (int, float, Decimal)):
            return Decimal(str(value))
        if isinstance(value, str):
            cleaned = ''.join(c for c in value if c.isdigit() or c in ['.', ','])
            if not cleaned:
                return None
            cleaned = cleaned.replace(',', '.')
            try:
                val = float(cleaned)
                if 1 <= val <= 100:
                    return Decimal(str(val))
                return None
            except:
                return None
        return None
    
    def _clean_description(self, text):
        """Nettoie une description pour enlever les caractères parasites"""
        if not text:
            return ""
        import re
        cleaned = re.sub(r'[^\w\s\u0600-\u06FF\.\,\-\(\)\:]+', ' ', text)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()
    
    def traiter_image_complete(self, image_path):
        """
        Traite une image complète avec les modèles YOLO
        """
        try:
            print(f"🔍 Traitement de l'image: {image_path}")
            
            # Appeler la fonction de pipeline
            produits = process_catalogue_image(
                image_path, 
                conf_product=0.5,
                conf_field=0.5,
                debug=False
            )
            
            print(f"📊 {len(produits)} produits détectés")
            
            # Convertir les données pour correspondre au format attendu par Django
            resultats = []
            for idx, produit in enumerate(produits):
                try:
                    # Nettoyer et convertir les valeurs
                    prix = self._clean_value(produit.get('prix'))
                    prix_avant = self._clean_value(produit.get('prix_avant'))
                    pourcentage = self._clean_percentage(produit.get('pourcentage'))
                    
                    # Gérer la remise
                    remise_value = produit.get('remise')
                    remise = None
                    if remise_value:
                        if isinstance(remise_value, str) and '%' in remise_value:
                            remise = None
                        else:
                            remise = self._clean_value(remise_value)
                    
                    # Nettoyer les descriptions
                    description = self._clean_description(produit.get('description', ''))
                    description_2 = self._clean_description(produit.get('description_2', ''))
                    description_3 = self._clean_description(produit.get('description_3', ''))
                    
                    # ⚠️ IMPORTANT: Récupérer les noms
                    nom_fr = produit.get('nom_fr', '').strip()
                    nom_ar = produit.get('nom_ar', '').strip()
                    
                    # Debug
                    print(f"\n🔹 Produit {idx+1}:")
                    print(f"  nom_fr (brut): '{produit.get('nom_fr', '')}'")
                    print(f"  nom_ar (brut): '{produit.get('nom_ar', '')}'")
                    print(f"  nom_fr apres strip: '{nom_fr}'")
                    print(f"  nom_ar apres strip: '{nom_ar}'")
                    
                    # Nom du produit - PRIORITÉ au nom français
                    if nom_fr:
                        nom_produit = nom_fr
                    elif nom_ar:
                        nom_produit = nom_ar
                    else:
                        nom_produit = f"Produit {idx + 1}"
                    
                    print(f"  Nom final: '{nom_produit}'")
                    print(f"  Description nettoyée: '{description[:50]}...'")
                    
                    resultats.append({
                        'id': produit.get('id', idx),
                        'nom': nom_produit,       # Pour l'affichage
                        'nom_fr': nom_fr,         # ⚠️ Nom FR exact
                        'nom_ar': nom_ar,         # ⚠️ Nom AR exact
                        'marque': produit.get('marque', ''),
                        'prix': prix,
                        'prix_avant': prix_avant,
                        'pourcentage': pourcentage,
                        'remise': remise,
                        'description': description,
                        'description_2': description_2,
                        'description_3': description_3,
                        'extrait_texte': f"Marque: {produit.get('marque', '')} - Description: {description}",
                        'product_image_b64': produit.get('product_image_b64'),
                    })
                    
                except Exception as e:
                    print(f"❌ Erreur lors du traitement du produit {idx}: {e}")
                    continue
            
            return resultats
            
        except Exception as e:
            print(f"❌ Erreur lors du traitement de l'image: {e}")
            import traceback
            traceback.print_exc()
            return []
    
# catalogue_app/utils.py - extraire_texte_fallback CORRIGÉ

    def extraire_texte_fallback(self, image_path):
        """Méthode de fallback utilisant EasyOCR avec les deux readers"""
        try:
            from .pipeline import get_ocr_readers
            reader_latin, reader_ar = get_ocr_readers()
            
            image = cv2.imread(image_path)
            if image is None:
                return ""
            
            image_big = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(image_big, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 🔥 Essayer avec le reader latin
            results_latin = reader_latin.readtext(thresh, detail=0)
            texts_latin = ' '.join(results_latin) if results_latin else ""
            
            # 🔥 Essayer avec le reader arabe
            results_ar = reader_ar.readtext(thresh, detail=0)
            texts_ar = ' '.join(results_ar) if results_ar else ""
            
            # 🔥 Combiner les résultats
            combined = texts_latin + " " + texts_ar
            
            # 🔥 Nettoyer les doublons approximatifs
            # On garde les deux car ils peuvent être différents
            return combined.strip()
            
        except Exception as e:
            print(f"❌ Erreur fallback: {e}")
            return ""
    
    def detecter_prix_remise(self, texte):
        """Détecte les prix, pourcentages et remises dans le texte (fallback)"""
        import re
        
        produits = []
        
        patterns = {
            'prix': r'(\d+[.,]\d{2})\s*€',
            'prix_avant': r'(?:avant|ancien|au lieu de)\s*(\d+[.,]\d{2})\s*€',
            'pourcentage': r'(-?\d+[.,]?\d*)\s*%',
            'remise': r'remise\s*:\s*(\d+[.,]\d{2})\s*€',
        }
        
        prix_trouves = re.findall(patterns['prix'], texte)
        prix_avant_trouves = re.findall(patterns['prix_avant'], texte)
        pourcentages_trouves = re.findall(patterns['pourcentage'], texte)
        remises_trouves = re.findall(patterns['remise'], texte)
        
        texte_clean = self._clean_description(texte)
        
        produit = {
            'nom': 'Produit détecté',
            'nom_fr': '',
            'nom_ar': '',
            'marque': '',
            'prix': self._clean_value(prix_trouves[0] if prix_trouves else None),
            'prix_avant': self._clean_value(prix_avant_trouves[0] if prix_avant_trouves else None),
            'pourcentage': self._clean_percentage(pourcentages_trouves[0] if pourcentages_trouves else None),
            'remise': self._clean_value(remises_trouves[0] if remises_trouves else None),
            'description': texte_clean[:200],
            'description_2': '',
            'description_3': '',
            'extrait_texte': texte_clean[:500]
        }
        
        if produit['prix'] is not None and produit['prix_avant'] is not None:
            if produit['prix_avant'] > 0:
                produit['remise'] = produit['prix_avant'] - produit['prix']
                produit['pourcentage'] = (produit['remise'] / produit['prix_avant']) * 100
        
        if produit['prix'] is not None and produit['prix_avant'] is None and produit['pourcentage'] is not None:
            if produit['pourcentage'] > 0:
                produit['prix_avant'] = produit['prix'] / (1 - produit['pourcentage'] / 100)
                produit['remise'] = produit['prix_avant'] - produit['prix']
        
        produits.append(produit)
        return produits