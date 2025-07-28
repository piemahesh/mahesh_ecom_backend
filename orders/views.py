from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from .models import Order
from .serializers import OrderSerializer, OrderCreateSerializer
from .tasks import send_order_confirmation_email
from .utils import generate_order_receipt_pdf

class OrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

class OrderCreateView(generics.CreateAPIView):
    serializer_class = OrderCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        order = serializer.save()
        # Send confirmation email asynchronously
        send_order_confirmation_email.delay(order.id)

class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_order(request, order_id):
    """Cancel an order if it's still pending"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status not in ['pending', 'processing']:
        return Response({'error': 'Order cannot be cancelled'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Restore stock
    for item in order.items.all():
        item.product.stock += item.quantity
        item.product.save()
    
    order.status = 'cancelled'
    order.save()
    
    return Response({'message': 'Order cancelled successfully'})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_receipt_pdf(request, order_id):
    """Generate and download PDF receipt for an order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    pdf_buffer = generate_order_receipt_pdf(order)
    
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="order_{order.id}_receipt.pdf"'
    
    return response

# Admin views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_orders(request):
    """Get all orders for admin users"""
    if not request.user.is_admin:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    orders = Order.objects.all()
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def admin_update_order_status(request, order_id):
    """Update order status (admin only)"""
    if not request.user.is_admin:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    order = get_object_or_404(Order, id=order_id)
    new_status = request.data.get('status')
    
    if new_status not in dict(Order.STATUS_CHOICES):
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
    
    order.status = new_status
    order.save()
    
    serializer = OrderSerializer(order)
    return Response(serializer.data)