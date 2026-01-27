# create_inventory_data.py
import os
import sys
import django
from datetime import datetime, timedelta
import random
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mbaosmart_project.settings')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.contrib.auth import get_user_model
from inventory.models import (
    RawMaterialCategory, RawMaterial, 
    InventoryTransaction, StockAdjustment, StockAlert
)
from procurement.models import Supplier, PurchaseOrder, PurchaseOrderItem
from django.utils import timezone

User = get_user_model()

def create_users():
    """Create test users with different roles"""
    users = [
        {
            'username': 'owner',
            'email': 'owner@example.com',
            'first_name': 'John',
            'last_name': 'Kamau',
            'role': 'owner',
            'phone_number': '+254700111111',
            'is_staff': True,
            'is_superuser': True
        },
        {
            'username': 'store_manager',
            'email': 'store@example.com',
            'first_name': 'Mary',
            'last_name': 'Wanjiku',
            'role': 'store_manager',
            'phone_number': '+254700222222',
            'is_staff': True,
            'is_superuser': False
        },
        {
            'username': 'production_manager',
            'email': 'production@example.com',
            'first_name': 'James',
            'last_name': 'Mwangi',
            'role': 'production_manager',
            'phone_number': '+254700333333',
            'is_staff': True,
            'is_superuser': False
        },
        {
            'username': 'fundi',
            'email': 'fundi@example.com',
            'first_name': 'Peter',
            'last_name': 'Ochieng',
            'role': 'fundi',
            'phone_number': '+254700444444',
            'is_staff': False,
            'is_superuser': False
        },
        {
            'username': 'accountant',
            'email': 'accounts@example.com',
            'first_name': 'Sarah',
            'last_name': 'Atieno',
            'role': 'accountant',
            'phone_number': '+254700555555',
            'is_staff': True,
            'is_superuser': False
        }
    ]
    
    created_users = {}
    for user_data in users:
        user, created = User.objects.get_or_create(
            username=user_data['username'],
            defaults={
                'email': user_data['email'],
                'first_name': user_data['first_name'],
                'last_name': user_data['last_name'],
                'role': user_data['role'],
                'phone_number': user_data['phone_number'],
                'is_staff': user_data['is_staff'],
                'is_superuser': user_data.get('is_superuser', False)
            }
        )
        if created:
            user.set_password('password123')
            user.save()
            print(f"Created user: {user.username} (role: {user.role})")
        created_users[user.role] = user  # Use the actual role from the user object
    
    return created_users

def create_categories():
    """Create raw material categories"""
    categories = [
        {'name': 'Timber', 'description': 'All types of wood and timber'},
        {'name': 'Metal', 'description': 'Iron sheets, steel bars, metal fittings'},
        {'name': 'Hardware', 'description': 'Nails, screws, hinges, locks'},
        {'name': 'Finishes', 'description': 'Paint, varnish, polish'},
        {'name': 'Glass & Mirrors', 'description': 'Glass panels, mirrors'},
        {'name': 'Electrical', 'description': 'Wires, switches, sockets'},
        {'name': 'Fasteners', 'description': 'Nails, screws, bolts'},
    ]
    
    created_categories = {}
    for cat_data in categories:
        category, created = RawMaterialCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults={'description': cat_data['description']}
        )
        if created:
            print(f"Created category: {category.name}")
        created_categories[cat_data['name']] = category
    
    return created_categories

def create_suppliers():
    """Create suppliers"""
    suppliers = [
        {
            'name': 'Timber Suppliers Ltd',
            'contact_person': 'David Kiprop',
            'email': 'info@timbersuppliers.co.ke',
            'phone': '+254720111111',
            'address': 'Industrial Area, Nairobi'
        },
        {
            'name': 'Metal Works Kenya',
            'contact_person': 'Samuel Gitonga',
            'email': 'sales@metalworks.co.ke',
            'phone': '+254720222222',
            'address': 'Mombasa Road, Nairobi'
        },
        {
            'name': 'Hardware Wholesalers',
            'contact_person': 'Grace Mumbi',
            'email': 'orders@hardwarewholesalers.co.ke',
            'phone': '+254720333333',
            'address': 'Kariakor, Nairobi'
        }
    ]
    
    created_suppliers = []
    for supplier_data in suppliers:
        supplier, created = Supplier.objects.get_or_create(
            name=supplier_data['name'],
            defaults=supplier_data
        )
        if created:
            print(f"Created supplier: {supplier.name}")
        created_suppliers.append(supplier)
    
    return created_suppliers

