import csv
import pandas as pd 

import numpy as np 
import csv 
import torch 
import random 
import time 
# 设置随机种子 

def setup_seed(seed): 
    torch.manual_seed(seed) 
    torch.cuda.manual_seed_all(seed) 
    np.random.seed(seed) 
    random.seed(seed) 
    torch.backends.cudnn.deterministic = True 
    
setup_seed(20) 

xMin = 0 # x轴最小值 
xMax = 125 # x轴最大值 
yMin = 0 # y轴最小值 
yMax = 125 # y轴最大值 
xDelta = xMax - xMin 
yDelta = yMax - yMin # rectangle dimensions 
areaTotal = xDelta * yDelta 

# Poisson process parameters 
lambda0 = 0.14 # intensity (ie mean density) of the Poisson process 
numbPoints = np.random.poisson(lambda0 * areaTotal) 
print("总用户数为： ", numbPoints) 

# 生成用户位置 
xx = np.random.uniform(0, 1, numbPoints) 
yy = np.random.uniform(0, 1, numbPoints) 
xx = xDelta * xx + xMin 
yy = yDelta * yy + yMin 

# plt.scatter(xx, yy, edgecolor='b', facecolor='none', alpha=0.5) # 画图代码 
# plt.xlabel("x") 
# plt.ylabel("y") 
# plt.show() 

# 保存用户位置到CSV文件 
user_Loc = np.stack((xx, yy), axis=1) 
with open('user_Location_PPP_125m_times125m.csv', mode='w', newline='') as file: 
    writer = csv.writer(file) 
    writer.writerows(user_Loc) 
    
# 生成均匀分布的WiFi AP点 
def generate_ap_locations(area_size, num_aps): 
    grid_size = int(np.sqrt(num_aps)) 
    x = np.linspace(0, area_size, grid_size, endpoint=False) 
    y = np.linspace(0, area_size, grid_size, endpoint=False) 
    x_grid, y_grid = np.meshgrid(x, y) 
    ap_locations = np.vstack([x_grid.ravel(), y_grid.ravel()]).T 
    return ap_locations 

def calculate_average_energy_matrix(energy_1,energy_2,energy_3,energy_4):
    average_energy=(energy_1+energy_2+energy_3+energy_4)/4
    return average_energy

