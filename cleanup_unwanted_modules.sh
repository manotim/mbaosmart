#!/bin/bash
echo "Cleaning up unwanted module references..."
echo "=========================================="

# List of unwanted modules to clean
UNWANTED_MODULES=("sales" "hr" "dashboard" "purchase" "procurement" "inventory" "production" "reporting")

for module in "${UNWANTED_MODULES[@]}"; do
    echo -e "\nCleaning up '$module' references..."
    
    # 1. Clean Python files
    echo "  Cleaning Python files..."
    find . -name "*.py" -type f -exec sed -i "s/'${module}:/'accounts:/g" {} \; 2>/dev/null
    find . -name "*.py" -type f -exec sed -i "s/\"${module}:/\"accounts:/g" {} \; 2>/dev/null
    
    # 2. Clean HTML templates
    echo "  Cleaning HTML templates..."
    find templates -name "*.html" -type f -exec sed -i "s/{% url '${module}:/{% url 'accounts:/g" {} \; 2>/dev/null
    find templates -name "*.html" -type f -exec sed -i "s/{% url \"${module}:/{% url \"accounts:/g" {} \; 2>/dev/null
    
    # 3. Clean common redirect patterns
    echo "  Cleaning redirect patterns..."
    find . -type f \( -name "*.py" -o -name "*.html" \) -exec sed -i "s/${module}:dashboard/accounts:profile/g" {} \; 2>/dev/null
    find . -type f \( -name "*.py" -o -name "*.html" \) -exec sed -i "s/${module}:home/accounts:profile/g" {} \; 2>/dev/null
    find . -type f \( -name "*.py" -o -name "*.html" \) -exec sed -i "s/${module}:index/accounts:profile/g" {} \; 2>/dev/null
    find . -type f \( -name "*.py" -o -name "*.html" \) -exec sed -i "s/${module}:profile/accounts:profile/g" {} \; 2>/dev/null
done

echo -e "\n=========================================="
echo "Cleanup complete!"
echo ""
echo "You should also check:"
echo "1. Remove unwanted apps from INSTALLED_APPS in settings.py"
echo "2. Remove unwanted URL patterns from urls.py"
echo "3. Remove unwanted app directories if they exist"