def create_raw_materials(categories, suppliers):
    """Create raw materials"""
    materials = [
        {
            'name': 'Pine Wood 2x4',
            'code': 'TIM-001',
            'category': categories['Timber'],
            'unit': 'pcs',
            'unit_price': Decimal('350.00'),
            'min_stock_level': Decimal('20'),
            'max_stock_level': Decimal('100'),
            'current_stock': Decimal('15'),
            'location': 'Main Store - Rack A1',
            'supplier': suppliers[0],
            'notes': '8ft length'
        },
        {
            'name': 'Plywood 1/2"',
            'code': 'TIM-002',
            'category': categories['Timber'],
            'unit': 'sheet',
            'unit_price': Decimal('1200.00'),
            'min_stock_level': Decimal('10'),
            'max_stock_level': Decimal('50'),
            'current_stock': Decimal('25'),
            'location': 'Main Store - Rack A2',
            'supplier': suppliers[0],
            'notes': '4x8 feet sheets'
        },
        {
            'name': 'Iron Sheets G28',
            'code': 'MET-001',
            'category': categories['Metal'],
            'unit': 'sheet',
            'unit_price': Decimal('850.00'),
            'min_stock_level': Decimal('30'),
            'max_stock_level': Decimal('150'),
            'current_stock': Decimal('45'),
            'location': 'Metal Store - Yard',
            'supplier': suppliers[1],
            'notes': 'Colored coated'
        },
        {
            'name': 'Steel Bars 1/2"',
            'code': 'MET-002',
            'category': categories['Metal'],
            'unit': 'pcs',
            'unit_price': Decimal('650.00'),
            'min_stock_level': Decimal('50'),
            'max_stock_level': Decimal('200'),
            'current_stock': Decimal('12'),
            'location': 'Metal Store - Rack B1',
            'supplier': suppliers[1],
            'notes': '12ft length'
        },
        {
            'name': '3" Nails',
            'code': 'HRD-001',
            'category': categories['Hardware'],
            'unit': 'kg',
            'unit_price': Decimal('150.00'),
            'min_stock_level': Decimal('20'),
            'max_stock_level': Decimal('100'),
            'current_stock': Decimal('5'),
            'location': 'Hardware Store - Bin C1',
            'supplier': suppliers[2],
            'notes': 'Galvanized'
        },
        {
            'name': 'Paint White',
            'code': 'FIN-001',
            'category': categories['Finishes'],
            'unit': 'l',
            'unit_price': Decimal('450.00'),
            'min_stock_level': Decimal('30'),
            'max_stock_level': Decimal('150'),
            'current_stock': Decimal('35'),
            'location': 'Paint Store - Shelf D1',
            'supplier': suppliers[2],
            'notes': 'Oil-based, gloss finish'
        },
        {
            'name': 'Glass 6mm Clear',
            'code': 'GLS-001',
            'category': categories['Glass & Mirrors'],
            'unit': 'sheet',
            'unit_price': Decimal('1800.00'),
            'min_stock_level': Decimal('5'),
            'max_stock_level': Decimal('25'),
            'current_stock': Decimal('0'),
            'location': 'Glass Store - Rack E1',
            'supplier': suppliers[1],
            'notes': 'Toughened glass'
        },
        {
            'name': 'Electrical Wire 2.5mm',
            'code': 'ELC-001',
            'category': categories['Electrical'],
            'unit': 'roll',
            'unit_price': Decimal('2800.00'),
            'min_stock_level': Decimal('10'),
            'max_stock_level': Decimal('50'),
            'current_stock': Decimal('8'),
            'location': 'Electrical Store - Box F1',
            'supplier': suppliers[2],
            'notes': 'Copper, PVC insulated'
        },
    ]
    
    created_materials = []
    for material_data in materials:
        material, created = RawMaterial.objects.get_or_create(
            code=material_data['code'],
            defaults=material_data
        )
        if created:
            print(f"Created material: {material.name}")
        created_materials.append(material)
    
    return created_materials