# 计算每个小方格内的用户数 
def calculate_users_in_grids(xx, yy, grid_size): 
    user_count_matrix = np.zeros((grid_size, grid_size)) 
    for x, y in zip(xx, yy): 
        grid_x = int(x // (xMax / grid_size)) 
        grid_y = int(y // (yMax / grid_size)) 
        user_count_matrix[grid_x, grid_y] += 1 
    return user_count_matrix 

# 计算每个AP的用户连接 
def assign_users_to_aps(xx, yy, ap_locations, coverage_radius, max_connections, grid_size): 
    ap_users = {tuple(ap): [] for ap in ap_locations} 
    ap_connections_matrix = np.zeros((grid_size, grid_size)) 
    
    for ap_x, ap_y in ap_locations: 
        distances = np.sqrt((xx - ap_x) ** 2 + (yy - ap_y) ** 2) 
        close_users = distances <= coverage_radius 
        users_within_range = np.array(list(zip(xx[close_users], yy[close_users]))) 
        
        if len(users_within_range) > max_connections: 
            distances_within_range = np.sqrt((users_within_range[:, 0] - ap_x) ** 2 + (users_within_range[:, 1] - ap_y) ** 2) 
            sorted_indices = np.argsort(distances_within_range) 
            closest_users = sorted_indices[:max_connections] 
            ap_users[tuple((ap_x, ap_y))] = users_within_range[closest_users] 
        else: 
            ap_users[tuple((ap_x, ap_y))] = users_within_range 
            
            # 更新AP连接的用户数矩阵 
        grid_x = int(ap_x // (xMax / grid_size)) 
        grid_y = int(ap_y // (yMax / grid_size)) 
        ap_connections_matrix[grid_x, grid_y] += len(ap_users[tuple((ap_x, ap_y))]) 
            
    return ap_users, ap_connections_matrix


# 计算每个小方格的剩余用户数 
def calculate_remaining_users(user_count_matrix, ap_users, grid_size, coverage_radius): 
    remaining_users_matrix = np.copy(user_count_matrix) 
    for ap_location, users in ap_users.items(): 
        ap_x, ap_y = ap_location 
        grid_x = int(ap_x // (xMax / grid_size)) 
        grid_y = int(ap_y // (yMax / grid_size)) 
        
        # Update the number of users in this grid cell 
        total_users_in_cell = user_count_matrix[grid_x, grid_y] 
        connected_users = len(users) 
        remaining_users_matrix[grid_x, grid_y] = total_users_in_cell - connected_users 
    return remaining_users_matrix 


def sum_first_column(csv_file):
    total_sum = 0
    with open(csv_file, mode='r') as file:
        reader = csv.reader(file)
        for row in reader:
            try:
                total_sum += float(row[0])  # 转换为浮点数
            except ValueError:
                print(f"无法处理行: {row[0]} 不是数字")
                continue
    return total_sum

# 参数设置 
num_aps = 100 
coverage_radius = 3 # 基线中wifi的覆盖半径
max_connections = 4 #基线中wifi的最大连接用户数
throughput_per_user = 10 #单用户的吞吐量
max_wifi = max(round(50/throughput_per_user),4) #增益中wifi的最大连接用户数=吞吐量/单用户吞吐量
# max_wifi = 4
with open('/home/estar/cosin-env/ceshi/10Mbps/energy.txt', 'r') as file:
    lines = file.readlines()
energy_enb_per_user = 0.100942
energy_wifi_per_user = float(lines[1].strip())
energy_lifi_per_user = float(lines[2].strip())

#22个基站的能耗矩阵(txpower=30dbm/1W)
energy_matrix_10Mb = [
    [0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.11441545, 0.11441545],
    [0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.0998737, 0.0998737],
    [0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.11441545, 0.11441545],
    [0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.11441545, 0.11441545],
    [0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.0998737, 0.0998737],
    [0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.11441545, 0.11441545],
    [0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115],
    [0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115, 0.10467115],
    [0.11441545, 0.0998737, 0.11441545, 0.11441545, 0.0998737, 0.11441545, 0.24153951, 0.10467115, 0.10467115, 0.24153951],
    [0.11441545, 0.0998737, 0.11441545, 0.11441545, 0.0998737, 0.11441545, 0.24153951, 0.10467115, 0.10467115, 0.24153951]
]


# 生成AP位置--平均分布
ap_locations = generate_ap_locations(xMax, num_aps) 
# 计算每个小方格内的用户数 
grid_size = 10 # 10x10的网格 
user_count_matrix = calculate_users_in_grids(xx, yy, grid_size)  
# print("每个小方格的用户数矩阵:") 
transposed_usertot_matrix = user_count_matrix.T  
rotated_usetot_matrix = np.flipud(transposed_usertot_matrix) 
# print(rotated_usetot_matrix)


#增益--优化部署
rotated_usetot_matrix = rotated_usetot_matrix.copy()
rotated_usetot_matrix = torch.tensor(rotated_usetot_matrix,dtype=torch.float32)
# 22个基站
facotr_matrix=torch.tensor([
     [0.385628, 0.366907, 0.350213, 0.337293, 0.329823, 0.324776, 0.314965, 0.303841, 0.291550, 0.276883],
    [0.370547, 0.348209, 0.326751, 0.307410, 0.290094, 0.276116, 0.267833, 0.261519, 0.253617, 0.242357],
    [0.357461, 0.329822, 0.298475, 0.263859, 0.234197, 0.221402, 0.221029, 0.221486, 0.218094, 0.209557],
    [0.333830, 0.299503, 0.260292, 0.216191, 0.171128, 0.165419, 0.180006, 0.187102, 0.186560, 0.179185],
    [0.301577, 0.268092, 0.230084, 0.186706, 0.135038, 0.132709, 0.153448, 0.160765, 0.159537, 0.151134],
    [0.271782, 0.242037, 0.209759, 0.176680, 0.148684, 0.138518, 0.140673, 0.140891, 0.135644, 0.124227],
    [0.244042, 0.219093, 0.193250, 0.168667, 0.148799, 0.136471, 0.129406, 0.122386, 0.111984, 0.096555],
    [0.216319, 0.195830, 0.175032, 0.155424, 0.138524, 0.124879, 0.113153, 0.100847, 0.085755, 0.066785],
    [0.186141, 0.169337, 0.152103, 0.135309, 0.119554, 0.104764, 0.090037, 0.074062, 0.056080, 0.037265],
    [0.151168, 0.137311, 0.122568, 0.107418, 0.092079, 0.076427, 0.060176, 0.043546, 0.028150, 0.016454]
                       ],dtype=torch.float32)

user_enb = facotr_matrix * rotated_usetot_matrix
result = torch.round(user_enb)
user_wifi = rotated_usetot_matrix - result
user_wifi = torch.clamp(user_wifi,max=max_wifi)
user_wifi = user_wifi.numpy()
result = rotated_usetot_matrix - user_wifi
result = result.numpy()
result[0,0]-=10

sum_wifilifi=np.sum(user_wifi)
wifi_user_gain = user_wifi[:, :8]
sum_wifi=np.sum(wifi_user_gain)
sum_lifi=sum_wifilifi-sum_wifi
sum_enb=np.sum(result)
# print("优化后连接到基站的用户矩阵：")
# print(result)
# print("优化后连接到wifi的用户矩阵:")
# print(user_wifi)


energy_consumption = pd.read_csv('/home/estar/cosin-env/ceshi/10Mbps/gain2_energy.csv', usecols=[1], skiprows=9)
energy_consumption_sample = energy_consumption.iloc[:, 0][::3600][:24]
time_labels = [f'{str((i-1)%24).zfill(2)}' for i in range(1, 25)]
energy_consumption_after = pd.read_csv('/home/estar/cosin-env/ceshi/10Mbps/gain2_energy.csv', usecols=[1], skiprows=9)
total_energy_consumption = energy_consumption_after.sum()
# print(f"Total energy consumption: {total_energy_consumption[0]/24/3600}")
result_1 =np.multiply(result,energy_matrix_10Mb)
a=np.sum(result_1)
b=(97*22*2+a*energy_enb_per_user/0.10467115)/2-97*0*0.8

print("增益三中基站的能耗为：",b)
print("加入绿电中的能耗值为：",b/2)

