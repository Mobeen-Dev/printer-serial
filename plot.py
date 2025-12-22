import matplotlib.pyplot as plt
import numpy as np

# -----------------------------
# Data Generation (Sharp edges)
# -----------------------------
# Define specific points for sharp peaks/valleys
# x coordinates
x_points = np.array([0, 2, 4, 7, 10, 13, 16, 19, 22, 25, 26.9, 27, 30])

# y coordinates (Pressure)
y_points = np.array([10, 60, 30, 90, 50, 130, 80, 195, 110, 160, 160, 0, 0])
# Explanation of points:
# (2, 60), (7, 90), (13, 130), (25, 160) -> Local Maxima
# (19, 195) -> Global Maximum
# (26.9, 160) to (27, 0) -> Sudden crash
# (27, 0) to (30, 0) -> Stays zero for last 3 seconds

# -----------------------------
# Axis definitions
# -----------------------------
x_ticks = np.arange(0, 31, 2)
y_ticks = np.arange(0, 201, 25)

# -----------------------------
# Create figure
# -----------------------------
plt.figure(figsize=(9, 5))

# Plot the line graph with sharp edges (default linear interpolation)
plt.plot(x_points, y_points, color="blue", linewidth=2)

# Axis limits
plt.xlim(0, 30)
plt.ylim(0, 200)

# Ticks
plt.xticks(x_ticks)
plt.yticks(y_ticks, [f"{y}K" if y != 0 else "0" for y in y_ticks])

# Grid
plt.grid(True, linestyle="-", linewidth=0.8)

# -----------------------------
# Labels
# -----------------------------
plt.ylabel("Pressure", fontsize=12)

# Write TIME after the end of the graph
plt.text(31, -12, "TIME", fontsize=12, ha="left", va="top")

# -----------------------------
# Layout
# -----------------------------
plt.tight_layout()
plt.savefig("sharp_pressure_graph.png")
