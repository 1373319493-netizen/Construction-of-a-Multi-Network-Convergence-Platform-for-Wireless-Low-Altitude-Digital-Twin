import os
import subprocess
import sys
from pathlib import Path

# =========================
# 1. 项目路径
# =========================
project_root = Path(__file__).parent
planner_script = project_root / "cost_and_astar.py"

network_file = project_root / "network_eval.csv"
power_file = project_root / "power_eval.csv"

# =========================
# 2. 起点终点（测试用）
# =========================
START_POS = (0.0, 0.0, 10.0)
GOAL_POS  = (90.0, 90.0, 55.0)

# =========================
# 3. 如果没有数据 → 自动生成
# =========================
def generate_test_data():
    print("⚠ 未检测到数据文件，自动生成测试数据...")

    import pandas as pd
    import numpy as np
    import random

    rows = []
    point_id = 1

    x_vals = [i * 10 for i in range(10)]
    y_vals = [i * 10 for i in range(10)]
    z_vals = [10 + i * 5 for i in range(10)]

    for x in x_vals:
        for y in y_vals:
            for z in z_vals:

                effective_snr_db = random.uniform(5, 20)
                num_paths = random.randint(1, 5)
                rms_delay = random.uniform(1, 10)

                throughput = random.uniform(20, 100)
                delay = random.uniform(5, 40)
                loss = random.uniform(0.0, 0.05)

                bs_energy = random.uniform(800, 3000)

                skipped = 0
                if random.random() < 0.05:
                    skipped = 1
                    effective_snr_db = np.nan

                rows.append({
                    "point_id": point_id,
                    "x": x,
                    "y": y,
                    "z": z,
                    "num_paths": num_paths,
                    "effective_snr_db": effective_snr_db,
                    "rms_delay_spread_ns": rms_delay,
                    "throughput_mbps": throughput,
                    "delay_ms": delay,
                    "loss_rate": loss,
                    "bs_energy_j": bs_energy,
                    "skipped": skipped
                })

                point_id += 1

    pd.DataFrame(rows).to_csv(network_file, index=False, encoding="utf-8-sig")

    power_rows = []
    for t in range(20):
        power_rows.append({
            "time": t,
            "bus": "bus1",
            "voltage_pu": random.uniform(0.95, 1.0),
            "load_kw": random.uniform(100, 130)
        })

    pd.DataFrame(power_rows).to_csv(power_file, index=False, encoding="utf-8-sig")

    print("✔ 测试数据生成完成")


# =========================
# 4. 检查数据
# =========================
if not network_file.exists() or not power_file.exists():
    generate_test_data()
else:
    print("✔ 已检测到数据文件")

# =========================
# 5. 调用路径规划
# =========================
print("\n=== 开始路径规划测试 ===")
print(f"起点: {START_POS}")
print(f"终点: {GOAL_POS}")

cmd = [
    sys.executable,
    str(planner_script),

    "--start_x", str(START_POS[0]),
    "--start_y", str(START_POS[1]),
    "--start_z", str(START_POS[2]),

    "--goal_x", str(GOAL_POS[0]),
    "--goal_y", str(GOAL_POS[1]),
    "--goal_z", str(GOAL_POS[2]),
]

result = subprocess.run(cmd, cwd=str(project_root))

print("\n路径规划返回码:", result.returncode)

if result.returncode != 0:
    print("❌ 路径规划失败")
else:
    print("✔ 路径规划成功")