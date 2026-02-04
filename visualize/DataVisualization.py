import random
import matplotlib.pyplot as plt


def generate_sample_data(num_points=4800, pattern=1):
    rise_points = int(num_points * (26.0 / 30.0))
    data = []
    max_pressure = 200

    if pattern == 1:
        # Pattern 1: Quadratic (Smooth acceleration)
        for i in range(rise_points):
            progress = i / rise_points
            base_value = max_pressure * (progress**2)
            noise = random.uniform(-3, 3)
            value = base_value + noise
            data.append(max(0, min(max_pressure, value)))

    elif pattern == 2:
        # Pattern 2: Linear (Steady rise)
        for i in range(rise_points):
            progress = i / rise_points
            base_value = max_pressure * progress
            noise = random.uniform(-8, 8)
            value = base_value + noise
            data.append(max(0, min(max_pressure, value)))

    # Sudden drop to 0 for both patterns
    for _ in range(num_points - rise_points):
        data.append(0)

    return data[:num_points]


# --- Visualization ---
p1_data = generate_sample_data(pattern=1)
p2_data = generate_sample_data(pattern=2)

plt.figure(figsize=(12, 6))
plt.plot(p1_data, label="Pattern 1: Quadratic (Smooth)", color="blue", alpha=0.7)
plt.plot(p2_data, label="Pattern 2: Linear (Steady)", color="orange", alpha=0.7)

plt.title("Pressure Build-up Patterns (0 to 200K)")
plt.xlabel("Data Points (Time)")
plt.ylabel("Pressure Value")
plt.legend()
plt.grid(True, linestyle="--", alpha=0.6)
plt.show()

# --- Snapshot of values ---
print(f"{'Index':<10} | {'Pattern 1':<15} | {'Pattern 2':<15}")
print("-" * 45)
for idx in [0, 1000, 2000, 4159, 4161]:  # Start, Mid-points, Peak, Drop
    status = "PEAK" if idx == 4159 else "DROP" if idx == 4161 else "RISE"
    print(f"{idx:<10} | {p1_data[idx]:<15.2f} | {p2_data[idx]:<15.2f} ({status})")
