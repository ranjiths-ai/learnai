# Create a set of visitor IDs
visitor_ids = {101, 102, 103}

print("Initial visitor IDs set:")
print(visitor_ids)

# Add an existing ID again to demonstrate duplicate handling
visitor_ids.add(101)

# Add a new ID to the set
visitor_ids.add(104)

print("\nSet after adding duplicate (101) and new ID (104):")
print(sorted(visitor_ids))