import airsim
import pandas as pd
import time
from pathlib import Path


def main():
    """
    AirSim 轨迹演示脚本
    功能：
    1. 读取路径表
    2. 控制无人机依次飞到各路径点
    3. 在 UE 中演示规划结果
    """

    # =========================
    # 1. 参数设置
    # =========================
    speed = 6.0          # 飞行速度（m/s）
    timeout_sec = 5    # 每段飞行最大等待时间

    # 路径表文件
    csv_path = Path(__file__).resolve().parent / "planned_path.csv"

    if not csv_path.exists():
        print(f"未找到路径表: {csv_path}")
        return

    # =========================
    # 2. 读取路径表
    # =========================
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()

    required_cols = ["x", "y", "z"]
    for col in required_cols:
        if col not in df.columns:
            print(f"路径表缺少列: {col}")
            return

    points = df[["x", "y", "z"]].values.tolist()

    if len(points) == 0:
        print("路径表为空")
        return

    print(f"成功读取路径点数量: {len(points)}")

    # =========================
    # 3. 连接 AirSim
    # =========================
    client = airsim.MultirotorClient()
    client.confirmConnection()

    print("已连接 AirSim")

    client.enableApiControl(True)
    client.armDisarm(True)

    # =========================
    # 4. 起飞
    # =========================
    print("无人机起飞...")
    client.takeoffAsync().join()
    time.sleep(2)

    # =========================
    # 5. 先飞到第一个点
    # =========================
    first_x, first_y, first_z = map(float, points[0])

    airsim_z = -first_z  # ⭐ 关键：取负

    print(f"飞向第一个路径点: ({first_x}, {first_y}, {airsim_z})")

    client.moveToPositionAsync(
        first_x, first_y, airsim_z,
        speed,
        timeout_sec
    ).join()

    time.sleep(1)

    # =========================
    # 6. 依次飞行整条路径
    # =========================
    print("开始路径演示...")

    for i, pt in enumerate(points):
        x, y, z = map(float, pt)

        airsim_z = -z  # ⭐ 关键：取负

        print(f"路径点 {i + 1}: x={x:.2f}, y={y:.2f}, z={airsim_z:.2f}")

        client.moveToPositionAsync(
            x, y, airsim_z,
            speed,
            timeout_sec
        ).join()

        time.sleep(0.5)
    # =========================
    # 7. 降落
    # =========================
    print("无人机降落...")
    client.moveToZAsync(0, 10).join()
    client.landAsync().join()
    client.armDisarm(False)
    client.enableApiControl(False)

    print("AirSim 演示结束")


if __name__ == "__main__":
    main()