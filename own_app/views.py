from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.template import loader
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Sum
from own_app.models import Item, Cart, CartItem, Order, OrderItem
import os






def index(request):
    cart = get_or_create_cart(request)
    cart_count = CartItem.objects.filter(cart=cart).aggregate(Sum('quantity'))['quantity__sum'] or 0
    items = Item.objects.all()
    item = Item.objects.get(name='New Green Jacket')
    return render(request, 'index.html', {'cart_count': cart_count, 'items': items, 'item': item})

def home(request):
    return render(request, 'index.html')

def about(request):
    cart = get_or_create_cart(request)
    cart_count = CartItem.objects.filter(cart=cart).aggregate(Sum('quantity'))['quantity__sum'] or 0
    return render(request, 'about.html', {'cart_count': cart_count})

def contact(request):
    cart = get_or_create_cart(request)
    cart_count = CartItem.objects.filter(cart=cart).aggregate(Sum('quantity'))['quantity__sum'] or 0
    return render(request, 'contact.html', {'cart_count': cart_count})

def products(request):
    cart = get_or_create_cart(request)
    cart_count = CartItem.objects.filter(cart=cart).aggregate(Sum('quantity'))['quantity__sum'] or 0
    item = Item.objects.get(name='New Green Jacket')
    return render(request, 'products.html', {'cart_count': cart_count, 'item': item})

def single_product(request, id):
    cart = get_or_create_cart(request)
    cart_count = CartItem.objects.filter(cart=cart).aggregate(Sum('quantity'))['quantity__sum'] or 0
    item = get_object_or_404(Item, id=id)
    return render(request, 'single-product.html', {'cart_count': cart_count, 'item': item})

def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart

def add_to_cart(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    cart = get_or_create_cart(request)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, item=item)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    messages.success(request, f"{item.name} added to cart.")
    return redirect('view_cart')

def view_cart(request):
    cart = get_or_create_cart(request)
    cart_items = CartItem.objects.filter(cart=cart)
    total = sum(item.total_price for item in cart_items)
    cart_count = CartItem.objects.filter(cart=cart).aggregate(Sum('quantity'))['quantity__sum'] or 0
    return render(request, 'cart.html', {'cart_items': cart_items, 'total': total, 'cart_count': cart_count})

def remove_from_cart(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    cart = get_or_create_cart(request)
    try:
        cart_item = CartItem.objects.get(cart=cart, item=item)
        cart_item.delete()
        messages.success(request, f"{item.name} removed from cart.")
    except CartItem.DoesNotExist:
        messages.error(request, "Item not in cart.")
    return redirect('view_cart')

def update_cart_item(request, item_id):
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        item = get_object_or_404(Item, id=item_id)
        cart = get_or_create_cart(request)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, item=item)
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
        else:
            cart_item.delete()
        return redirect('view_cart')
    return redirect('view_cart')

@login_required
def checkout(request):
    cart = get_or_create_cart(request)
    cart_items = CartItem.objects.filter(cart=cart)
    if not cart_items:
        messages.error(request, "Your cart is empty.")
        return redirect('view_cart')
    total = sum(item.total_price for item in cart_items)
    cart_count = CartItem.objects.filter(cart=cart).aggregate(Sum('quantity'))['quantity__sum'] or 0
    if request.method == 'POST':
        # Create order
        order = Order.objects.create(user=request.user, total_amount=total)
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                item=cart_item.item,
                quantity=cart_item.quantity,
                price=cart_item.item.price
            )
        # Clear cart
        cart_items.delete()
        messages.success(request, "Order placed successfully!")
        return redirect('order_confirmation', order_id=order.id)
    return render(request, 'checkout.html', {'cart_items': cart_items, 'total': total, 'cart_count': cart_count})

@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    cart = get_or_create_cart(request)
    cart_count = CartItem.objects.filter(cart=cart).aggregate(Sum('quantity'))['quantity__sum'] or 0
    return render(request, 'order_confirmation.html', {'order': order, 'cart_count': cart_count})

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Logged in successfully!")
            return redirect('profile')
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, 'login.html')

def signup_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        if password == confirm_password:
            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists.")
            elif User.objects.filter(email=email).exists():
                messages.error(request, "Email already exists.")
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                user.save()
                messages.success(request, "Account created successfully! Please log in.")
                return redirect('login')
        else:
            messages.error(request, "Passwords do not match.")
    return render(request, 'signup.html')

def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect('index')

@login_required
def profile(request):
    cart = get_or_create_cart(request)
    cart_count = CartItem.objects.filter(cart=cart).aggregate(Sum('quantity'))['quantity__sum'] or 0
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'profile.html', {'user': request.user, 'cart_count': cart_count, 'orders': orders})
