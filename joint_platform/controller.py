import shutil
import subprocess
from pathlib import Path

from vm_bridge import (
    send_channel_eval_to_vm,
    wait_for_vm_outputs,
    get_vm_result_paths,
)

# =========================
# 1. 项目根目录
# =========================
project_root = Path(r"C:\Users\13733\Desktop\毕设相关\joint_platform")

# =========================
# 2. 各环境解释器
# =========================
airsim_python = Path(r"C:\Users\13733\anaconda3\envs\bt_py39\python.exe")
sionna_python = Path(r"C:\Users\13733\anaconda3\envs\sionna_rt\python.exe")

planner_python = airsim_python

# =========================
# 3. 各模块脚本
# =========================
sionna_script = project_root / "channel_part" / "test.py"
planner_script = project_root / "path_planning_part" / "cost_and_astar.py"
airsim_script = project_root / "airsim_part" / "airsim_replay.py"

# =========================
# 4. 起点终点（用坐标定义）
# =========================
START_POS = (0.0, 0.0, 10.0)
GOAL_POS  = (90.0, 90.0, 55.0)

# =========================
# 5. 关键文件路径
# =========================
channel_eval_file = project_root / "channel_part" / "output" / "channel_eval.csv"

planner_network_file = project_root / "path_planning_part" / "network_eval.csv"
planner_power_file = project_root / "path_planning_part" / "power_eval.csv"

path_planning_input_file = project_root / "path_planning_part" / "path_planning_input.csv"
planned_path_src = project_root / "path_planning_part" / "planned_path.csv"

planned_path_dst = project_root / "airsim_part" / "planned_path.csv"

# =========================
# 6. Step 1: Sionna 计算各点评估表
# =========================
print("=== Step 1: 网格采样点评估（Sionna） ===")

r1 = subprocess.run(
    [str(sionna_python), str(sionna_script)],
    cwd=str(project_root / "channel_part")
)

print(f"Sionna 返回码: {r1.returncode}")

if r1.returncode != 0:
    print("❌ Sionna 模块运行失败，流程终止")
    raise SystemExit(1)

if not channel_eval_file.exists():
    print(f"❌ 未找到 Sionna 输出文件: {channel_eval_file}")
    raise SystemExit(1)

print(f"✔ 已找到 Sionna 输出文件: {channel_eval_file}")

# =========================
# 7. Step 2: 发给 VM 跑 ns-3 / GridLAB-D
# =========================
print("=== Step 2: 发送到 VM ===")
send_channel_eval_to_vm(channel_eval_file)

# =========================
# 8. Step 3: 等待 VM 输出
# =========================
print("=== Step 3: 等待 VM 运行 ns-3 / GridLAB-D ===")
print("请确保虚拟机中的脚本已启动")

ok = wait_for_vm_outputs(timeout=1800, interval=2)

if not ok:
    print("❌ 等待 VM 输出超时")
    raise SystemExit(1)

vm_results = get_vm_result_paths()

network_eval_vm = Path(vm_results["network_eval"])
power_eval_vm = Path(vm_results["power_eval"])

print(f"✔ 已收到 network_eval.csv: {network_eval_vm}")
print(f"✔ 已收到 power_eval.csv:   {power_eval_vm}")

# =========================
# 9. Step 4: 复制 VM 输出到路径规划模块目录
# =========================
print("=== Step 4: 准备路径规划输入文件 ===")

if not network_eval_vm.exists():
    print(f"❌ 未找到 VM 输出 network_eval.csv: {network_eval_vm}")
    raise SystemExit(1)

if not power_eval_vm.exists():
    print(f"❌ 未找到 VM 输出 power_eval.csv: {power_eval_vm}")
    raise SystemExit(1)

planner_network_file.parent.mkdir(parents=True, exist_ok=True)

shutil.copy2(network_eval_vm, planner_network_file)
shutil.copy2(power_eval_vm, planner_power_file)

print(f"✔ 已复制 network_eval.csv -> {planner_network_file}")
print(f"✔ 已复制 power_eval.csv   -> {planner_power_file}")

# =========================
# 10. Step 5: 运行路径规划（传入起点终点坐标）
# =========================
print("=== Step 5: 运行路径规划 ===")
print(f"起点坐标: {START_POS}")
print(f"终点坐标: {GOAL_POS}")

r_plan = subprocess.run(

    [
        str(planner_python),
        str(planner_script),
        "--start_x", str(START_POS[0]),
        "--start_y", str(START_POS[1]),
        "--start_z", str(START_POS[2]),
        "--goal_x", str(GOAL_POS[0]),
        "--goal_y", str(GOAL_POS[1]),
        "--goal_z", str(GOAL_POS[2]),
    ],
    cwd=str(project_root / "path_planning_part")
)

print(f"路径规划返回码: {r_plan.returncode}")

if r_plan.returncode != 0:
    print("❌ 路径规划失败")
    raise SystemExit(1)

if not path_planning_input_file.exists():
    print(f"❌ 未生成代价表: {path_planning_input_file}")
    raise SystemExit(1)

if not planned_path_src.exists():
    print(f"❌ 未生成规划路径: {planned_path_src}")
    print("可能原因：有效节点太少，或起点终点不连通。")
    raise SystemExit(1)

print(f"✔ 已生成代价表: {path_planning_input_file}")
print(f"✔ 已生成规划路径: {planned_path_src}")

# =========================
# 11. Step 6: 同步路径到 AirSim
# =========================
print("=== Step 6: 同步路径到 AirSim ===")

planned_path_dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(planned_path_src, planned_path_dst)

if not planned_path_dst.exists():
    print(f"❌ 同步失败，未找到 AirSim 路径表: {planned_path_dst}")
    raise SystemExit(1)

print(f"✔ 已同步路径表到 AirSim: {planned_path_dst}")

# =========================
# 12. Step 7: AirSim 演示规划结果
# =========================
print("=== Step 7: AirSim 轨迹演示 ===")

r2 = subprocess.run(
    [str(airsim_python), str(airsim_script)],
    cwd=str(project_root / "airsim_part")
)

print(f"AirSim 返回码: {r2.returncode}")

if r2.returncode != 0:
    print("❌ AirSim 演示失败")
    raise SystemExit(1)

print("=== 全流程完成 ===")