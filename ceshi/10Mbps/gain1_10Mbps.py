import csv
# import matplotlib.pyplot as plt
import pandas as pd 
import numpy as np 
# import matplotlib.pyplot as plt 
# import csv 
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

def calculate_average_energy_matrix(energy_1,energy_2,energy_3,energy_4):
    average_energy=(energy_1+energy_2+energy_3+energy_4)/4
    return average_energy

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
energy_enb_per_user = float(lines[0].strip())
energy_wifi_per_user = float(lines[1].strip())
energy_lifi_per_user = float(lines[2].strip())

#22个基站的能耗矩阵(txpower=30dbm/1W)
energy_matrix_1Mb=[[0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.46816,0.46816],
               [0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44233,0.44233],
               [0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.46816,0.46816],
               [0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.46816,0.46816],
               [0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44233,0.44233],
               [0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.46816,0.46816],
               [0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44825],
               [0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44825,0.44825],
               [0.46816,0.44233,0.46816,0.46816,0.44233,0.46816,0.54852,0.44825,0.44825,0.54852],
               [0.46816,0.44233,0.46816,0.46816,0.44233,0.46816,0.54852,0.44825,0.44825,0.54852]]

energy_matrix_2Mb = [
    [0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.50675, 0.50675],
    [0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.47969, 0.47969],
    [0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.50675, 0.50675],
    [0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.50675, 0.50675],
    [0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.47969, 0.47969],
    [0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.50675, 0.50675],
    [0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908],
    [0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908, 0.46908],
    [0.50675, 0.47969, 0.50675, 0.50675, 0.47969, 0.50675, 0.66135, 0.46908, 0.46908, 0.66135],
    [0.50675, 0.47969, 0.50675, 0.50675, 0.47969, 0.50675, 0.66135, 0.46908, 0.46908, 0.66135]
]

energy_matrix_3Mb = [
    [0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.54063, 0.54063],
    [0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.49562, 0.49562],
    [0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.54063, 0.54063],
    [0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.54063, 0.54063],
    [0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.49562, 0.49562],
    [0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.54063, 0.54063],
    [0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993],
    [0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993, 0.4993],
    [0.54063, 0.49562, 0.54063, 0.54063, 0.49562, 0.54063, 0.71631, 0.4993, 0.4993, 0.71631],
    [0.54063, 0.49562, 0.54063, 0.54063, 0.49562, 0.54063, 0.71631, 0.4993, 0.4993, 0.71631]
]

energy_matrix_6Mb = [
    [0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.59927, 0.59927],
    [0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.53054, 0.53054],
    [0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.59927, 0.59927],
    [0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.59927, 0.59927],
    [0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.53054, 0.53054],
    [0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.59927, 0.59927],
    [0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233],
    [0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233, 0.54233],
    [0.59927, 0.53054, 0.59927, 0.59927, 0.53054, 0.59927, 1.04147, 0.54233, 0.54233, 1.04147],
    [0.59927, 0.53054, 0.59927, 0.59927, 0.53054, 0.59927, 1.04147, 0.54233, 0.54233, 1.04147]
]

energy_matrix_10Mb = [
    [0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.64685, 0.64685],
    [0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.5641, 0.5641],
    [0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.64685, 0.64685],
    [0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.64685, 0.64685],
    [0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.5641, 0.5641],
    [0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.64685, 0.64685],
    [0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995],
    [0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995, 0.58995],
    [0.64685, 0.5641, 0.64685, 0.64685, 0.5641, 0.64685, 1.36183, 0.58995, 0.58995, 1.36183],
    [0.64685, 0.5641, 0.64685, 0.64685, 0.5641, 0.64685, 1.36183, 0.58995, 0.58995, 1.36183]
]

