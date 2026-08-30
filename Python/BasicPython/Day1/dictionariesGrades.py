# Create a dictionary with student names as keys and marks as values
student_marks = {"Marjuri": 85, "James": 92, "Charlie": 78}

# Retrieve one student's grade
student_name = "James"
print(f"{student_name}'s mark: {student_marks[student_name]}")

# Add a new student
student_marks["David"] = 88
print("\nAfter adding David:")
print(student_marks)

# Update an existing grade
student_marks["Jessica"] = 90
print("\nAfter updating Jessica's mark:")
print(student_marks) 

# Add a new student
student_marks["Mary"] = 68
print("\nAfter adding Mary:")
print(student_marks)