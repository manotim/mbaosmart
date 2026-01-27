# assign_permissions.py
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mbaosmart_project.settings')
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from inventory.models import RawMaterial, RawMaterialCategory, InventoryTransaction, StockAdjustment, StockAlert
from procurement.models import Supplier, PurchaseOrder

User = get_user_model()

def assign_permissions():
    print("Assigning permissions to users...")
    
    # Get users
    users = {
        'owner': User.objects.get(username='owner'),
        'store_manager': User.objects.get(username='store_manager'),
        'production_manager': User.objects.get(username='production_manager'),
        'fundi': User.objects.get(username='fundi'),
        'accountant': User.objects.get(username='accountant'),
    }
    
    # Get or create groups
    groups = {}
    for group_name in ['Inventory Managers', 'Production Managers', 'Fundi Workers', 'Accountants']:
        group, created = Group.objects.get_or_create(name=group_name)
        groups[group_name] = group
        if created:
            print(f"Created group: {group_name}")
    
    # INVENTORY PERMISSIONS
    inventory_perms = [
        'view_rawmaterial', 'add_rawmaterial', 'change_rawmaterial', 'delete_rawmaterial',
        'view_rawmaterialcategory', 'add_rawmaterialcategory', 'change_rawmaterialcategory', 'delete_rawmaterialcategory',
        'view_inventorytransaction', 'add_inventorytransaction', 'change_inventorytransaction', 'delete_inventorytransaction',
        'view_stockadjustment', 'add_stockadjustment', 'change_stockadjustment', 'delete_stockadjustment',
        'view_stockalert', 'change_stockalert',
    ]
    
    # Get inventory permissions
    inventory_content_types = ContentType.objects.get_for_models(
        RawMaterial, RawMaterialCategory, InventoryTransaction, StockAdjustment, StockAlert
    )
    
    all_perms = {}
    for content_type in inventory_content_types.values():
        for codename in inventory_perms:
            try:
                perm = Permission.objects.get(
                    content_type=content_type,
                    codename=codename
                )
                all_perms[codename] = perm
            except Permission.DoesNotExist:
                print(f"Permission not found: {codename}")
    
    # PROCUREMENT PERMISSIONS
    procurement_perms = [
        'view_supplier', 'add_supplier', 'change_supplier', 'delete_supplier',
        'view_purchaseorder', 'add_purchaseorder', 'change_purchaseorder', 'delete_purchaseorder',
    ]
    
    # Assign permissions to groups
    
    # Inventory Managers group
    inv_group = groups['Inventory Managers']
    inv_group.permissions.set([
        all_perms['view_rawmaterial'], all_perms['add_rawmaterial'], all_perms['change_rawmaterial'],
        all_perms['view_rawmaterialcategory'], all_perms['add_rawmaterialcategory'], all_perms['change_rawmaterialcategory'],
        all_perms['view_inventorytransaction'], all_perms['add_inventorytransaction'],
        all_perms['view_stockadjustment'], all_perms['add_stockadjustment'],
        all_perms['view_stockalert'], all_perms['change_stockalert'],
    ])
    
    # Production Managers group
    prod_group = groups['Production Managers']
    prod_group.permissions.set([
        all_perms['view_rawmaterial'],
        all_perms['view_inventorytransaction'], all_perms['add_inventorytransaction'],
        all_perms['view_stockalert'],
    ])
    
    # Accountants group
    acc_group = groups['Accountants']
    acc_group.permissions.set([
        all_perms['view_rawmaterial'],
        all_perms['view_inventorytransaction'],
        all_perms['view_stockadjustment'],
        all_perms['view_stockalert'],
    ])
    
    # Fundi Workers group (minimal permissions)
    fundi_group = groups['Fundi Workers']
    fundi_group.permissions.set([
        all_perms['view_rawmaterial'],
    ])
    
    # Assign users to groups
    users['store_manager'].groups.add(groups['Inventory Managers'])
    users['production_manager'].groups.add(groups['Production Managers'])
    users['accountant'].groups.add(groups['Accountants'])
    users['fundi'].groups.add(groups['Fundi Workers'])
    
    # Owner gets all permissions
    users['owner'].user_permissions.set(Permission.objects.all())
    users['owner'].is_superuser = True
    users['owner'].is_staff = True
    users['owner'].save()
    
    # Make sure store_manager has staff access
    users['store_manager'].is_staff = True
    users['store_manager'].save()
    
    users['production_manager'].is_staff = True
    users['production_manager'].save()
    
    users['accountant'].is_staff = True
    users['accountant'].save()
    
    print("\n" + "="*50)
    print("PERMISSIONS ASSIGNED SUCCESSFULLY!")
    print("="*50)
    
    print("\nUser Permissions Summary:")
    for username, user in users.items():
        perms = user.get_all_permissions()
        print(f"\n{username.upper()}:")
        print(f"  Groups: {', '.join([g.name for g in user.groups.all()])}")
        print(f"  Staff: {user.is_staff}")
        print(f"  Superuser: {user.is_superuser}")
        print(f"  Total permissions: {len(perms)}")
        if len(perms) < 10:
            for perm in perms:
                print(f"    - {perm}")

if __name__ == '__main__':
    assign_permissions()