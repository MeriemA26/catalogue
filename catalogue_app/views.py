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


def upload_stream(request):
    """
    Vue SSE : reçoit l'image uploadée, lance le pipeline produit par produit,
    et envoie chaque produit au client dès qu'il est prêt via Server-Sent Events.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST requis'}, status=405)

    form = UploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({'error': str(form.errors)}, status=400)

    enseigne    = form.cleaned_data['enseigne']
    date_debut  = form.cleaned_data['date_debut']
    date_fin    = form.cleaned_data['date_fin']
    image       = form.cleaned_data['image']

    # Créer ou récupérer le catalogue
    catalogue, _ = Catalogue.objects.get_or_create(
        enseigne=enseigne,
        date_debut=date_debut,
        date_fin=date_fin,
        defaults={'date_upload': timezone.now()}
    )

    # Sauvegarder l'image catalogue
    image_name = f'{enseigne.nom}_{date_debut}_{date_fin}_{image.name}'
    image_path = default_storage.save(
        f'catalogues/{image_name}',
        ContentFile(image.read())
    )
    catalogue.image_path = image_path
    catalogue.save()

    full_path = os.path.join(settings.MEDIA_ROOT, image_path)
    media_image_url = os.path.join(settings.MEDIA_URL, image_path)

    def event_stream():
        # Sauvegarder l'URL de l'image en session via un signal JSON spécial
        yield f"data: {json.dumps({'type': 'catalogue', 'image_url': media_image_url, 'catalogue_id': catalogue.id})}\n\n"

        ocr = OCRProcessor()

        try:
            from .pipeline import (
                get_product_model, get_field_model, get_ocr_readers,
                FIELD_CLASS_MAP, image_to_base64,
                extract_price, extract_percentage, extract_text,
                _detect_language
            )
            import cv2, torch, re, base64 as b64

            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            product_model = get_product_model()
            field_model   = get_field_model()
            reader_latin, reader_ar = get_ocr_readers()

            image_cv = cv2.imread(full_path)
            if image_cv is None:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Impossible de lire l image'})}\n\n"
                return

            product_results = product_model(full_path, conf=0.5, verbose=False, device=device)[0]
            total = len(product_results.boxes)
            yield f"data: {json.dumps({'type': 'total', 'count': total})}\n\n"

            if total == 0:
                yield f"data: {json.dumps({'type': 'done', 'count': 0})}\n\n"
                return

            for idx, box in enumerate(product_results.boxes):
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                crop = image_cv[y1:y2, x1:x2]
                if crop.size == 0:
                    continue

                data = {
                    'nom_fr': '', 'nom_ar': '', 'marque': '',
                    'prix': None, 'prix_avant': None, 'pourcentage': None,
                    'remise': '', 'description': '', 'description_2': '', 'description_3': '',
                    'product_image_b64': image_to_base64(crop),
                }

                field_results = field_model.predict(crop, conf=0.5, device=device, verbose=False)[0]
                field_names   = field_results.names
                extracted_pct = extracted_prix = extracted_prix_avant = None

                for fbox, fcls in zip(field_results.boxes.xyxy.cpu().numpy(), field_results.boxes.cls.cpu().numpy()):
                    fx1, fy1, fx2, fy2 = map(int, fbox)
                    class_name = field_names[int(fcls)]
                    roi = crop[fy1:fy2, fx1:fx2]
                    if roi.size == 0:
                        continue
                    target = FIELD_CLASS_MAP.get(class_name)
                    if target is None:
                        continue

                    if class_name == 'product_AR':
                        data['nom_ar'] = extract_text(roi, reader_ar)
                    elif class_name == 'product_name':
                        data['nom_fr'] = extract_text(roi, reader_latin)
                    elif class_name == 'brand':
                        v = extract_text(roi, reader_latin)
                        data['marque'] = v or extract_text(roi, reader_ar)
                    elif class_name == 'price':
                        v = extract_price(roi)
                        if v:
                            data['prix'] = float(v)
                            extracted_prix = float(v)
                    elif class_name == 'price_before':
                        v = extract_price(roi)
                        if v:
                            data['prix_avant'] = float(v)
                            extracted_prix_avant = float(v)
                    elif class_name == 'pct':
                        v = extract_percentage(roi)
                        if v:
                            data['pourcentage'] = float(v)
                            extracted_pct = float(v)
                    elif class_name in ('description', 'description2', 'description3'):
                        v = extract_text(roi, reader_latin) or extract_text(roi, reader_ar)
                        if v:
                            v = re.sub(r'[^\w\s\u0600-\u06FF\.\,\-\(\)\:]+', ' ', v)
                            v = re.sub(r'\s+', ' ', v).strip()
                        key = {'description': 'description', 'description2': 'description_2', 'description3': 'description_3'}[class_name]
                        data[key] = v or ''

                # Calcul prix
                if extracted_pct and 1 <= extracted_pct <= 100:
                    data['pourcentage'] = extracted_pct
                    if extracted_prix:
                        data['prix_avant'] = round(extracted_prix / (1 - extracted_pct / 100), 3)
                    elif extracted_prix_avant:
                        data['prix'] = round(extracted_prix_avant * (1 - extracted_pct / 100), 3)
                elif extracted_prix and extracted_prix_avant and extracted_prix_avant > 0:
                    if extracted_prix < extracted_prix_avant:
                        pct = round((1 - extracted_prix / extracted_prix_avant) * 100, 2)
                        if 1 <= pct <= 100:
                            data['pourcentage'] = pct

                # Créer le produit en DB
                nom_fr = data['nom_fr'].strip()
                nom_ar = data['nom_ar'].strip()
                nom_affiche = nom_fr or nom_ar or f"Produit {idx + 1}"

                description   = data.get('description', '') or ''
                description_2 = data.get('description_2', '') or ''
                description_3 = data.get('description_3', '') or ''
                if not description and (description_2 or description_3):
                    description, description_2, description_3 = description_2, description_3, ''

                remise_val = data.get('remise')
                if isinstance(remise_val, str) and '%' in remise_val:
                    remise_val = None

                image_produit = None
                if data.get('product_image_b64'):
                    try:
                        img_data = b64.b64decode(data['product_image_b64'])
                        ts = int(timezone.now().timestamp())
                        image_produit = ContentFile(img_data, f'produit_{catalogue.id}_{idx}_{ts}.jpg')
                    except Exception:
                        pass

                produit = Produit(
                    catalogue=catalogue,
                    nom=nom_affiche,
                    nom_fr=nom_fr or None,
                    nom_ar=nom_ar or None,
                    marque=data.get('marque') or None,
                    prix=data.get('prix'),
                    prix_avant=data.get('prix_avant'),
                    pourcentage=data.get('pourcentage'),
                    remise=remise_val or None,
                    description=description or None,
                    description_2=description_2 or None,
                    description_3=description_3 or None,
                    extrait_texte=f"Marque: {data.get('marque','')} - {description}" or None,
                    image_produit=image_produit,
                )
                produit.save()

                # Préparer la payload SSE
                payload = {
                    'type': 'product',
                    'index': idx + 1,
                    'id': produit.id,
                    'nom': nom_affiche,
                    'nom_fr': nom_fr,
                    'nom_ar': nom_ar,
                    'marque': data.get('marque', ''),
                    'prix': str(produit.prix) if produit.prix is not None else '',
                    'prix_avant': str(produit.prix_avant) if produit.prix_avant is not None else '',
                    'pourcentage': str(int(produit.pourcentage)) if produit.pourcentage is not None else '',
                    'description': description[:80] if description else '',
                    'description_2': description_2[:80] if description_2 else '',
                    'description_3': description_3[:80] if description_3 else '',
                    'image_url': produit.image_produit.url if produit.image_produit else '',
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'count': total})}\n\n"

        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


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