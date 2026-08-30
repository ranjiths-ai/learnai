# Define 2D coordinates as a tuple (x, y)
point = (10, 20)

print("Original Point:", point)
print(f"X coordinate: {point[0]}, Y coordinate: {point[1]}")

# Demonstrate immutability by trying to modify an element
try:
    point[0] = 15
except TypeError as e:
    print("\nAttempted to change point[0] to 15...")
    print("Error caught:", e)

# Print the tuple again to confirm it remains unchanged
print("\nPoint after modification attempt:", point)