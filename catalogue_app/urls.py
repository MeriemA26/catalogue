# catalogue_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
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
    path('api/delete-by-marque/', views.delete_by_marque, name='delete_by_marque'),
    path('api/save-by-marque/', views.save_by_marque, name='save_by_marque'),
    path('product/edit_saved/<int:product_id>/', views.edit_product_saved, name='edit_product_saved'),
    path('product/delete/<int:product_id>/', views.delete_saved_product, name='delete_saved_product'),
    path('product/export/excel/', views.export_products_excel, name='export_products_excel'),
]