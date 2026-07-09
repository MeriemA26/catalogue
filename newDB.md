**installation de Django et un env** 


**1. Va dans le dossier du projet**

cd C:\\chemin\\vers\\catalogue\_project



**2. Crée un nouvel environnement virtuel**

python -m venv venv

(Tu peux aussi l'appeler env, mais venv est le nom le plus courant.)



**3. Active-le**

Sous PowerShell :

.\\venv\\Scripts\\Activate



**4. Mets pip à jour (optionnel mais recommandé)**

python -m pip install --upgrade pip



**5. Installe la même version de Django**

pip install Django==5.2.8



**6. Vérifie**

python -m django --version

=>5.2.8



**7.installer les biblios necessaire** 



\------------------------------------------------------------------------------------

Dans la table extraction, le champ **id\_sqlite** sert à faire le lien entre un produit dans **SQLite** et son équivalent dans **SQL Server**.







**to start from scratch (id=1)**

\*\*1/\*\*cd C:\\Users\\merya\\Desktop\\3AI\\sem1\\pyhton\\catalogue\_project

del db.sqlite3

**2/**# Créer les nouvelles migrations

python manage.py makemigrations



\# Appliquer les migrations

python manage.py migrate



\# Créer un superutilisateur (optionnel)

python manage.py createsuperuser



**🗄️ Étape 1 : Nettoyer SQL Server**



from catalogue\_app.sql\_sync import SQLServerSync



print("🗄️ Nettoyage de SQL Server...")

sql\_sync = SQLServerSync()

conn = sql\_sync.get\_connection()



if conn:

&#x20;   cursor = conn.cursor()

&#x20;

&#x20;   # Supprimer les données

&#x20;   cursor.execute("DELETE FROM extraction")

&#x20;   cursor.execute("DELETE FROM catalogues")

&#x20;   print("✅ Données supprimées de SQL Server")

&#x20;

&#x20;   # Réinitialiser les séquences IDENTITY

&#x20;   cursor.execute("DBCC CHECKIDENT ('extraction', RESEED, 0)")

&#x20;   cursor.execute("DBCC CHECKIDENT ('catalogues', RESEED, 0)")

&#x20;   print("✅ Séquences IDENTITY réinitialisées")

&#x20;

&#x20;   conn.commit()

&#x20;   conn.close()

&#x20;   print("✅ SQL Server complètement nettoyé !")

else:

&#x20;   print("❌ Impossible de se connecter à SQL Server")





**📝 Étape 2 : Insérer les enseignes**

from catalogue\_app.models import Enseigne



print("\\n📝 Insertion des enseignes...")



enseignes = \[

&#x20;   'MG',

&#x20;   'Carrefour',

&#x20;   'Carrefour Market',

&#x20;   'Carrefour Express',

&#x20;   'Aziza',

&#x20;   'Anouar',

&#x20;   'Géant',

&#x20;   'Monoprix'

]



for nom in enseignes:

&#x20;   enseigne = Enseigne.objects.create(nom=nom)

&#x20;   print(f"✅ Créée: {nom} (ID: {enseigne.id})")



print(f"\\n📊 Total: {Enseigne.objects.count()} enseignes")

print("\\n📋 Liste des enseignes :")

for e in Enseigne.objects.all().order\_by('id'):

&#x20;   print(f"   ID: {e.id:2d} | {e.nom}")