def create_transactions(materials, users):
    """Create inventory transactions"""
    transactions = []
    
    # Purchase transactions
    for i in range(20):
        material = random.choice(materials)
        transaction = InventoryTransaction.objects.create(
            raw_material=material,
            transaction_type='purchase',
            quantity=Decimal(str(random.randint(10, 50))),
            unit_price=material.unit_price,
            reference=f'PO-2024-{random.randint(1000, 9999)}',
            notes=f'Purchase from {material.supplier.name}',
            created_by=users['store_manager'],
            created_at=timezone.now() - timedelta(days=random.randint(1, 90))
        )
        transactions.append(transaction)
    
    # Production usage transactions
    for i in range(15):
        material = random.choice(materials)
        transaction = InventoryTransaction.objects.create(
            raw_material=material,
            transaction_type='production_usage',
            quantity=Decimal(str(random.randint(1, 10))),
            reference=f'PROD-{random.randint(100, 999)}',
            notes='Used in furniture production',
            created_by=users['production_manager'],  # Fixed key name
            created_at=timezone.now() - timedelta(days=random.randint(1, 60))
        )
        transactions.append(transaction)
    
    print(f"Created {len(transactions)} transactions")
    return transactions

def create_stock_adjustments(materials, users):
    """Create stock adjustments"""
    adjustments = []
    
    for material in materials[:3]:  # Adjust first 3 materials
        adjustment = StockAdjustment.objects.create(
            raw_material=material,
            adjustment_type=random.choice(['add', 'remove']),
            quantity=Decimal(str(random.randint(1, 10))),
            reason='physical_count',
            notes='Adjusted after physical stock count',
            adjusted_by=users['store_manager'],
            previous_stock=material.current_stock,
            new_stock=material.current_stock + Decimal(str(random.randint(1, 10)))
        )
        adjustments.append(adjustment)
    
    print(f"Created {len(adjustments)} stock adjustments")
    return adjustments

def create_stock_alerts(materials):
    """Create stock alerts based on current stock levels"""
    alerts = []
    
    for material in materials:
        if material.current_stock <= material.min_stock_level:
            alert_type = 'out_of_stock' if material.current_stock <= 0 else 'low_stock'
            
            if not StockAlert.objects.filter(raw_material=material, is_active=True).exists():
                alert = StockAlert.objects.create(
                    raw_material=material,
                    alert_type=alert_type,
                    message=f'{material.name} is {"out of stock" if material.current_stock <= 0 else "below minimum stock level"}. Current: {material.current_stock} {material.unit}',
                    is_active=True
                )
                alerts.append(alert)
    
    print(f"Created {len(alerts)} stock alerts")
    return alerts

def main():
    """Main function to create all test data"""
    print("Starting test data creation...")
    
    # Create test data
    users = create_users()
    print("\nAvailable user keys:", list(users.keys()))
    
    categories = create_categories()
    suppliers = create_suppliers()
    materials = create_raw_materials(categories, suppliers)
    transactions = create_transactions(materials, users)
    adjustments = create_stock_adjustments(materials, users)
    alerts = create_stock_alerts(materials)
    
    print("\n" + "="*50)
    print("TEST DATA CREATION COMPLETE!")
    print("="*50)
    print("\nTest Users Created (password: 'password123'):")
    for role, user in users.items():
        print(f"  • {role}: username='{user.username}'")
    
    print("\nLogin Credentials Summary:")
    print("  • Owner: username='owner', password='password123'")
    print("  • Store Manager: username='store_manager', password='password123'")
    print("  • Production Manager: username='production_manager', password='password123'")
    print("  • Fundi/Worker: username='fundi', password='password123'")
    print("  • Accountant: username='accountant', password='password123'")
    
    print("\nTest Materials Created:")
    print("  • Pine Wood 2x4 (Low stock: 15/20 min)")
    print("  • Steel Bars 1/2\" (Low stock: 12/50 min)")
    print("  • 3\" Nails (Low stock: 5/20 min)")
    print("  • Glass 6mm Clear (Out of stock)")
    print("  • Electrical Wire 2.5mm (Low stock: 8/10 min)")
    
    print("\nAccess the application at: http://localhost:8000/")
    print("Access the admin panel at: http://localhost:8000/admin/")

if __name__ == '__main__':
    main()