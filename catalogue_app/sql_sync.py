# catalogue_app/sql_sync.py
import pyodbc
from django.conf import settings

class SQLServerSync:
    def __init__(self):
        # Configuration de la connexion SQL Server
        self.connection_string = (
            'DRIVER={ODBC Driver 17 for SQL Server};'
            'SERVER=LAPTOP-SS7MFL50\\MSSQLSERVER01;'
            'DATABASE=votre_base;'  # Remplacez par le nom de votre base
            'Trusted_Connection=yes;'
        )
    
    def get_connection(self):
        """Établit la connexion à SQL Server"""
        try:
            return pyodbc.connect(self.connection_string)
        except Exception as e:
            print(f"Erreur de connexion à SQL Server: {e}")
            return None
    
    def sync_produits(self, produits):
        """Synchronise les produits avec SQL Server"""
        conn = self.get_connection()
        if not conn:
            print("Impossible de se connecter à SQL Server")
            return False
        
        try:
            cursor = conn.cursor()
            
            # Créer la table si elle n'existe pas
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='extraction' AND xtype='U')
                CREATE TABLE extraction (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    nom VARCHAR(255),
                    prix DECIMAL(10,2),
                    prix_avant DECIMAL(10,2),
                    pourcentage DECIMAL(5,2),
                    remise DECIMAL(10,2),
                    description TEXT,
                    extrait_texte TEXT,
                    catalogue_id INT,
                    date_sync DATETIME DEFAULT GETDATE()
                )
            """)
            
            for produit in produits:
                cursor.execute("""
                    INSERT INTO extraction (nom, prix, prix_avant, pourcentage, remise, 
                                          description, extrait_texte, catalogue_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    produit.nom,
                    produit.prix,
                    produit.prix_avant,
                    produit.pourcentage,
                    produit.remise,
                    produit.description,
                    produit.extrait_texte,
                    produit.catalogue_id
                ))
            
            conn.commit()
            print(f"✓ {len(produits)} produits synchronisés avec SQL Server")
            return True
        except Exception as e:
            print(f"Erreur lors de la synchronisation: {e}")
            return False
        finally:
            conn.close()