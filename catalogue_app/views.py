# catalogue_app/views.py - Version sans logs avec caractères spéciaux
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import os
import json
import logging
import base64
from decimal import Decimal
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import time
from .models import Enseigne, Catalogue, Produit
from .forms import UploadForm, ProduitForm
from .utils import OCRProcessor

# Configuration du logging - Désactiver complètement
logging.disable(logging.CRITICAL)
logger = logging.getLogger(__name__)


def index(request):
    """Page d'accueil"""
    context = {
        'enseignes': Enseigne.objects.all(),
        'total_produits': Produit.objects.count(),
        'total_catalogues': Catalogue.objects.count(),
    }
    return render(request, 'index.html', context)


def upload(request):
    """Page d'upload avec traitement OCR"""
    # Initialiser last_uploaded_image en dehors des conditions
    last_uploaded_image = request.session.get('last_uploaded_image', None)
    
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                enseigne = form.cleaned_data['enseigne']
                date_debut = form.cleaned_data['date_debut']
                date_fin = form.cleaned_data['date_fin']
                image = form.cleaned_data['image']
                
                # Créer ou récupérer le catalogue
                catalogue, created = Catalogue.objects.get_or_create(
                    enseigne=enseigne,
                    date_debut=date_debut,
                    date_fin=date_fin,
                    defaults={'date_upload': timezone.now()}
                )
                
                # Sauvegarder l'image du catalogue
                image_name = f'{enseigne.nom}_{date_debut}_{date_fin}_{image.name}'
                image_path = default_storage.save(
                    f'catalogues/{image_name}',
                    ContentFile(image.read())
                )
                catalogue.image_path = image_path
                catalogue.save()
                
                # Traitement OCR avec les modèles YOLO
                ocr = OCRProcessor()
                full_path = os.path.join(settings.MEDIA_ROOT, image_path)
                
                # Vérifier que l'image existe
                if not os.path.exists(full_path):
                    messages.error(request, "Erreur: L'image n'a pas ete sauvegardee correctement.")
                    return redirect('upload')
                
                # Traiter l'image complète avec YOLO
                produits_data = []
                try:
                    produits_data = ocr.traiter_image_complete(full_path)
                    
                    # Afficher les données extraites pour debug (uniquement en console)
                    print("\n" + "=" * 80)
                    print("DONNEES EXTRAITES PAR L'OCR:")
                    print("=" * 80)
                    for i, data in enumerate(produits_data):
                        print(f"\nProduit {i+1}:")
                        print(f"  Nom (FR): {data.get('nom', 'NON TROUVE')}")
                        print(f"  Nom (AR): {data.get('nom_ar', 'NON TROUVE')}")
                        print(f"  Marque: {data.get('marque', 'NON TROUVE')}")
                        print(f"  Prix: {data.get('prix', 'NON TROUVE')}")
                        print(f"  Prix Avant: {data.get('prix_avant', 'NON TROUVE')}")
                        print(f"  %: {data.get('pourcentage', 'NON TROUVE')}")
                        print(f"  Remise: {data.get('remise', 'NON TROUVE')}")
                        print(f"  Description: {data.get('description', 'NON TROUVE')[:50]}...")
                        print(f"  Description 2: {data.get('description_2', 'NON TROUVE')[:50]}...")
                        print(f"  Description 3: {data.get('description_3', 'NON TROUVE')[:50]}...")
                    print("=" * 80 + "\n")
                    
                except Exception as e:
                    print(f"Erreur YOLO: {e}")
                    messages.warning(request, f"Erreur avec les modeles YOLO: {str(e)}")
                
                # Si aucun produit détecté, utiliser le fallback EasyOCR
                if not produits_data:
                    print("Utilisation du mode fallback (EasyOCR)")
                    messages.warning(request, "Aucun produit detecte avec les modeles YOLO, utilisation du mode fallback")
                    
                    try:
                        texte = ocr.extraire_texte_fallback(full_path)
                        if texte:
                            produits_data = ocr.detecter_prix_remise(texte)
                            print(f"Produits detectes avec fallback: {len(produits_data)}")
                        else:
                            messages.warning(request, "Aucun texte detecte dans l'image.")
                    except Exception as e:
                        print(f"Erreur fallback: {e}")
                        messages.error(request, f"Erreur lors de l'extraction du texte: {str(e)}")
                
                # Créer les produits dans la base de données
                produits_crees = []
                if produits_data:
                    for idx, data in enumerate(produits_data):
                        try:
                            # Sauvegarder l'image du produit si disponible
                            image_produit = None
                            if 'product_image_b64' in data and data['product_image_b64']:
                                try:
                                    image_data = base64.b64decode(data['product_image_b64'])
                                    timestamp = int(timezone.now().timestamp())
                                    filename = f'produit_{catalogue.id}_{idx}_{timestamp}.jpg'
                                    image_produit = ContentFile(image_data, filename)
                                    print(f"Image produit {idx} decodee avec succes")
                                except Exception as e:
                                    print(f"Erreur decodage image produit {idx}: {e}")
                            
                            # Récupérer les noms exacts (peuvent être vides)
                            nom_fr = data.get('nom_fr', '').strip()
                            nom_ar = data.get('nom_ar', '').strip()
                            
                            # nom = nom_fr s'il existe, sinon nom_ar s'il existe, sinon générique
                            if nom_fr:
                                nom_affiche = nom_fr
                            elif nom_ar:
                                nom_affiche = nom_ar
                            else:
                                nom_affiche = f"Produit {idx + 1}"
                            
                            # Nettoyer les descriptions
                            description = data.get('description', '') or ''
                            description_2 = data.get('description_2', '') or ''
                            description_3 = data.get('description_3', '') or ''
                            
                            if not description and (description_2 or description_3):
                                description = description_2
                                description_2 = description_3
                                description_3 = ''
                            
                            remise_val = data.get('remise')
                            if isinstance(remise_val, str) and '%' in remise_val:
                                remise_val = None
                            
                            produit = Produit(
                                catalogue=catalogue,
                                nom=nom_affiche,
                                nom_fr=nom_fr if nom_fr else None,
                                nom_ar=nom_ar if nom_ar else None,
                                marque=data.get('marque', '') if data.get('marque') else None,
                                prix=data.get('prix'),
                                prix_avant=data.get('prix_avant'),
                                pourcentage=data.get('pourcentage'),
                                remise=remise_val if remise_val else None,
                                description=description if description else None,
                                description_2=description_2 if description_2 else None,
                                description_3=description_3 if description_3 else None,
                                extrait_texte=data.get('extrait_texte', '') if data.get('extrait_texte') else None,
                                image_produit=image_produit,
                            )
                            produit.save()
                            produits_crees.append(produit)
                            print(f"Produit cree: ID {produit.id}")
                            
                        except Exception as e:
                            print(f"Erreur creation produit {idx}: {e}")
                            import traceback
                            traceback.print_exc()
                            continue
                
                if produits_crees:
                    messages.success(request, f'Upload reussi ! {len(produits_crees)} produits detectes et sauvegardes.')
                else:
                    messages.warning(request, 'Aucun produit detecte dans l\'image. Veuillez verifier la qualite de l\'image.')
                
                # Sauvegarder l'image dans la session
                request.session['last_uploaded_image'] = os.path.join(settings.MEDIA_URL, image_path)
                last_uploaded_image = request.session['last_uploaded_image']
                
            except Exception as e:
                print(f"Erreur generale: {e}")
                messages.error(request, f"Erreur lors du traitement: {str(e)}")
                import traceback
                traceback.print_exc()
            
            return redirect('upload')
    else:
        form = UploadForm()

    # Récupérer les produits non sauvegardés du dernier catalogue
    catalogues_recents = {}
    produits_non_sauvegardes = 0
    
    for enseigne in Enseigne.objects.all():
        dernier_catalogue = Catalogue.objects.filter(enseigne=enseigne).order_by('-date_upload').first()
        if dernier_catalogue:
            produits_non_sauvegardes_catalogue = dernier_catalogue.produits.filter(est_sauvegarde=False)
            if produits_non_sauvegardes_catalogue.exists():
                catalogues_recents[enseigne.nom] = produits_non_sauvegardes_catalogue
                produits_non_sauvegardes += produits_non_sauvegardes_catalogue.count()
    
    total_produits = Produit.objects.count()
    produits_sauvegardes = Produit.objects.filter(est_sauvegarde=True).count()
    produits_non_sauvegardes = Produit.objects.filter(est_sauvegarde=False).count()
    
    context = {
        'form': form,
        'catalogues_recents': catalogues_recents,
        'enseignes': Enseigne.objects.all(),
        'total_catalogues': Catalogue.objects.count(),
        'total_produits': total_produits,
        'produits_sauvegardes': produits_sauvegardes,
        'produits_non_sauvegardes': produits_non_sauvegardes,
        'last_uploaded_image': last_uploaded_image,
    }
    return render(request, 'upload.html', context)


