import math
import heapq
import argparse
import numpy as np
import pandas as pd


# =========================================================
# 0. 命令行参数：从 controller 传入起点终点坐标
# =========================================================
parser = argparse.ArgumentParser()
parser.add_argument("--start_x", type=float, required=True)
parser.add_argument("--start_y", type=float, required=True)
parser.add_argument("--start_z", type=float, required=True)
parser.add_argument("--goal_x", type=float, required=True)
parser.add_argument("--goal_y", type=float, required=True)
parser.add_argument("--goal_z", type=float, required=True)
args = parser.parse_args()

start_pos = (args.start_x, args.start_y, args.start_z)
goal_pos = (args.goal_x, args.goal_y, args.goal_z)

print(f"[路径规划] 起点坐标 = {start_pos}")
print(f"[路径规划] 终点坐标 = {goal_pos}")

# =========================================================
# 1. 文件路径
# =========================================================
NETWORK_CSV = "network_eval.csv"
POWER_CSV = "power_eval.csv"
COST_OUTPUT_CSV = "path_planning_input.csv"
PATH_OUTPUT_CSV = "planned_path.csv"

# =========================================================
# 2. 参数设置
# =========================================================
W_COMM = 0.35
W_NET = 0.35
W_BS = 0.15
W_POWER = 0.15

COMM_W_SNR = 0.5
COMM_W_PATHS = 0.2
COMM_W_DELAY_SPREAD = 0.3

NET_W_THROUGHPUT = 0.5
NET_W_DELAY = 0.3
NET_W_LOSS = 0.2

S_MAX = 20.0
N_MAX = 5.0
D_MAX = 10.0
T_MAX = 100.0
L_MAX = 50.0
R_MAX = 0.1

V_REF = 0.95

MOVE_COST_WEIGHT = 1.0
HEURISTIC_WEIGHT = 1.0


# =========================================================
# 3. 工具函数
# =========================================================
def clamp(value, min_val, max_val):
    return max(min_val, min(value, max_val))


def safe_norm_positive(value, max_val):
    if pd.isna(value):
        return 0.0
    if max_val <= 0:
        return 0.0
    return clamp(value / max_val, 0.0, 1.0)


def safe_norm_range(value, min_val, max_val):
    if pd.isna(value):
        return 0.0
    if max_val <= min_val:
        return 0.0
    return clamp((value - min_val) / (max_val - min_val), 0.0, 1.0)


def euclidean_distance(a, b):
    return math.sqrt(
        (a[0] - b[0]) ** 2 +
        (a[1] - b[1]) ** 2 +
        (a[2] - b[2]) ** 2
    )


def infer_step(values):
    values = sorted(set(float(v) for v in values))
    if len(values) < 2:
        return None
    diffs = [round(values[i + 1] - values[i], 6) for i in range(len(values) - 1)]
    diffs = [d for d in diffs if d > 0]
    if not diffs:
        return None
    return min(diffs)


def find_nearest_node(pos, node_list):
    min_dist = float("inf")
    best_node = None

    for node in node_list:
        dist = euclidean_distance(pos, node)
        if dist < min_dist:
            min_dist = dist
            best_node = node

    return best_node, min_dist


# =========================================================
# 4. 读取原始数据
# =========================================================
net_df = pd.read_csv(NETWORK_CSV)
power_df = pd.read_csv(POWER_CSV)

print("已读取文件：")
print(f"  network rows = {len(net_df)}")
print(f"  power rows   = {len(power_df)}")


# =========================================================
# 5. 计算全局 power_cost
# =========================================================
avg_voltage = power_df["voltage_pu"].mean()
avg_load = power_df["load_kw"].mean()
max_load = power_df["load_kw"].max()

voltage_penalty = (1.0 - avg_voltage) / (1.0 - V_REF)
voltage_penalty = clamp(voltage_penalty, 0.0, 1.0)

load_penalty = avg_load / max_load if max_load > 0 else 0.0
load_penalty = clamp(load_penalty, 0.0, 1.0)

