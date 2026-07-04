# catalogue_app/pipeline.py
import os
import re
from decimal import Decimal, InvalidOperation
import cv2
from ultralytics import YOLO
import easyocr
import torch
import base64


# Correction du chemin des modèles
ML_DIR = os.path.dirname(os.path.abspath(__file__))
# Les modèles sont dans le dossier 'models' à l'intérieur de catalogue_app
MODELS_DIR = os.path.join(ML_DIR, 'models')
PRODUCT_MODEL_PATH = os.path.join(MODELS_DIR, 'best_prod.pt')
FIELD_MODEL_PATH = os.path.join(MODELS_DIR, 'best_details.pt')

_product_model = None
_field_model = None
_reader_latin = None
_reader_ar = None


# Fonctions de détection de langue (définies en dehors de toute classe)
def _is_arabic(text):
    """Vérifie si le texte contient des caractères arabes"""
    if not text:
        return False
    arabic_pattern = re.compile(r'[\u0600-\u06FF]')
    return bool(arabic_pattern.search(text))

def _is_french(text):
    """Vérifie si le texte est en français (caractères latins)"""
    if not text:
        return False
    latin_pattern = re.compile(r'[a-zA-Z]')
    arabic_pattern = re.compile(r'[\u0600-\u06FF]')
    return bool(latin_pattern.search(text)) and not bool(arabic_pattern.search(text))

def _detect_language(text):
    """Détecte la langue d'un texte"""
    if not text:
        return 'unknown'
    if _is_arabic(text):
        return 'arabic'
    if _is_french(text):
        return 'french'
    return 'mixed'

def get_product_model():
    global _product_model
    if _product_model is None:
        if os.path.exists(PRODUCT_MODEL_PATH):
            _product_model = YOLO(PRODUCT_MODEL_PATH)
        else:
            raise FileNotFoundError(f"Modèle non trouvé: {PRODUCT_MODEL_PATH}")
    return _product_model

def get_field_model():
    global _field_model
    if _field_model is None:
        if os.path.exists(FIELD_MODEL_PATH):
            _field_model = YOLO(FIELD_MODEL_PATH)
        else:
            raise FileNotFoundError(f"Modèle non trouvé: {FIELD_MODEL_PATH}")
    return _field_model

def get_ocr_readers():
    global _reader_latin, _reader_ar
    if _reader_latin is None:
        use_gpu = torch.cuda.is_available()
        # 🔥 Reader pour les langues latines (français, anglais)
        _reader_latin = easyocr.Reader(['fr', 'en'], gpu=use_gpu)
        print("✅ Reader Latin (FR+EN) créé")
    if _reader_ar is None:
        use_gpu = torch.cuda.is_available()
        # 🔥 Reader pour l'arabe (avec anglais pour les chiffres)
        _reader_ar = easyocr.Reader(['ar', 'en'], gpu=use_gpu)
        print("✅ Reader AR+EN créé")
    return _reader_latin, _reader_ar

FIELD_CLASS_MAP = {
    'product_name': 'nom_fr',
    'product_AR': 'nom_ar',
    'brand': 'marque',
    'price': 'prix',
    'price_before': 'prix_avant',
    'pct': 'pourcentage',
    'description': 'desc_1',      # ← Clé: description, Valeur: desc_1
    'description2': 'desc_2',     # ← Clé: description2, Valeur: desc_2
    'description3': 'desc_3'      # ← Clé: description3, Valeur: desc_3
}

def image_to_base64(image):
    _, buffer = cv2.imencode('.jpg', image)
    return base64.b64encode(buffer).decode('utf-8')

