from django.urls import path
from . import views

urlpatterns = [
    path('', views.OrderListView.as_view(), name='order-list'),
    path('create/', views.OrderCreateView.as_view(), name='order-create'),
    path('<uuid:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('<uuid:order_id>/cancel/', views.cancel_order, name='cancel-order'),
    path('<uuid:order_id>/receipt-pdf/', views.order_receipt_pdf, name='order-receipt-pdf'),
    
    # Admin endpoints
    path('admin/all/', views.admin_orders, name='admin-orders'),
    path('admin/<uuid:order_id>/status/', views.admin_update_order_status, name='admin-update-order-status'),
]