power_cost_global = 0.5 * voltage_penalty + 0.5 * load_penalty

print("\n全局电力惩罚项：")
print(f"  avg_voltage       = {avg_voltage:.6f}")
print(f"  avg_load          = {avg_load:.6f}")
print(f"  max_load          = {max_load:.6f}")
print(f"  power_cost_global = {power_cost_global:.6f}")


# =========================================================
# 6. 计算节点代价
# =========================================================
bs_energy_min = net_df["bs_energy_j"].min()
bs_energy_max = net_df["bs_energy_j"].max()


def compute_comm_cost(row):
    effective_snr_db = row["effective_snr_db"]
    num_paths = row["num_paths"]
    rms_delay_spread_ns = row["rms_delay_spread_ns"]

    snr_term = 1.0 - safe_norm_positive(effective_snr_db, S_MAX)
    path_term = 1.0 - safe_norm_positive(num_paths, N_MAX)

    if pd.isna(rms_delay_spread_ns):
        delay_spread_term = 1.0
    else:
        delay_spread_term = clamp(rms_delay_spread_ns / D_MAX, 0.0, 1.0)

    return (
        COMM_W_SNR * snr_term +
        COMM_W_PATHS * path_term +
        COMM_W_DELAY_SPREAD * delay_spread_term
    )


def compute_net_cost(row):
    throughput_mbps = row["throughput_mbps"]
    delay_ms = row["delay_ms"]
    loss_rate = row["loss_rate"]

    throughput_term = 1.0 - safe_norm_positive(throughput_mbps, T_MAX)
    delay_term = clamp(delay_ms / L_MAX, 0.0, 1.0)
    loss_term = clamp(loss_rate / R_MAX, 0.0, 1.0)

    return (
        NET_W_THROUGHPUT * throughput_term +
        NET_W_DELAY * delay_term +
        NET_W_LOSS * loss_term
    )


def compute_bs_cost(row):
    return safe_norm_range(row["bs_energy_j"], bs_energy_min, bs_energy_max)


def compute_total_cost(row):
    skipped = row["skipped"]
    effective_snr_db = row["effective_snr_db"]

    if skipped == 1 or pd.isna(effective_snr_db):
        return pd.Series({
            "valid": 0,
            "comm_cost": math.inf,
            "net_cost": math.inf,
            "bs_cost": math.inf,
            "power_cost": power_cost_global,
            "total_cost": math.inf
        })

    comm_cost = compute_comm_cost(row)
    net_cost = compute_net_cost(row)
    bs_cost = compute_bs_cost(row)
    power_cost = power_cost_global

    total_cost = (
        W_COMM * comm_cost +
        W_NET * net_cost +
        W_BS * bs_cost +
        W_POWER * power_cost
    )

    return pd.Series({
        "valid": 1,
        "comm_cost": comm_cost,
        "net_cost": net_cost,
        "bs_cost": bs_cost,
        "power_cost": power_cost,
        "total_cost": total_cost
    })


cost_df = net_df.apply(compute_total_cost, axis=1)
result_df = pd.concat([net_df, cost_df], axis=1)
result_df.to_csv(COST_OUTPUT_CSV, index=False, encoding="utf-8-sig")

print(f"\n已生成代价文件：{COST_OUTPUT_CSV}")

# =========================================================
# 7. A* 规划
# =========================================================
valid_df = result_df[(result_df["valid"] == 1) & np.isfinite(result_df["total_cost"])].copy()

if valid_df.empty:
    raise ValueError("没有任何有效节点，无法进行路径规划。")

def to_node(row):
    return (float(row["x"]), float(row["y"]), float(row["z"]))

valid_df["node"] = valid_df.apply(to_node, axis=1)

node_cost = {}
node_to_point_id = {}

for _, row in valid_df.iterrows():
    node = row["node"]
    node_cost[node] = float(row["total_cost"])
    node_to_point_id[node] = int(row["point_id"])