def extract_price(roi, debug=False):
    reader_latin, _ = get_ocr_readers()
    roi_big = cv2.resize(roi, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(roi_big, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results = reader_latin.readtext(thresh, paragraph=False, width_ths=0.3, height_ths=0.3)
    
    if not results:
        return ""
    
    results_sorted = sorted(results, key=lambda x: x[0][0][1])
    numbers = []
    for bbox, text, conf in results_sorted:
        if conf > 0.3:
            text_clean = text.strip()
            if text_clean.upper() in ['DT', 'D1', '0T', 'D7', '0I', 'D', 'T']:
                continue
            numbers.append(text_clean)
    
    if len(numbers) >= 2:
        top = re.sub(r'[^0-9]', '', numbers[0])
        bottom = re.sub(r'[^0-9]', '', numbers[-1])
        if top and bottom:
            return f"{top}.{bottom}"
    elif len(numbers) == 1:
        digits = re.sub(r'[^0-9]', '', numbers[0])
        if len(digits) == 4:
            return f"{digits[0]}.{digits[1:]}"
        elif len(digits) == 5:
            return f"{digits[:2]}.{digits[2:]}"
        elif len(digits) == 3:
            return f"0.{digits}"
        elif len(digits) == 2:
            return f"0.{digits}"
    return ""

def extract_percentage(roi, debug=False):
    reader_latin, _ = get_ocr_readers()
    roi_big = cv2.resize(roi, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(roi_big, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results = reader_latin.readtext(thresh, paragraph=False)
    
    for bbox, text, conf in results:
        if conf > 0.3:
            match = re.search(r'(\d+[.,]?\d*)\s*%', text)
            if match:
                value = match.group(1).replace(',', '.')
                try:
                    val = float(value)
                    if 1 <= val <= 100:
                        return value
                except:
                    pass
            match = re.search(r'(\d+[.,]?\d*)', text)
            if match:
                value = match.group(1).replace(',', '.')
                try:
                    val = float(value)
                    if 1 <= val <= 100:
                        return value
                except:
                    pass
    return ""

def extract_text_mixed(roi, reader_latin, reader_ar):
    """
    Extrait le texte d'une ROI en combinant les résultats du reader latin et arabe.
    Utile pour les textes mixtes (arabe + français).
    """
    roi_big = cv2.resize(roi, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(roi_big, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 🔥 Essayer avec le reader latin d'abord
    results_latin = reader_latin.readtext(thresh)
    texts_latin = [t for bbox, t, conf in results_latin if conf > 0.2]
    
    # 🔥 Essayer avec le reader arabe
    results_ar = reader_ar.readtext(thresh)
    texts_ar = [t for bbox, t, conf in results_ar if conf > 0.2]
    
    # 🔥 Combiner les résultats (éviter les doublons)
    all_texts = texts_latin + texts_ar
    # Supprimer les doublons en gardant l'ordre
    seen = set()
    unique_texts = []
    for text in all_texts:
        text_clean = text.strip()
        if text_clean and text_clean not in seen:
            seen.add(text_clean)
            unique_texts.append(text_clean)
    
    return " ".join(unique_texts)


def extract_text(roi, reader, prefer_latin=True):
    """
    Extrait le texte d'une ROI avec un reader spécifique.
    """
    roi_big = cv2.resize(roi, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(roi_big, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    results = reader.readtext(thresh)
    if results:
        texts = [t for bbox, t, conf in results if conf > 0.2]
        return " ".join(texts)
    return ""

def format_price(value):
    if value is None or value == '':
        return None
    try:
        return float(value)
    except:
        return None

def process_catalogue_image(image_path, conf_product=0.45, conf_field=0.45, debug=False):
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    product_model = get_product_model()
    field_model = get_field_model()
    reader_latin, reader_ar = get_ocr_readers()
    
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Impossible de lire l'image : {image_path}")
    
    products = []
    product_results = product_model(image_path, conf=conf_product, verbose=False, device=device)[0]
    
    print(f"📊 {len(product_results.boxes)} produits détectés par YOLO")
    
    for idx, box in enumerate(product_results.boxes):
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        crop = image[y1:y2, x1:x2]
        if crop.size == 0:
            continue
        
        data = {
            'id': idx,
            'nom_fr': '',
            'nom_ar': '',
            'marque': '',
            'prix': None,
            'prix_avant': None,
            'pourcentage': None,
            'remise': '',
            'desc_1': '',
            'desc_2': '',
            'desc_3': '',
            'product_image_b64': image_to_base64(crop),
            'fields': [],
        }
        
        field_results = field_model.predict(crop, conf=conf_field, device=device, verbose=False)[0]
        field_names = field_results.names
        
        extracted_pct = None
        extracted_prix = None
        extracted_prix_avant = None
        
        for fbox, fcls in zip(field_results.boxes.xyxy.cpu().numpy(), field_results.boxes.cls.cpu().numpy()):
            fx1, fy1, fx2, fy2 = map(int, fbox)
            class_name = field_names[int(fcls)]
            roi = crop[fy1:fy2, fx1:fx2]
            if roi.size == 0:
                continue
            
            target = FIELD_CLASS_MAP.get(class_name)
            if target is None:
                continue
            
            extracted_value = ""
            
            if class_name == 'product_AR':
                extracted_value = extract_text(roi, reader_ar)
                data['nom_ar'] = extracted_value
                print(f"   ✅ Nom AR détecté: {extracted_value[:50]}...")
                
            elif class_name == 'product_name':
                extracted_value = extract_text(roi, reader_latin)
                data['nom_fr'] = extracted_value
                print(f"   ✅ Nom FR détecté: {extracted_value[:50]}...")
                
            elif class_name == 'brand':
                # Essayer d'abord en latin, puis en arabe
                extracted_value = extract_text(roi, reader_latin)
                if not extracted_value:
                    extracted_value = extract_text(roi, reader_ar)
                data['marque'] = extracted_value
            elif class_name == 'price':
                extracted_value = extract_price(roi, debug)
                if extracted_value:
                    data['prix'] = float(extracted_value)
                    extracted_prix = float(extracted_value)
                    print(f"   ✅ Prix détecté: {extracted_value}")
            elif class_name == 'price_before':
                extracted_value = extract_price(roi, debug)
                if extracted_value:
                    data['prix_avant'] = float(extracted_value)
                    extracted_prix_avant = float(extracted_value)
                    print(f"   ✅ Prix avant détecté: {extracted_value}")
            elif class_name == 'pct':
                extracted_value = extract_percentage(roi, debug)
                if extracted_value:
                    data['pourcentage'] = float(extracted_value)
                    extracted_pct = float(extracted_value)
                    print(f"   ✅ Pourcentage détecté: {extracted_value}%")
            elif class_name == 'description':
                # 🔥 Utiliser le reader latin pour les descriptions (peut contenir du français)
                extracted_value = extract_text(roi, reader_latin)
                # 🔥 Si pas de résultat, essayer avec le reader arabe
                if not extracted_value:
                    extracted_value = extract_text(roi, reader_ar)
                # 🔥 Si toujours pas, utiliser le mixte
                if not extracted_value:
                    extracted_value = extract_text_mixed(roi, reader_latin, reader_ar)
                
                # Nettoyer la description
                if extracted_value:
                    extracted_value = re.sub(r'[^\w\s\u0600-\u06FF\.\,\-\(\)\:]+', ' ', extracted_value)
                    extracted_value = re.sub(r'\s+', ' ', extracted_value).strip()
                data['desc_1'] = extracted_value
                if extracted_value:
                    print(f"   ✅ Desc 1 nettoyée: {extracted_value[:50]}...")
                    
            elif class_name == 'description2':
                # 🔥 Même logique pour description2
                extracted_value = extract_text(roi, reader_latin)
                if not extracted_value:
                    extracted_value = extract_text(roi, reader_ar)
                if not extracted_value:
                    extracted_value = extract_text_mixed(roi, reader_latin, reader_ar)
                data['desc_2'] = extracted_value
                if extracted_value:
                    print(f"   ✅ Desc 2 nettoyée: {extracted_value[:50]}...")
                    
            elif class_name == 'description3':
                # 🔥 Même logique pour description3
                extracted_value = extract_text(roi, reader_latin)
                if not extracted_value:
                    extracted_value = extract_text(roi, reader_ar)
                if not extracted_value:
                    extracted_value = extract_text_mixed(roi, reader_latin, reader_ar)
                data['desc_3'] = extracted_value
                if extracted_value:
                    print(f"   ✅ Desc 3 nettoyée: {extracted_value[:50]}...")
        
        # Calcul des prix
        # 🔥 RÈGLE D'OR : si prix ET prix_avant ont TOUS LES DEUX été lus directement par l'OCR,
        # on les garde tels quels (ce sont les vraies valeurs imprimées). On ne les recalcule
        # JAMAIS à partir du pourcentage, car le "-X%" affiché sur l'étiquette est souvent
        # lui-même arrondi et ne redonne pas exactement le même prix_avant si on le recalcule.
        if extracted_prix is not None and extracted_prix > 0 and extracted_prix_avant is not None and extracted_prix_avant > 0:
            data['prix'] = extracted_prix
            data['prix_avant'] = extracted_prix_avant
            if extracted_pct is not None and 1 <= extracted_pct <= 100:
                # Le pourcentage a aussi été lu directement -> on garde la valeur imprimée
                data['pourcentage'] = extracted_pct
                data['remise'] = f"{extracted_pct}%"
            elif extracted_prix < extracted_prix_avant:
                # Pas de pourcentage lu -> on le déduit des 2 prix réels
                pct = round((1 - extracted_prix / extracted_prix_avant) * 100)
                if 1 <= pct <= 100:
                    data['pourcentage'] = pct
                    data['remise'] = f"{pct}%"
        # Un seul des deux prix est connu + un pourcentage -> on déduit celui qui manque
        elif extracted_pct is not None and 1 <= extracted_pct <= 100:
            data['pourcentage'] = extracted_pct
            data['remise'] = f"{extracted_pct}%"
            if extracted_prix is not None and extracted_prix > 0:
                data['prix_avant'] = round(extracted_prix / (1 - extracted_pct/100), 3)
                data['prix'] = extracted_prix
            elif extracted_prix_avant is not None and extracted_prix_avant > 0:
                data['prix'] = round(extracted_prix_avant * (1 - extracted_pct/100), 3)
                data['prix_avant'] = extracted_prix_avant
        elif extracted_prix is not None and extracted_prix > 0:
            data['prix'] = extracted_prix
        elif extracted_prix_avant is not None and extracted_prix_avant > 0:
            data['prix_avant'] = extracted_prix_avant
        
        # Détecter la langue des descriptions
        desc_1_lang = _detect_language(data['desc_1'])
        desc_2_lang = _detect_language(data['desc_2'])
        desc_3_lang = _detect_language(data['desc_3'])
        
        # Log des données extraites
        print(f"\n📦 Produit {idx+1}:")
        print(f"  Nom FR: {data['nom_fr'] if data['nom_fr'] else '(non détecté)'}")
        print(f"  Nom AR: {data['nom_ar'] if data['nom_ar'] else '(non détecté)'}")
        print(f"  Marque: {data['marque'] if data['marque'] else '(non détecté)'}")
        print(f"  Prix: {data['prix'] if data['prix'] is not None else '(non détecté)'}")
        print(f"  Prix avant: {data['prix_avant'] if data['prix_avant'] is not None else '(non détecté)'}")
        print(f"  Pourcentage: {data['pourcentage'] if data['pourcentage'] is not None else '(non détecté)'}")
        print(f"  Desc 1: {(data['desc_1'][:50] + '...') if data['desc_1'] else '(non détecté)'} [{desc_1_lang}]")
        print(f"  Desc 2: {(data['desc_2'][:50] + '...') if data['desc_2'] else '(non détecté)'} [{desc_2_lang}]")
        print(f"  Desc 3: {(data['desc_3'][:50] + '...') if data['desc_3'] else '(non détecté)'} [{desc_3_lang}]")

        products.append(data)
    
    return products