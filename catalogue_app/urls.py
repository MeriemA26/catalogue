# catalogue_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.welcome, name='welcome'),
    path('dashboard/', views.index, name='index'),
    path('upload/', views.upload, name='upload'),
    path('product/edit/<int:product_id>/', views.edit_product, name='edit_product'),  # Changé ici
    path('update-field/', views.update_product_field, name='update_product_field'),
    path('save-selected/', views.save_selected_products, name='save_selected_products'),
    path('save-all/', views.save_all_products, name='save_all_products'),
    path('delete-selected/', views.delete_selected_products, name='delete_selected_products'),
    path('delete-all/', views.delete_all_products, name='delete_all_products'),
    path('products/', views.product_list, name='product_list'),
    path('api/product/<int:product_id>/', views.get_product_details, name='get_product_details'),
    path('api/catalogue/<int:catalogue_id>/image/', views.get_catalogue_image, name='get_catalogue_image'),
    path('upload/stream/', views.upload_stream, name='upload_stream'),
    path('api/recent-products/', views.get_recent_products, name='get_recent_products'),
    path('product/add/', views.add_product, name='add_product'),
    path('api/marques/', views.get_marques_list, name='get_marques_list'),
    path('product/edit_saved/<int:product_id>/', views.edit_product_saved, name='edit_product_saved'),
    path('product/delete/<int:product_id>/', views.delete_saved_product, name='delete_saved_product'),
    path('product/export/excel/', views.export_products_excel, name='export_products_excel'),
    path('export/catalogue/<int:catalogue_id>/', views.export_catalogue_excel, name='export_catalogue_excel'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('creer-compte/', views.creer_compte, name='creer_compte'),
    path('register-admin/', views.register_admin, name='register_admin'),
    
]