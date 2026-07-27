# catalogue_app/sql_sync.py
import pyodbc
from django.conf import settings
from datetime import datetime

class SQLServerSync:
    def __init__(self):
        self.connection_string = (
            'DRIVER={ODBC Driver 17 for SQL Server};'
            'SERVER=LAPTOP-SS7MFL50\\MSSQLSERVER01;'
            'DATABASE=catalogue;'
            'Trusted_Connection=yes;'
        )
    
    def get_connection(self):
        try:
            conn = pyodbc.connect(self.connection_string)
            print("✅ Connexion à SQL Server établie avec succès")
            return conn
        except Exception as e:
            print(f"❌ Erreur de connexion à SQL Server: {e}")
            return None
    
    def create_tables(self):
        conn = self.get_connection()
        if not conn:
            return False
        
        try:
            cursor = conn.cursor()
            
            # Table Extraction avec id_sqlite
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='extraction' AND xtype='U')
                CREATE TABLE extraction (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    id_sqlite INT NULL,
                    nom_fr NVARCHAR(255) NULL,
                    nom_ar NVARCHAR(255) NULL,
                    marque NVARCHAR(255) NULL,
                    prix DECIMAL(10,3) NULL,
                    prix_avant DECIMAL(10,3) NULL,
                    pourcentage DECIMAL(5,2) NULL,
                    desc_1 NVARCHAR(MAX) NULL,
                    desc_2 NVARCHAR(MAX) NULL,
                    desc_3 NVARCHAR(MAX) NULL,
                    note_1 NVARCHAR(MAX) NULL,
                    note_2 NVARCHAR(MAX) NULL,
                    catalogue_id INT NULL
                )
            """)
            
            #  Table Catalogue avec id_sqlite
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='catalogues' AND xtype='U')
                CREATE TABLE catalogues (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    id_sqlite INT NULL,
                    enseigne NVARCHAR(100) NULL,
                    date_debut DATE NULL,
                    date_fin DATE NULL,
                    note NVARCHAR(255) NULL,
                    date_upload DATETIME NULL
                )
            """)
            
            conn.commit()
            print("✅ Tables créées avec succès dans SQL Server")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la création des tables: {e}")
            return False
        finally:
            conn.close()
    
    def sync_catalogues(self, catalogues):
        conn = self.get_connection()
        if not conn:
            print("❌ Impossible de se connecter à SQL Server")
            return False
        
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM catalogues")
            
            for catalogue in catalogues:
                cursor.execute("""
                    INSERT INTO catalogues (id_sqlite, enseigne, date_debut, date_fin, note, date_upload)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    catalogue.id,
                    catalogue.enseigne.nom if catalogue.enseigne else None,
                    catalogue.date_debut,
                    catalogue.date_fin,
                    catalogue.note,
                    catalogue.date_upload
                ))
            
            conn.commit()
            print(f"✅ {len(catalogues)} catalogues synchronisés avec SQL Server")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la synchronisation des catalogues: {e}")
            return False
        finally:
            conn.close()
    
    def sync_produits(self, produits):
        conn = self.get_connection()
        if not conn:
            print("❌ Impossible de se connecter à SQL Server")
            return False
        
        try:
            cursor = conn.cursor()
            
            for produit in produits:
                # Utiliser MERGE (UPSERT) pour SQL Server
                cursor.execute("""
                    MERGE INTO extraction AS target
                    USING (SELECT ? AS id_sqlite) AS source
                    ON target.id_sqlite = source.id_sqlite
                    WHEN MATCHED THEN
                        UPDATE SET
                            nom_fr = ?,
                            nom_ar = ?,
                            marque = ?,
                            prix = ?,
                            prix_avant = ?,
                            pourcentage = ?,
                            desc_1 = ?,
                            desc_2 = ?,
                            desc_3 = ?,
                            note_1 = ?,
                            note_2 = ?,
                            catalogue_id = ?
                    WHEN NOT MATCHED THEN
                        INSERT (
                            id_sqlite, nom_fr, nom_ar, marque,
                            prix, prix_avant, pourcentage,
                            desc_1, desc_2, desc_3,
                            note_1, note_2,
                            catalogue_id
                        ) VALUES (
                            ?, ?, ?, ?,
                            ?, ?, ?,
                            ?, ?, ?,
                            ?, ?, ?
                        );
                """, (
                    # Source
                    produit.id,
                    # UPDATE
                    produit.nom_fr or '',
                    produit.nom_ar or '',
                    produit.marque or '',
                    produit.prix,
                    produit.prix_avant,
                    produit.pourcentage,
                    produit.desc_1 or '',
                    produit.desc_2 or '',
                    produit.desc_3 or '',
                    produit.note_1 or '',
                    produit.note_2 or '',
                    produit.catalogue_id,
                    # INSERT
                    produit.id,
                    produit.nom_fr or '',
                    produit.nom_ar or '',
                    produit.marque or '',
                    produit.prix,
                    produit.prix_avant,
                    produit.pourcentage,
                    produit.desc_1 or '',
                    produit.desc_2 or '',
                    produit.desc_3 or '',
                    produit.note_1 or '',
                    produit.note_2 or '',
                    produit.catalogue_id
                ))
            
            conn.commit()
            print(f"✅ {len(produits)} produits synchronisés avec SQL Server (UPSERT)")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la synchronisation des produits: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def delete_produits(self, produits_ids):
        """Supprime les produits de SQL Server par id_sqlite"""
        conn = self.get_connection()
        if not conn:
            print("❌ Impossible de se connecter à SQL Server")
            return False
        
        try:
            cursor = conn.cursor()
            
            placeholders = ','.join(['?'] * len(produits_ids))
            query = f"DELETE FROM extraction WHERE id_sqlite IN ({placeholders})"
            
            print(f"🔍 Suppression des produits SQLite IDs: {produits_ids}")
            print(f"🔍 Requête SQL: {query}")
            
            cursor.execute(query, produits_ids)
            rows_affected = cursor.rowcount
            conn.commit()
            
            print(f"✅ {rows_affected} produits supprimés de SQL Server")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la suppression: {e}")
            return False
        finally:
            conn.close()
    
    def sync_all(self):
        from .models import Catalogue, Produit
        
        print("🔄 Début de la synchronisation avec SQL Server...")
        
        self.create_tables()
        
        catalogues = Catalogue.objects.all()
        self.sync_catalogues(catalogues)
        
        produits = Produit.objects.filter(est_sauvegarde=True)
        self.sync_produits(produits)
        
        print("✅ Synchronisation terminée !")
    
    def get_produits_from_sql(self):
        conn = self.get_connection()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    id, id_sqlite,
                    nom_fr, nom_ar, marque,
                    prix, prix_avant, pourcentage,
                    desc_1, desc_2, desc_3,
                    note_1, note_2,
                    catalogue_id
                FROM extraction 
                ORDER BY id_sqlite
            """)
            rows = cursor.fetchall()
            
            produits = []
            for row in rows:
                produits.append({
                    'id': row[0],
                    'id_sqlite': row[1],
                    'nom_fr': row[2],
                    'nom_ar': row[3],
                    'marque': row[4],
                    'prix': row[5],
                    'prix_avant': row[6],
                    'pourcentage': row[7],
                    'desc_1': row[8],
                    'desc_2': row[9],
                    'desc_3': row[10],
                    'note_1': row[11],
                    'note_2': row[12],
                    'catalogue_id': row[13]
                })
            
            print(f"✅ {len(produits)} produits récupérés depuis SQL Server")
            return produits
        except Exception as e:
            print(f"❌ Erreur lors de la récupération: {e}")
            return []
        finally:
            conn.close()