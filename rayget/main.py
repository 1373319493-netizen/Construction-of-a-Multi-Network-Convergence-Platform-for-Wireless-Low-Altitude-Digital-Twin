import sionna.rt
from sionna.rt import load_scene, PlanarArray, Transmitter, Receiver, PathSolver
import numpy as np
# === 固定发射机位置 ===
tx_pos = np.array([-80, 35, 35])
tx_id = 1  # 假设只有一个发射机，ID为0
# === 加载接收机位置文件 ===
rx_pos_file = "input/rx_positions.txt"
with open(rx_pos_file, "r") as f:
    rx_positions = [list(map(float, line.strip().split())) for line in f if line.strip()]

# === 加载场景 ===
scene = load_scene("C:/Users/13733/Desktop/毕设相关/rayget/input/shu/buildings.xml", merge_shapes=False)

# === 添加发射机 ===
tx_name = "tx"
if scene.get(tx_name):
    scene.remove(tx_name)
scene.add(Transmitter(tx_name, position=tx_pos, display_radius=2))

# 设置阵列
scene.tx_array = PlanarArray(num_cols=1, num_rows=1, pattern="iso", polarization="V")
scene.rx_array = scene.tx_array

# === 初始化结果列表 ===
all_paths_points = []

# === 遍历每个接收机位置 ===
for rx_id, rx_pos in enumerate(rx_positions, start=1):
    rx_pos = np.array(rx_pos)
    rx_name = f"rx-{rx_id}"



    # 添加接收机
    scene.add(Receiver(rx_name, position=rx_pos, display_radius=2))

    # 路径求解器
    p_solver = PathSolver()
    paths = p_solver(scene, max_depth=4,refraction=False)
    num_paths = paths.objects.shape[3]
    scene.remove(rx_name)
#去除无效交互点
    for path_idx in range(min(num_paths, 5)):
        pos = np.array(paths.vertices.numpy()[:, 0, 0, path_idx])
        combined_points = np.vstack([tx_pos, pos, rx_pos])
        filtered_points = combined_points[~np.all(combined_points == 0, axis=1)]

        for point_idx, point in enumerate(filtered_points):
            row = [
                rx_id, rx_pos[0], rx_pos[1], rx_pos[2],  # rx_id, rx_x, rx_y, rx_z
                path_idx, point_idx,                    # path_id, point_id
                point[0], point[1], point[2],           # x, y, z
                tx_id
            ]
            all_paths_points.append(row)
    scene.remove(rx_name)
# === 保存路径点信息 ===
output_path = "output/all_paths_points_with_info.csv"
header = "rx_id,rx_x,rx_y,rx_z,path_id,point_id,x,y,z,tx_id"
np.savetxt(output_path, all_paths_points, delimiter=",", fmt="%.6f", header=header, comments='')
print(f"所有路径点已保存到 {output_path}")







