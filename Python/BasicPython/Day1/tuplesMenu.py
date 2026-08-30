# Create a tuple of fixed menu items
menu_items = ("Pizza", "Burger", "Pasta", "Taco", "nachos")

print("Fixed Menu Items:", menu_items)

# Demonstrate immutability by trying to append/modify
try:
    # Attempting to add an item
    menu_items.append("Salad")
except AttributeError as e:
    print("\nAttempting menu_items.append('Salad')...")
    print("Error caught:", e)

try:
    # Attempting to change an item
    menu_items[0] = "Sushi"
except TypeError as e:
    print("\nAttempting menu_items[0] = 'Sushi'...")
    print("Error caught:", e)

print("\nFinal Menu Items remain unchanged:", menu_items)