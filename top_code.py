import random
import matplotlib.pyplot as plt


def generate_sample_data(num_points=4800):
    data = []

    cycle_len = num_points

    for c in range(1):
        # 1️⃣ Build-up curve
        for i in range(int(cycle_len * 0.4)):
            p = i / (cycle_len * 0.4)
            val = 150 * (p**2) + random.uniform(-5, 5)
            data.append(max(0, val))

        # # 2️⃣ Peak hold
        # for _ in range(int(cycle_len * 0.02)):
        #     data.append(180 + random.uniform(-8, 8))

        # 3️⃣ Sudden drop (brick break)
        data.append(5)

        # 4️⃣ Recovery tail
        remaining = cycle_len - len(data) % cycle_len
        for i in range(remaining):
            p = i / remaining
            val = 40 * (1 - p) + random.uniform(-3, 3)
            data.append(max(0, val))

    return data[:num_points]


def generate_graph_points(data, graph_width=480, graph_height=1200, margin=10):
    if not data:
        raise ValueError("Empty data")

    # --- Downsample to 1200 points using max pooling ---
    if len(data) > graph_height:
        ratio = len(data) / graph_height
        reduced = []
        for i in range(graph_height):
            start = int(i * ratio)
            end = int((i + 1) * ratio)
            segment = data[start:end]
            reduced.append(max(segment) if segment else data[start])
        # data = reduced

        data = moving_average(reduced, window=11)

    # Pad if smaller
    elif len(data) < graph_height:
        data = data + [0] * (graph_height - len(data))

    # --- Scaling ---
    dmin = min(data)
    dmax = max(data)
    center_x = graph_width // 2

    if dmax - dmin == 0:
        scale = 0
    else:
        scale = (graph_width // 2 - margin) / (dmax - dmin)

    # --- Convert to pixel points ---
    points = []
    for y in range(graph_height):
        val = data[y]
        extent = int((val - dmin) * scale)
        x = center_x + extent
        points.append((x, y))

    return points


def draw_line(bitmap, x0, y0, x1, y1):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy

    while True:
        if 0 <= y0 < len(bitmap) and 0 <= x0 < len(bitmap[0]):
            bitmap[y0][x0] = 1

        if x0 == x1 and y0 == y1:
            break

        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def create_graph_bitmap(data, width=480, height=1200):
    bitmap = [[0 for _ in range(width)] for _ in range(height)]

    points = generate_graph_points(data, width, height)

    px, py = points[0]
    for x, y in points[1:]:
        draw_line(bitmap, px, py, x, y)
        px, py = x, y

    return bitmap, points


def moving_average(data, window=5):
    if window < 2:
        return data[:]

    half = window // 2
    out = []

    for i in range(len(data)):
        s = 0
        c = 0
        for j in range(i - half, i + half + 1):
            if 0 <= j < len(data):
                s += data[j]
                c += 1
        out.append(s / c)

    return out


def preview_graph_org(points, width=480, height=1200):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    plt.figure(figsize=(5, 10))
    plt.plot(xs, ys, "k")
    plt.axvline(width // 2, linestyle="--")
    plt.gca().invert_yaxis()
    plt.title("Thermal Printer Graph Preview")
    plt.show()


def preview_graph(points, width=480, height=1200):
    # Swap axes
    xs = [p[1] for p in points]  # time now on X
    ys = [p[0] for p in points]  # magnitude now on Y

    plt.figure(figsize=(12, 4))
    plt.plot(xs, ys, "k")
    plt.axhline(width // 2, linestyle="--")  # center line becomes horizontal
    plt.title("Rotated Graph Preview (Time → X axis)")
    plt.xlabel("Time / Sample Index")
    plt.ylabel("Magnitude (Pixel X Position)")
    plt.grid(True, alpha=0.3)
    plt.show()


if __name__ == "__main__":
    print("Generating 4800 sample sensor values...")
    data = generate_sample_data(4800)

    # clean_data = moving_average(data, window=21)
    # clean_data = moving_average(clean_data, window=11)
    # clean_data = moving_average(clean_data, window=11)

    print("Creating graph bitmap...")
    bitmap, points = create_graph_bitmap(data)

    print("Done.")
    print("Total points:", len(points))
    print("Bitmap size:", len(bitmap), "x", len(bitmap[0]))
    preview_graph(points)