def edit_product(request, product_id):
    """Éditer un produit individuel"""
    produit = get_object_or_404(Produit, id=product_id)
    
    if request.method == 'POST':
        form = ProduitForm(request.POST, instance=produit)
        if form.is_valid():
            try:
                produit = form.save(commit=False)
                produit.save()
                messages.success(request, 'Produit mis a jour avec succes !')
                return redirect('edit_product', product_id=produit.id)
            except Exception as e:
                messages.error(request, f"Erreur lors de la mise a jour: {str(e)}")
        else:
            messages.error(request, "Le formulaire contient des erreurs.")
    else:
        form = ProduitForm(instance=produit)
    
    context = {
        'form': form,
        'produit': produit,
    }
    return render(request, 'edit_product.html', context)


@csrf_exempt
def update_product_field(request):
    """API pour mettre à jour un champ d'un produit en AJAX"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            field_name = data.get('field_name')
            field_value = data.get('field_value')
            
            if not product_id or not field_name:
                return JsonResponse({'success': False, 'error': 'Parametres manquants'})
            
            produit = get_object_or_404(Produit, id=product_id)
            
            if field_name in ['prix', 'prix_avant', 'pourcentage', 'remise']:
                if field_value:
                    try:
                        setattr(produit, field_name, Decimal(str(field_value)))
                    except:
                        setattr(produit, field_name, None)
                else:
                    setattr(produit, field_name, None)
                
                produit.save()
                
                return JsonResponse({
                    'success': True,
                    'prix': str(produit.prix) if produit.prix else None,
                    'prix_avant': str(produit.prix_avant) if produit.prix_avant else None,
                    'pourcentage': str(produit.pourcentage) if produit.pourcentage else None,
                    'remise': str(produit.remise) if produit.remise else None,
                })
            
            return JsonResponse({'success': False, 'error': 'Champ non modifiable'})
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'JSON invalide'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Methode non autorisee'})


def save_selected_products(request):
    """Sauvegarder les produits sélectionnés"""
    if request.method == 'POST':
        product_ids = request.POST.getlist('selected_products')
        if not product_ids:
            messages.warning(request, 'Aucun produit selectionne.')
            return redirect('upload')
        
        try:
            produits = Produit.objects.filter(id__in=product_ids)
            count = produits.count()
            
            if count == 0:
                messages.warning(request, 'Produits non trouves.')
                return redirect('upload')
            
            produits.update(est_sauvegarde=True)
            
            restants = Produit.objects.filter(est_sauvegarde=False).count()
            
            if restants == 0:
                if 'last_uploaded_image' in request.session:
                    del request.session['last_uploaded_image']
                messages.info(request, 'Tous les produits sont maintenant sauvegardes !')
            else:
                messages.success(request, f'{count} produits sauvegardes ! Il reste {restants} produit(s) en attente.')
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la sauvegarde: {str(e)}")
        
        return redirect('upload')
    return redirect('upload')


def save_all_products(request):
    """Sauvegarder tous les produits et rediriger vers product_list"""
    if request.method == 'POST':
        try:
            produits = Produit.objects.filter(est_sauvegarde=False)
            count = produits.count()
            
            if count == 0:
                messages.info(request, 'Aucun nouveau produit a sauvegarder.')
                return redirect('product_list')
            
            produits.update(est_sauvegarde=True)
            
            if 'last_uploaded_image' in request.session:
                del request.session['last_uploaded_image']
            
            messages.success(request, f'{count} produits sauvegardes !')
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la sauvegarde: {str(e)}")
        
        return redirect('product_list')
    return redirect('upload')


def delete_selected_products(request):
    """Supprimer les produits sélectionnés"""
    if request.method == 'POST':
        product_ids = request.POST.getlist('selected_products')
        if not product_ids:
            messages.warning(request, 'Aucun produit selectionne.')
            return redirect('upload')
        
        try:
            produits = Produit.objects.filter(id__in=product_ids)
            count = produits.count()
            
            if count == 0:
                messages.warning(request, 'Produits non trouves.')
                return redirect('upload')
            
            for produit in produits:
                if produit.image_produit:
                    try:
                        image_path = os.path.join(settings.MEDIA_ROOT, str(produit.image_produit))
                        if os.path.exists(image_path):
                            os.remove(image_path)
                    except Exception as e:
                        pass
            
            produits.delete()
            
            restants = Produit.objects.filter(est_sauvegarde=False).count()
            
            if restants == 0:
                if 'last_uploaded_image' in request.session:
                    del request.session['last_uploaded_image']
                messages.info(request, 'Tous les produits ont ete supprimes.')
            else:
                messages.success(request, f'{count} produits supprimes ! Il reste {restants} produit(s).')
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression: {str(e)}")
        
        return redirect('upload')
    return redirect('upload')


def delete_all_products(request):
    """Supprimer tous les produits non sauvegardés"""
    if request.method == 'POST':
        try:
            produits = Produit.objects.filter(est_sauvegarde=False)
            count = produits.count()
            
            if count == 0:
                messages.info(request, 'Aucun produit a supprimer.')
                return redirect('upload')
            
            for produit in produits:
                if produit.image_produit:
                    try:
                        image_path = os.path.join(settings.MEDIA_ROOT, str(produit.image_produit))
                        if os.path.exists(image_path):
                            os.remove(image_path)
                    except Exception as e:
                        pass
            
            produits.delete()
            
            if 'last_uploaded_image' in request.session:
                del request.session['last_uploaded_image']
            
            messages.success(request, f'{count} produits supprimes !')
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression: {str(e)}")
        
        return redirect('upload')
    return redirect('upload')


def product_list(request):
    """Liste des produits du dernier catalogue sauvegardé"""
    
    # Récupérer le dernier catalogue QUI A DES PRODUITS SAUVEGARDÉS
    dernier_catalogue = None
    produits = []
    
    # Chercher le dernier catalogue qui a au moins un produit sauvegardé
    for catalogue in Catalogue.objects.order_by('-date_upload'):
        produits_sauvegardes = catalogue.produits.filter(est_sauvegarde=True)
        if produits_sauvegardes.exists():
            dernier_catalogue = catalogue
            produits = produits_sauvegardes
            break
    
    if dernier_catalogue:
        context = {
            'catalogue': dernier_catalogue,
            'produits': produits,
            'total_produits': produits.count(),
            'has_products': True,
        }
    else:
        context = {
            'catalogue': None,
            'produits': [],
            'total_produits': 0,
            'has_products': False,
        }
    
    return render(request, 'product_list.html', context)

def get_product_details(request, product_id):
    """API pour récupérer les détails d'un produit (AJAX)"""
    if request.method == 'GET':
        try:
            produit = get_object_or_404(Produit, id=product_id)
            data = {
                'id': produit.id,
                'nom': produit.nom,
                'prix': str(produit.prix) if produit.prix else None,
                'prix_avant': str(produit.prix_avant) if produit.prix_avant else None,
                'pourcentage': str(produit.pourcentage) if produit.pourcentage else None,
                'remise': str(produit.remise) if produit.remise else None,
                'description': produit.description,
                'extrait_texte': produit.extrait_texte,
                'est_sauvegarde': produit.est_sauvegarde,
                'image_url': produit.image_produit.url if produit.image_produit else None,
            }
            return JsonResponse({'success': True, 'data': data})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Methode non autorisee'})


