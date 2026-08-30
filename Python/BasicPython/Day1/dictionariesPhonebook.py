# Create a phonebook dictionary with initial entries
phonebook = {"Marjuri": "111-0101", "James": "111-0102", "Charlie": "111-0103"}

# Demonstrate fast lookup by name
lookup_name = "James"
print(f"Lookup result for '{lookup_name}': {phonebook[lookup_name]}")

print("\nPhonebook before updating Jame number:")
print(phonebook)

# Overwrite James's phone number
phonebook["James"] = "111-9999"

print("\nPhonebook after overwriting James's number:")
print(phonebook)