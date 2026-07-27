j'ai change def upload steam ligne 611 + autre ligne sous try views  **done**

pipline aussi  **done**

style.css ajout au dernier **done**

modification dans upload.html **done**





changer depuis celui à distance dans ce qui est dans le pc celle de date **done**







**DeliceAdmin2026 code** 

python manage.py shell



from django.contrib.auth.models import User



\# Voir combien d'utilisateurs existent avant de supprimer

User.objects.all().count()

User.objects.all().values\_list('username', 'is\_superuser')



\# Supprimer TOUS les utilisateurs (y compris superuser)

User.objects.all().delete()





User.objects.all().count()
pour verifier