def get_catalogue_image(request, catalogue_id):
    """API pour récupérer l'image du catalogue"""
    if request.method == 'GET':
        try:
            catalogue = get_object_or_404(Catalogue, id=catalogue_id)
            if catalogue.image_path:
                image_url = os.path.join(settings.MEDIA_URL, catalogue.image_path)
                return JsonResponse({'success': True, 'image_url': image_url})
            return JsonResponse({'success': False, 'error': 'Aucune image'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Methode non autorisee'})

def _clean_value(self, value):
        """Nettoie une valeur pour la conversion en Decimal"""
        if value is None:
            return None
        if isinstance(value, (int, float, Decimal)):
            # Vérifier que le prix n'est pas aberrant
            val = float(value)
            if val > 1000:  # Si le prix > 1000, c'est probablement une erreur OCR
                print(f"⚠️ Prix aberrant détecté: {val}, ignoré")
                return None
            return Decimal(str(value))
        if isinstance(value, str):
            # Enlever les caractères non numériques sauf le point et la virgule
            cleaned = ''.join(c for c in value if c.isdigit() or c in ['.', ','])
            if not cleaned:
                return None
            cleaned = cleaned.replace(',', '.')
            try:
                val = float(cleaned)
                # Vérifier que le prix n'est pas aberrant
                if val > 1000:
                    print(f"⚠️ Prix aberrant détecté: {val}, ignoré")
                    return None
                return Decimal(cleaned)
            except:
                return None
        return None
def get_recent_products(request):
    """Récupère les produits non sauvegardés récents"""
    produits = Produit.objects.filter(est_sauvegarde=False).order_by('-created_at')[:10]
    data = []
    for p in produits:
        data.append({
            'id': p.id,
            'nom': p.nom,
            'nom_fr': p.nom_fr,
            'nom_ar': p.nom_ar,
            'marque': p.marque,
            'prix': str(p.prix) if p.prix else None,
            'prix_avant': str(p.prix_avant) if p.prix_avant else None,
            'pourcentage': str(p.pourcentage) if p.pourcentage else None,
            'description': p.description,
            'description_2': p.description_2,
            'description_3': p.description_3,
            'image_url': p.image_produit.url if p.image_produit else None,
        })
    return JsonResponse({'products': data})