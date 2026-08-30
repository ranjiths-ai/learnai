# Create a list of shopping items with duplicate entries
shopping_list = ["apple", "banana", "apple", "milk", "bread","milk", "eggs", "banana"]

# Print the list to demonstrate that order and duplicates are preserved
shopping_list = list(dict.fromkeys(shopping_list))  # Remove duplicates while preserving order
print("Shopping List:")
print(sorted(shopping_list))