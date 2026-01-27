#!/usr/bin/env python
"""
Test Data Generator for FurniTrack Pro Sales App - FIXED VERSION
Run: python manage.py shell < create_test_data.py
"""

import os
import sys
import django
from datetime import datetime, timedelta
import random
from decimal import Decimal
from django.utils import timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mbaosmart_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import User
from production.models import Product
from sales.models import Shop, ShopStock, StockTransfer, StockTransferItem, Sale, SaleItem, Customer, DailySalesReport
from hr.models import Employee

User = get_user_model()

def create_test_users():
    """Create test users with different roles"""
    print("Creating test users...")
    
    users_data = [
        # Owner
        {
            'username': 'owner',
            'email': 'owner@furnitrack.com',
            'password': 'password123',
            'first_name': 'John',
            'last_name': 'Kamau',
            'role': 'owner',
            'phone_number': '+254700111111'
        },
        # Store Manager
        {
            'username': 'store_manager',
            'email': 'store@furnitrack.com',
            'password': 'password123',
            'first_name': 'Mary',
            'last_name': 'Wanjiku',
            'role': 'store_manager',
            'phone_number': '+254700222222'
        },
        # Production Manager
        {
            'username': 'production_manager',
            'email': 'production@furnitrack.com',
            'password': 'password123',
            'first_name': 'Peter',
            'last_name': 'Kariuki',
            'role': 'production_manager',
            'phone_number': '+254700333333'
        },
        # Accountant
        {
            'username': 'accountant',
            'email': 'accountant@furnitrack.com',
            'password': 'password123',
            'first_name': 'Susan',
            'last_name': 'Muthoni',
            'role': 'accountant',
            'phone_number': '+254700444444'
        },
        # Supervisor
        {
            'username': 'supervisor',
            'email': 'supervisor@furnitrack.com',
            'password': 'password123',
            'first_name': 'David',
            'last_name': 'Odhiambo',
            'role': 'supervisor',
            'phone_number': '+254700555555'
        },
        # Fundi/Worker
        {
            'username': 'fundi1',
            'email': 'fundi1@furnitrack.com',
            'password': 'password123',
            'first_name': 'James',
            'last_name': 'Omondi',
            'role': 'fundi',
            'phone_number': '+254700666666'
        },
        {
            'username': 'fundi2',
            'email': 'fundi2@furnitrack.com',
            'password': 'password123',
            'first_name': 'Jane',
            'last_name': 'Atieno',
            'role': 'fundi',
            'phone_number': '+254700777777'
        },
        # Shop Manager 1
        {
            'username': 'shop_manager1',
            'email': 'shop1@furnitrack.com',
            'password': 'password123',
            'first_name': 'Michael',
            'last_name': 'Mwangi',
            'role': 'shop_manager',
            'phone_number': '+254700888888'
        },
        # Shop Manager 2
        {
            'username': 'shop_manager2',
            'email': 'shop2@furnitrack.com',
            'password': 'password123',
            'first_name': 'Sarah',
            'last_name': 'Wambui',
            'role': 'shop_manager',
            'phone_number': '+254700999999'
        },
        # Sales Person 1
        {
            'username': 'sales_person1',
            'email': 'sales1@furnitrack.com',
            'password': 'password123',
            'first_name': 'Brian',
            'last_name': 'Kipchoge',
            'role': 'sales_person',
            'phone_number': '+254700101010'
        },
        # Sales Person 2
        {
            'username': 'sales_person2',
            'email': 'sales2@furnitrack.com',
            'password': 'password123',
            'first_name': 'Grace',
            'last_name': 'Akinyi',
            'role': 'sales_person',
            'phone_number': '+254700202020'
        },
    ]
    
    users = {}
    for user_data in users_data:
        user, created = User.objects.get_or_create(
            username=user_data['username'],
            defaults={
                'email': user_data['email'],
                'first_name': user_data['first_name'],
                'last_name': user_data['last_name'],
                'role': user_data['role'],
                'phone_number': user_data['phone_number']
            }
        )
        if created:
            user.set_password(user_data['password'])
            user.save()
            print(f"Created user: {user.get_full_name()} ({user.role})")
        users[user_data['username']] = user
    return users

