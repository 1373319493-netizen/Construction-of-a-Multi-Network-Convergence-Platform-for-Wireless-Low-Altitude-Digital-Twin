import os
import pandas as pd
import numpy as np
from sionna.rt import load_scene, PlanarArray, Transmitter, Receiver, PathSolver

# =========================
# 1. 加载场景
# =========================
scene = load_scene("input/shu/buildings.xml", merge_shapes=False)

# =========================
# 2. 设置阵列（当前版本必须）
# =========================
scene.tx_array = PlanarArray(
    num_cols=1,
    num_rows=1,
    pattern="iso",
    polarization="V"
)
scene.rx_array = scene.tx_array

# =========================
# 3. 发射机设置
# =========================
tx_pos = np.array([-80.0, 35.0, 35.0], dtype=float)
tx_name = "tx"

if scene.get(tx_name):
    scene.remove(tx_name)

scene.add(
    Transmitter(tx_name, position=tx_pos.tolist(), display_radius=2)
)

# =========================
# 4. 采样参数
# =========================
x_min, x_max = 0, 100
y_min, y_max = 0,100
z_fixed = 20
step = 10

# =========================
# 5. 发射功率 / 噪声
# =========================
tx_power_dbm = 0.0
noise_power_dbm = -90.0

# =========================
# 6. 自动生成采样点
# =========================
points = []
point_id = 1

for x in np.arange(x_min, x_max + step, step):
    for y in np.arange(y_min, y_max + step, step):
        points.append({
            "point_id": point_id,
            "x": float(x),
            "y": float(y),
            "z": float(z_fixed)
        })
        point_id += 1

print(f"共生成 {len(points)} 个采样点")

# =========================
# 7. 创建路径求解器
# =========================
p_solver = PathSolver()

# =========================
# 8. 逐点评估
# =========================
channel_eval_rows = []

for p in points:
    point_id = p["point_id"]
    rx_pos = np.array([p["x"], p["y"], p["z"]], dtype=float)
    rx_name = f"rx-{point_id}"

    if scene.get(rx_name):
        scene.remove(rx_name)

    scene.add(
        Receiver(rx_name, position=rx_pos.tolist(), display_radius=2)
    )

    # 求解路径
    paths = p_solver(scene, max_depth=4, refraction=False)
    num_paths = int(paths.objects.shape[3])

    # 默认值
    path_gain_db = None
    strongest_path_db = None
    mean_delay_ns = None
    rms_delay_spread_ns = None
    path_loss_db = None
    rx_power_dbm = None
    snr_db = None

    # =========================
    # 8.1 从 CIR 提取传播指标
    # =========================
    if num_paths > 0:
        try:
            a, tau = paths.cir()

            a_np = np.array(a)
            tau_np = np.array(tau)

            # 每条路径对应一个时延
            delays = tau_np.reshape(-1)

            if len(delays) > num_paths:
                delays = delays[:num_paths]

            power_all = np.abs(a_np) ** 2

            # 在 a 的形状中找出哪一维是“路径维”
            candidate_axes = [ax for ax, size in enumerate(power_all.shape) if size == num_paths]

            if len(candidate_axes) == 0:
                raise ValueError(
                    f"无法在 a 的形状 {power_all.shape} 中找到与 num_paths={num_paths} 对应的路径维"
                )

            # 一般取最后一个匹配轴
            path_axis = candidate_axes[-1]

            # 对非路径维求和，得到“每条路径一个功率”
            sum_axes = tuple(ax for ax in range(power_all.ndim) if ax != path_axis)
            power_per_path = np.sum(power_all, axis=sum_axes)

            power_per_path = np.array(power_per_path).reshape(-1)

            # 长度对齐
            power_per_path = power_per_path[:num_paths]
            delays = delays[:num_paths]

            valid = power_per_path > 0
            power_per_path = power_per_path[valid]
            delays = delays[valid]

            if len(power_per_path) > 0:
                total_power = np.sum(power_per_path)
                max_power = np.max(power_per_path)

                path_gain_db = 10 * np.log10(total_power)
                strongest_path_db = 10 * np.log10(max_power)

                mean_delay = np.sum(power_per_path * delays) / total_power
                mean_delay_ns = mean_delay * 1e9

                rms_delay = np.sqrt(
                    np.sum(power_per_path * (delays - mean_delay) ** 2) / total_power
                )
                rms_delay_spread_ns = rms_delay * 1e9

                path_loss_db = -path_gain_db
                rx_power_dbm = tx_power_dbm + path_gain_db
                snr_db = rx_power_dbm - noise_power_dbm

        except Exception as e:
            print(f"point_{point_id}: CIR 提取失败: {e}")

    print(
        f"point_{point_id}: ({rx_pos[0]}, {rx_pos[1]}, {rx_pos[2]}), "
        f"路径数={num_paths}, path_gain_db={path_gain_db}, snr_db={snr_db}"
    )

    channel_eval_rows.append({
        "point_id": point_id,
        "x": float(rx_pos[0]),
        "y": float(rx_pos[1]),
        "z": float(rx_pos[2]),
        "num_paths": num_paths,
        "path_gain_db": path_gain_db,
        "strongest_path_db": strongest_path_db,
        "mean_delay_ns": mean_delay_ns,
        "rms_delay_spread_ns": rms_delay_spread_ns,
        "path_loss_db": path_loss_db,
        "rx_power_dbm": rx_power_dbm,
        "snr_db": snr_db
    })

    scene.remove(rx_name)

# =========================
# 9. 输出结果
# =========================
os.makedirs("output", exist_ok=True)

eval_df = pd.DataFrame(channel_eval_rows)
eval_df.to_csv(
    "output/channel_eval.csv",
    index=False,
    encoding="utf-8-sig"
)

print("完成！已生成：output/channel_eval.csv")