# Create a phonebook dictionary with initial entries
phonebook = {"Jessica": "111-0101", "Mathew": "111-0102", "Charlie": "111-0103"}

# Demonstrate fast lookup by name
lookup_name = "Mathew"
print(f"Lookup result for '{lookup_name}': {phonebook[lookup_name]}")

print("\nPhonebook before updating Mathew's number:")
print(phonebook)

# Overwrite Mathew's phone number
phonebook["Mathew"] = "111-9999"

print("\nPhonebook after overwriting Mathew's number:")
print(phonebook)