def create_employees(users):
    """Create employee records for users"""
    print("\nCreating employees...")
    
    employee_users = ['store_manager', 'production_manager', 'supervisor', 'fundi1', 'fundi2']
    
    for username in employee_users:
        user = users.get(username)
        if user:
            employee, created = Employee.objects.get_or_create(
                user=user,
                defaults={
                    'hire_date': timezone.now().date() - timedelta(days=365),
                    'hourly_rate': Decimal('500') if 'fundi' in username else Decimal('1000'),
                    'department': 'production' if 'fundi' in username else 'general'
                }
            )
            if created:
                print(f"Created employee: {employee.full_name}")

def create_shops(users):
    """Create test shops"""
    print("\nCreating shops...")
    
    shops_data = [
        {
            'name': 'Nairobi CBD Main Shop',
            'shop_type': 'main',
            'location': 'Moi Avenue, Nairobi CBD',
            'phone': '+254202345678',
            'email': 'nairobi@furnitrack.com',
            'address': 'Moi Avenue, Next to KICC, Nairobi',
            'opening_date': timezone.now().date() - timedelta(days=730),
            'manager': users.get('shop_manager1')
        },
        {
            'name': 'Westlands Branch',
            'shop_type': 'branch',
            'location': 'Westlands, Nairobi',
            'phone': '+254202456789',
            'email': 'westlands@furnitrack.com',
            'address': 'Woodvale Grove, Westlands, Nairobi',
            'opening_date': timezone.now().date() - timedelta(days=365),
            'manager': users.get('shop_manager2')
        },
        {
            'name': 'Thika Showroom',
            'shop_type': 'showroom',
            'location': 'Thika Road, Thika',
            'phone': '+254202567890',
            'email': 'thika@furnitrack.com',
            'address': 'Thika Road Mall, Thika',
            'opening_date': timezone.now().date() - timedelta(days=180),
            'manager': users.get('shop_manager1')
        },
        {
            'name': 'Mombasa Branch',
            'shop_type': 'branch',
            'location': 'Mombasa',
            'phone': '+254412345678',
            'email': 'mombasa@furnitrack.com',
            'address': 'Moi Avenue, Mombasa',
            'opening_date': timezone.now().date() - timedelta(days=90),
            'manager': users.get('shop_manager2')
        }
    ]
    
    shops = []
    for shop_data in shops_data:
        shop, created = Shop.objects.get_or_create(
            name=shop_data['name'],
            defaults=shop_data
        )
        if created:
            print(f"Created shop: {shop.name}")
        shops.append(shop)
    
    return shops

def create_products():
    """Create test products"""
    print("\nCreating products...")
    
    products_data = [
        {
            'name': '3-Seater Sofa Set',
            'product_type': 'sofa',
            'description': 'Premium 3-seater sofa with wooden frame and leather upholstery',
            'selling_price': Decimal('45000.00')
        },
        {
            'name': 'Executive Office Chair',
            'product_type': 'chair',
            'description': 'Ergonomic executive office chair with lumbar support',
            'selling_price': Decimal('15000.00')
        },
        {
            'name': 'King Size Bed',
            'product_type': 'bed',
            'description': 'Solid wood king size bed with storage drawers',
            'selling_price': Decimal('65000.00')
        },
        {
            'name': 'Dining Table Set',
            'product_type': 'table',
            'description': '6-seater dining table with matching chairs',
            'selling_price': Decimal('35000.00')
        },
        {
            'name': 'Bookshelf Cabinet',
            'product_type': 'cabinet',
            'description': 'Modern bookshelf cabinet with glass doors',
            'selling_price': Decimal('22000.00')
        },
        {
            'name': 'Coffee Table',
            'product_type': 'table',
            'description': 'Glass top coffee table with wooden legs',
            'selling_price': Decimal('12000.00')
        },
        {
            'name': 'Bar Stool',
            'product_type': 'stool',
            'description': 'Adjustable height bar stool with cushioned seat',
            'selling_price': Decimal('8000.00')
        },
        {
            'name': 'Garden Bench',
            'product_type': 'bench',
            'description': 'Outdoor garden bench made of treated wood',
            'selling_price': Decimal('18000.00')
        }
    ]
    
    products = []
    for product_data in products_data:
        product, created = Product.objects.get_or_create(
            name=product_data['name'],
            defaults=product_data
        )
        if created:
            print(f"Created product: {product.name} - Ksh {product.selling_price}")
        products.append(product)
    
    return products

