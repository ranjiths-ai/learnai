# Initial list of 5 daily tasks
daily_tasks = [
    "Check emails",
    "Attend standup meeting",
    "Review pull requests",
    "Write documentation",
    "Submit daily status report",
]

print("Initial Daily Tasks:")
print(daily_tasks)
print("-" * 40)

# Simulate finishing tasks using remove
completed_task_1 = "Check emails"
daily_tasks.remove(completed_task_1)
print(f"Finished: '{completed_task_1}'")
print("Remaining Tasks:", daily_tasks)
print("-" * 40)

completed_task_2 = "Attend standup meeting"
daily_tasks.remove(completed_task_2)
print(f"Finished: '{completed_task_2}'")
print("Remaining Tasks:", daily_tasks)
print("-" * 40)

completed_task_3 = "Review pull requests"
daily_tasks.remove(completed_task_3)
print(f"Finished: '{completed_task_3}'")
print("Remaining Tasks:", daily_tasks)
print("-" * 40)

# Add a new task using append
new_task = "Prepare presentation for tomorrow"
daily_tasks.append(new_task)
print(f"Added new task: '{new_task}'")
print("Updated Task List:", daily_tasks)
print("-" * 40)

new_task = "Give a Project demo to clients"
daily_tasks.append(new_task)
print(f"Added new task: '{new_task}'")
print("Updated Task List:", daily_tasks)