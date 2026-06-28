# catalogue_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('upload/', views.upload, name='upload'),
    path('edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('update-field/', views.update_product_field, name='update_product_field'),
    path('save-selected/', views.save_selected_products, name='save_selected_products'),
    path('save-all/', views.save_all_products, name='save_all_products'),
    path('delete-selected/', views.delete_selected_products, name='delete_selected_products'),
    path('delete-all/', views.delete_all_products, name='delete_all_products'),
    path('products/', views.product_list, name='product_list'),
    path('api/product/<int:product_id>/', views.get_product_details, name='get_product_details'),
    path('api/catalogue/<int:catalogue_id>/image/', views.get_catalogue_image, name='get_catalogue_image'),
]