def create_customers():
    """Create test customers"""
    print("\nCreating customers...")
    
    customers_data = [
        {
            'name': 'John Enterprises Ltd',
            'customer_type': 'corporate',
            'phone': '+254722111111',
            'email': 'john@enterprises.co.ke',
            'id_number': 'C12345678',
            'address': 'Kenyatta Avenue, Nairobi',
            'credit_limit': Decimal('500000.00'),
            'loyalty_points': 2500
        },
        {
            'name': 'Mary Wambui',
            'customer_type': 'retail',
            'phone': '+254733222222',
            'email': 'mary.wambui@gmail.com',
            'id_number': '29876543',
            'address': 'Kilimani, Nairobi',
            'credit_limit': Decimal('100000.00'),
            'loyalty_points': 500
        },
        {
            'name': 'Uchumi Supermarket',
            'customer_type': 'wholesale',
            'phone': '+254202987654',
            'email': 'procurement@uchumi.co.ke',
            'id_number': 'C87654321',
            'address': 'Enterprise Road, Nairobi',
            'credit_limit': Decimal('1000000.00'),
            'loyalty_points': 10000
        },
        {
            'name': 'St. Mary\'s School',
            'customer_type': 'institutional',
            'phone': '+25441333444',
            'email': 'admin@stmarys.sc.ke',
            'id_number': 'SCH0012345',
            'address': 'Mombasa Road, Nairobi',
            'credit_limit': Decimal('300000.00'),
            'loyalty_points': 1500
        },
        {
            'name': 'Robert Omondi',
            'customer_type': 'retail',
            'phone': '+254744555555',
            'email': 'robert.omondi@yahoo.com',
            'id_number': '31234567',
            'address': 'Runda, Nairobi',
            'credit_limit': Decimal('150000.00'),
            'loyalty_points': 750
        }
    ]
    
    customers = []
    for customer_data in customers_data:
        customer, created = Customer.objects.get_or_create(
            name=customer_data['name'],
            defaults=customer_data
        )
        if created:
            print(f"Created customer: {customer.name} ({customer.customer_type})")
        customers.append(customer)
    
    return customers

def create_shop_stock(shops, products):
    """Create initial shop stock"""
    print("\nCreating shop stock...")
    
    for shop in shops:
        for product in products:
            # Different stock levels for each shop
            if shop.shop_type == 'main':
                quantity = random.randint(10, 30)
            elif shop.shop_type == 'branch':
                quantity = random.randint(5, 15)
            else:
                quantity = random.randint(2, 8)
            
            stock, created = ShopStock.objects.get_or_create(
                shop=shop,
                product=product,
                defaults={
                    'quantity': quantity,
                    'min_stock_level': 5,
                    'max_stock_level': 50
                }
            )
            if created:
                print(f"Created stock: {product.name} at {shop.name} - {quantity} units")

