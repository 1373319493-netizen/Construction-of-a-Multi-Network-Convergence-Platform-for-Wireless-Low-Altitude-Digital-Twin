import numpy as np
import csv

# 起点和终点
start = np.array([30,26,0])
end = np.array([0.0, 0.0, -50.0])
#start = np.array([0.0, 0.0, -50.0])
#end = np.array([-170.0, -2.0, -10.0])
# 插值函数，生成轨迹点
def generate_spline_path(start, end, num_points=100):
    t = np.linspace(0, 1, num_points)
    path = []
    for i in t:
        point = (1 - i) * start + i * end
        path.append(point.tolist() + [0])  # 添加 yaw=0,这里没有在运行中使用
    return path
# 生成轨迹
trajectory = generate_spline_path(start, end, num_points=100)
# 保存到 CSV
with open('watpoint.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['x', 'y', 'z'])  #表头
    writer.writerows(trajectory)

print("轨迹保存完成".format(len(trajectory)))