node_list = list(node_cost.keys())

start_node, start_dist = find_nearest_node(start_pos, node_list)
goal_node, goal_dist = find_nearest_node(goal_pos, node_list)

if start_node is None:
    raise ValueError("起点无法映射到任何有效节点。")

if goal_node is None:
    raise ValueError("终点无法映射到任何有效节点。")

print(f"[路径规划] 起点映射到节点: {start_node}, 距离={start_dist:.2f}")
print(f"[路径规划] 终点映射到节点: {goal_node}, 距离={goal_dist:.2f}")

# -------------------------
# 关键保护 1：
# 如果用户设定了不同的起终点坐标，但它们被压到了同一个有效节点，
# 在本项目中应视为“终点不可达”或“地图分辨率不足”，直接报错
# -------------------------
if start_node == goal_node and start_pos != goal_pos:
    raise ValueError(
        "起点和终点被映射到了同一个有效节点，说明当前有效节点过少，"
        "无法支持从起点到终点的有效路径规划。"
    )

x_step = infer_step(valid_df["x"].tolist())
y_step = infer_step(valid_df["y"].tolist())
z_step = infer_step(valid_df["z"].tolist())

node_set = set(node_list)

print("\n自动识别步长：")
print(f"  x_step = {x_step}")
print(f"  y_step = {y_step}")
print(f"  z_step = {z_step}")


def get_neighbors(node):
    x, y, z = node
    candidates = []

    if x_step is not None:
        candidates.append((x + x_step, y, z))
        candidates.append((x - x_step, y, z))

    if y_step is not None:
        candidates.append((x, y + y_step, z))
        candidates.append((x, y - y_step, z))

    if z_step is not None:
        candidates.append((x, y, z + z_step))
        candidates.append((x, y, z - z_step))

    return [cand for cand in candidates if cand in node_set]


def heuristic(a, b):
    return HEURISTIC_WEIGHT * euclidean_distance(a, b)


def reconstruct_path(came_from, current):
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def astar(start, goal):
    open_heap = []
    heapq.heappush(open_heap, (0.0, start))

    came_from = {}
    g_score = {start: 0.0}
    closed_set = set()

    while open_heap:
        _, current = heapq.heappop(open_heap)

        if current in closed_set:
            continue

        if current == goal:
            return reconstruct_path(came_from, current), g_score[current]

        closed_set.add(current)

        for neighbor in get_neighbors(current):
            if neighbor in closed_set:
                continue

            move_cost = MOVE_COST_WEIGHT * euclidean_distance(current, neighbor)
            tentative_g = g_score[current] + node_cost[neighbor] + move_cost

            if (neighbor not in g_score) or (tentative_g < g_score[neighbor]):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f = tentative_g + heuristic(neighbor, goal)
                heapq.heappush(open_heap, (f, neighbor))

    return None, math.inf


path, total_path_cost = astar(start_node, goal_node)

if path is None:
    raise ValueError("未找到从起点到终点的可行路径，终点不可达。")

# -------------------------
# 关键保护 2：
# 路径长度不足，说明没有真实移动
# -------------------------
if len(path) < 2:
    raise ValueError(
        "路径规划失败：虽然返回了路径，但路径长度不足，未形成从起点到终点的有效飞行轨迹。"
    )

print("\n找到路径：")
path_rows = []
for order, node in enumerate(path, start=1):
    pid = node_to_point_id[node]
    print(f"{order:02d}. point_id={pid}, node={node}, node_cost={node_cost[node]:.6f}")
    path_rows.append({
        "path_order": order,
        "point_id": pid,
        "x": node[0],
        "y": node[1],
        "z": node[2],
        "node_cost": node_cost[node]
    })

path_df = pd.DataFrame(path_rows)
path_df.to_csv(PATH_OUTPUT_CSV, index=False, encoding="utf-8-sig")

print(f"\n路径总代价 = {total_path_cost:.6f}")
print(f"已导出路径文件：{PATH_OUTPUT_CSV}")