def create_sales(shops, products, customers, users):
    """Create test sales records"""
    print("\nCreating sales...")
    
    payment_methods = ['cash', 'mpesa', 'card', 'credit']
    statuses = ['completed', 'completed', 'completed', 'completed', 'pending']
    sales_persons = [users.get('sales_person1'), users.get('sales_person2'), 
                     users.get('shop_manager1'), users.get('shop_manager2')]
    
    for i in range(20):  # Create 20 sales (reduced for testing)
        shop = random.choice(shops)
        customer = random.choice(customers)
        sales_person = random.choice(sales_persons)
        
        if not sales_person:
            sales_person = users.get('sales_person1')  # Fallback
        
        # Use timezone-aware datetime
        sale_date = timezone.now() - timedelta(days=random.randint(0, 30), 
                                               hours=random.randint(0, 23))
        
        sale = Sale.objects.create(
            shop=shop,
            customer_name=customer.name,
            customer_phone=customer.phone,
            customer_email=customer.email if random.random() > 0.3 else '',
            sold_by=sales_person,
            payment_method=random.choice(payment_methods),
            status=random.choice(statuses),
            sale_date=sale_date,
            discount_amount=Decimal('0.00') if random.random() > 0.2 else Decimal(str(random.randint(500, 2000))),
            notes='' if random.random() > 0.1 else 'Special order with delivery'
        )
        
        # Add items to sale
        num_items = random.randint(1, 4)
        sale_items = random.sample(products, min(num_items, len(products)))
        
        subtotal = Decimal('0.00')
        for product in sale_items:
            quantity = random.randint(1, 3)
            unit_price = product.selling_price * Decimal('0.9') if random.random() > 0.7 else product.selling_price
            discount = Decimal('0.00') if random.random() > 0.3 else Decimal(str(random.randint(5, 15)))
            
            item = SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity=quantity,
                unit_price=unit_price,
                discount_percentage=discount
            )
            subtotal += item.total_price
        
        # Update sale totals
        sale.subtotal = subtotal
        sale.total_amount = subtotal - sale.discount_amount
        
        if sale.status == 'completed':
            sale.amount_paid = sale.total_amount if random.random() > 0.2 else sale.total_amount * Decimal('0.5')
            sale.balance = sale.total_amount - sale.amount_paid
        else:
            sale.amount_paid = Decimal('0.00')
            sale.balance = sale.total_amount
        
        sale.save()
        
        # Update shop stock if sale is completed
        if sale.status == 'completed':
            for item in sale.items.all():
                shop_stock = ShopStock.objects.filter(shop=shop, product=item.product).first()
                if shop_stock:
                    shop_stock.quantity = max(0, shop_stock.quantity - item.quantity)
                    shop_stock.save()
    
    print(f"Created 20 sales records")

def create_stock_transfers(shops, products, users):
    """Create test stock transfers"""
    print("\nCreating stock transfers...")
    
    for i in range(5):  # Create 5 transfers (reduced for testing)
        if random.random() > 0.5:
            # Manufacturing to shop
            from_location = None
            to_shop = random.choice(shops)
            transfer_type = 'manufacturing_to_shop'
        else:
            # Shop to shop
            shop_pair = random.sample(shops, 2)
            from_location = shop_pair[0]
            to_shop = shop_pair[1]
            transfer_type = 'shop_to_shop'
        
        transfer = StockTransfer.objects.create(
            transfer_type=transfer_type,
            from_location=from_location,
            to_shop=to_shop,
            initiated_by=users.get('store_manager'),
            status=random.choice(['pending', 'in_transit', 'delivered', 'received']),
            transfer_date=timezone.now() - timedelta(days=random.randint(1, 10)),
            expected_delivery_date=timezone.now().date() + timedelta(days=random.randint(1, 3)),
            vehicle_number=f'K{"".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=3))}{random.randint(100, 999)}',
            driver_name=random.choice(['John Driver', 'Peter Mwangi', 'David Ochieng']),
            driver_contact=f'+2547{random.randint(10000000, 99999999)}'
        )
        
        # Add items to transfer
        num_items = random.randint(2, 4)
        transfer_products = random.sample(products, min(num_items, len(products)))
        
        for product in transfer_products:
            quantity = random.randint(3, 8)
            received = quantity if transfer.status == 'received' else random.randint(0, quantity)
            
            StockTransferItem.objects.create(
                stock_transfer=transfer,
                product=product,
                quantity=quantity,
                received_quantity=received
            )
        
        print(f"Created transfer: {transfer.transfer_number} ({transfer.get_status_display()})")

