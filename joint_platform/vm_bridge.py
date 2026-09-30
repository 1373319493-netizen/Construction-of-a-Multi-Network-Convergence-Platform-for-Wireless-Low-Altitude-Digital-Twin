import shutil
import time
from pathlib import Path


# =========================
# 1. 共享目录（Windows 主机）
#    改成你实际路径
# =========================
shared_root = Path(r"C:\Users\13733\Desktop\毕设相关\vm_exchange")

# 主机 -> VM
vm_input_dir = shared_root / "input"

# VM -> 主机
vm_output_dir = shared_root / "output"

# 输入输出文件
vm_channel_eval_file = vm_input_dir / "channel_eval.csv"
vm_network_eval_file = vm_output_dir / "network_eval.csv"
vm_power_eval_file = vm_output_dir / "power_eval.csv"
vm_done_flag = vm_output_dir / "DONE"


def ensure_vm_dirs():
    vm_input_dir.mkdir(parents=True, exist_ok=True)
    vm_output_dir.mkdir(parents=True, exist_ok=True)


def clear_old_vm_outputs():
    for old_file in [vm_network_eval_file, vm_power_eval_file, vm_done_flag]:
        if old_file.exists():
            old_file.unlink()


def send_channel_eval_to_vm(channel_eval_file: Path):
    """
    把 Sionna 输出复制到共享目录，供 VM 读取
    """
    if not channel_eval_file.exists():
        raise FileNotFoundError(f"未找到 Sionna 输出文件: {channel_eval_file}")

    ensure_vm_dirs()

    if vm_channel_eval_file.exists():
        vm_channel_eval_file.unlink()

    clear_old_vm_outputs()
    shutil.copy2(channel_eval_file, vm_channel_eval_file)

    print(f"✔ 已发送到 VM 共享目录: {vm_channel_eval_file}")


def wait_for_vm_outputs(timeout=1800, interval=2):
    """
    等待 VM 返回 network_eval.csv 和 power_eval.csv
    """
    start = time.time()

    while time.time() - start < timeout:
        if vm_done_flag.exists():
            if vm_network_eval_file.exists() and vm_power_eval_file.exists():
                return True

        if vm_network_eval_file.exists() and vm_power_eval_file.exists():
            return True

        time.sleep(interval)

    return False


def get_vm_result_paths():
    """
    返回 VM 输出文件路径
    """
    return {
        "network_eval": vm_network_eval_file,
        "power_eval": vm_power_eval_file,
    }