# Generate 2400 values:
# - 80% gradual rise from 0 to 200
# - Then instant sharp drop to 0
# - Remaining 20% stay at 0

total_values = 750

rise_count = int(total_values * 0.8)  # 1920
zero_count = total_values - rise_count  # 480

values = []

# Gradual rise from 0 to 200
for i in range(rise_count):
    value = (i / (rise_count - 1)) * 200
    values.append(int(value))

# Instant drop to 0 and remain there
values.extend([0] * zero_count)

# Print result
print(values)

# Check length
print("Total values:", len(values))
