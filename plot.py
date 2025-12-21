import matplotlib.pyplot as plt
import numpy as np

# -----------------------------
# Axis definitions
# -----------------------------

# X-axis: Time (15 divisions up to 30)
x_ticks = np.arange(0, 31, 2)   # 0,2,4,...,30

# Y-axis: Pressure up to 200K
y_ticks = np.arange(0, 201, 25)  # 0,25,...,200

# -----------------------------
# Create figure
# -----------------------------
plt.figure(figsize=(9, 5))

# Axis limits
plt.xlim(0, 30)
plt.ylim(0, 200)

# Ticks
plt.xticks(x_ticks)
plt.yticks(y_ticks, [f"{y}K" if y != 0 else "0" for y in y_ticks])

# Grid
plt.grid(True, linestyle='-', linewidth=0.8)

# -----------------------------
# Slanted lines (events)
# -----------------------------

# -----------------------------
# Axis labels
# -----------------------------
plt.ylabel("Pressure", fontsize=12)

# Write TIME after the end of the graph
plt.text(
    31, -12, "TIME",
    fontsize=12,
    ha='left',
    va='top'
)

# -----------------------------
# Layout
# -----------------------------
plt.tight_layout()
plt.show()