energy_matrix_16Mb = [
    [0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.73695, 0.73695],
    [0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.64023, 0.64023],
    [0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.73695, 0.73695],
    [0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.73695, 0.73695],
    [0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.64023, 0.64023],
    [0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.73695, 0.73695],
    [0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743],
    [0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743, 0.67743],
    [0.73695, 0.64023, 0.73695, 0.73695, 0.64023, 0.73695, 2.16718, 0.67743, 0.67743, 2.16718],
    [0.73695, 0.64023, 0.73695, 0.73695, 0.64023, 0.73695, 2.16718, 0.67743, 0.67743, 2.16718]
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

# 分配用户到APs 
ap_users,ap_connections_matrix = assign_users_to_aps(xx, yy, ap_locations, coverage_radius, max_connections,grid_size) 
transposed_matrix = ap_connections_matrix.T  
rotated_matrix = np.flipud(transposed_matrix) 
# print("每个小方格多制式中连接WiFi的用户数矩阵:")
# print(rotated_matrix)
sum=np.sum(rotated_matrix)
wifi_user = rotated_matrix[:, :8]
wifi_sum=np.sum(wifi_user)
lifi_sum=sum-wifi_sum
# print("基线中连接基站的用户数为: ",2199-wifi_sum-lifi_sum-10)
# print("基线中连接wifi的用户数为: ",wifi_sum)
# print("基线中连接lifi的用户数为: ",lifi_sum)
# print("基线中连接到有线的用户数: ",10)


# 计算剩余用户数 
remaining_user_matrix = calculate_remaining_users(user_count_matrix, ap_users, grid_size, coverage_radius) 
# print("每个小方格多制式中连接蜂窝的用户数矩阵:")  
remainingsum=np.sum(remaining_user_matrix)
transposed_remaining_matrix = remaining_user_matrix.T  
rotated_remaining_matrix = np.flipud(transposed_remaining_matrix) 
# print(rotated_remaining_matrix)
result111 = np.multiply(rotated_remaining_matrix, energy_matrix_10Mb) 
result_sum1 = np.sum(result111)
Energy_BS_baseline = 97*22+result_sum1*energy_enb_per_user/2/0.58995
Energy_Wifi_Baseline = 80*5+(0.049*wifi_sum)*energy_wifi_per_user/0.049
Energy_Lifi_Baseline = 20*5+(0.046*lifi_sum)*energy_lifi_per_user/0.046
Energy_Swith = 2.03*22+2.97*1*(10+Energy_Wifi_Baseline+Energy_Lifi_Baseline)/5000
Energy_Total = Energy_BS_baseline+Energy_Wifi_Baseline+Energy_Lifi_Baseline+Energy_Swith
Carbon_Emission_2020_baseline = (Energy_Total*0.821*0.709/3600+22*0.00177+80*0.0000403+22*0.0000162+20*0.0000093)/1000
Carbon_Emission_2022_baseline = (Energy_Total*0.821*0.638/3600+22*0.00177+80*0.0000403+22*0.0000162+20*0.0000093)/1000
Carbon_Emission_2030_baseline = (Energy_Total*0.821*0.475/3600+22*0.00177+80*0.0000403+22*0.0000162+20*0.0000093)/1000

energy_consumption = pd.read_csv('/home/estar/cosin-env/ceshi/10Mbps/gain1_energy.csv', usecols=[1], skiprows=9)
energy_consumption_sample = energy_consumption.iloc[:, 0][::3600][:24]
time_labels = [f'{str((i-1)%24).zfill(2)}' for i in range(1, 25)]
energy_consumption_after = pd.read_csv('/home/estar/cosin-env/ceshi/10Mbps/gain1_energy.csv', usecols=[1], skiprows=9)
total_energy_consumption_bs = energy_consumption_after.sum()
Energy_Total_Gain1 = Energy_BS_baseline/2+total_energy_consumption_bs.iloc[0]/24/3600+Energy_Wifi_Baseline+Energy_Lifi_Baseline+Energy_Swith
Carbon_Emission_2020_Gain1 = (Energy_Total_Gain1*0.821*0.709/3600+22*0.00177+80*0.0000403+22*0.0000162+20*0.0000093)/1000
Carbon_Emission_2022_Gain1 = (Energy_Total_Gain1*0.821*0.638/3600+22*0.00177+80*0.0000403+22*0.0000162+20*0.0000093)/1000
Carbon_Emission_2030_Gain1 = (Energy_Total_Gain1*0.821*0.475/3600+22*0.00177+80*0.0000403+22*0.0000162+20*0.0000093)/1000
print(f"增益一中基站的总功耗为: {Energy_BS_baseline/2+total_energy_consumption_bs.iloc[0]/24/3600}")
print("增益一中wifi的功耗为：",Energy_Wifi_Baseline)
print("增益一中lifi的功耗为：",Energy_Lifi_Baseline)
print("增益一中总功耗为：",Energy_Total_Gain1)
print("2020年增益一的总碳排为：",Carbon_Emission_2020_Gain1)
print("2022年增益一的总碳排为：",Carbon_Emission_2022_Gain1)
print("2030年增益一的总碳排为：",Carbon_Emission_2030_Gain1)
Gain1_2020 = (Carbon_Emission_2020_baseline-Carbon_Emission_2020_Gain1)/Carbon_Emission_2020_baseline
Gain1_2022 = (Carbon_Emission_2022_baseline-Carbon_Emission_2022_Gain1)/Carbon_Emission_2022_baseline
Gain1_2030 = (Carbon_Emission_2030_baseline-Carbon_Emission_2030_Gain1)/Carbon_Emission_2030_baseline
print("2020年的碳排增益一为：",Gain1_2020)
print("2022年的碳排增益一为：",Gain1_2022)
print("2030年的碳排增益一为：",Gain1_2030)