def create_daily_reports(shops):
    """Create test daily sales reports"""
    print("\nCreating daily sales reports...")
    
    for i in range(7):  # Last 7 days
        report_date = timezone.now().date() - timedelta(days=i)
        
        for shop in shops[:2]:  # Only for first 2 shops
            # Check if report already exists
            if not DailySalesReport.objects.filter(shop=shop, report_date=report_date).exists():
                report = DailySalesReport.objects.create(
                    shop=shop,
                    report_date=report_date,
                    total_sales=random.randint(5, 20),
                    total_amount=Decimal(str(random.randint(50000, 200000))),
                    cash_sales=Decimal(str(random.randint(20000, 80000))),
                    mpesa_sales=Decimal(str(random.randint(20000, 80000))),
                    card_sales=Decimal(str(random.randint(5000, 30000))),
                    credit_sales=Decimal(str(random.randint(5000, 30000))),
                    opening_balance=Decimal(str(random.randint(10000, 50000))),
                    closing_balance=Decimal(str(random.randint(10000, 50000))),
                    notes=f'Daily report for {report_date}'
                )
                print(f"Created daily report: {shop.name} - {report_date}")

def main():
    """Main function to create all test data"""
    print("=" * 60)
    print("FurniTrack Pro - Test Data Generator (FIXED)")
    print("=" * 60)
    
    try:
        # Create all test data
        users = create_test_users()
        create_employees(users)
        shops = create_shops(users)
        products = create_products()
        customers = create_customers()
        create_shop_stock(shops, products)
        create_sales(shops, products, customers, users)
        create_stock_transfers(shops, products, users)
        create_daily_reports(shops)
        
        print("\n" + "=" * 60)
        print("TEST DATA CREATION COMPLETE!")
        print("=" * 60)
        
        # Print summary
        print("\n" + "-" * 60)
        print("DATA SUMMARY:")
        print("-" * 60)
        print(f"Users created: {User.objects.count()}")
        print(f"Shops created: {Shop.objects.count()}")
        print(f"Products created: {Product.objects.count()}")
        print(f"Customers created: {Customer.objects.count()}")
        print(f"Shop stock items: {ShopStock.objects.count()}")
        print(f"Sales created: {Sale.objects.count()}")
        print(f"Sale items: {SaleItem.objects.count()}")
        print(f"Stock transfers: {StockTransfer.objects.count()}")
        print(f"Daily reports: {DailySalesReport.objects.count()}")
        
        # Print login credentials
        print("\n" + "-" * 60)
        print("LOGIN CREDENTIALS:")
        print("-" * 60)
        for user in User.objects.all().order_by('role'):
            print(f"Username: {user.username:15} | Password: password123 | Role: {user.get_role_display():20} | Name: {user.get_full_name()}")
        
        print("\n" + "-" * 60)
        print("IMPORTANT URLs:")
        print("-" * 60)
        print("Admin:               http://localhost:8000/admin/")
        print("Login:               http://localhost:8000/login/")
        print("Sales Dashboard:     http://localhost:8000/sales/dashboard/")
        print("Shops:               http://localhost:8000/sales/shops/")
        print("Sales:               http://localhost:8000/sales/sales/")
        print("Customers:           http://localhost:8000/sales/customers/")
        print("Stock Transfers:     http://localhost:8000/sales/transfers/")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()