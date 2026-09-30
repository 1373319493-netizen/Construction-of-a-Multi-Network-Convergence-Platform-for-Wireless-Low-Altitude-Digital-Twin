# Construction of a Multi-Network Convergence Platform for Wireless Low-Altitude Digital Twin

面向无线低空数字孪生的多网络融合平台。项目包含无线信道评估、网络与电力仿真数据交换、路径规划，以及 AirSim 无人机轨迹演示相关代码和实验数据。

## 目录

| 目录 | 内容 |
| --- | --- |
| `joint_platform/` | 联合仿真主控、信道评估、路径规划与轨迹演示 |
| `joint_platform/channel_part/` | Sionna RT 信道评估脚本与三维场景 |
| `joint_platform/path_planning_part/` | 综合代价计算、A* 路径规划与 CSV 数据 |
| `joint_platform/airsim_part/` | AirSim 轨迹演示 |
| `rayget/` | 射线传播相关实验脚本、场景和数据 |
| `ceshi/` | 不同业务速率下的实验脚本、结果及 ns-3 相关文件 |
| `vm_exchange/` | Windows 主机与虚拟机交换的输入、输出 CSV |

## 主流程

`joint_platform/controller.py` 串联以下步骤：

1. 调用 Sionna RT 生成 `channel_eval.csv`。
2. 将信道评估数据复制到虚拟机共享目录。
3. 等待虚拟机侧生成 `network_eval.csv` 和 `power_eval.csv`。
4. 计算综合代价并生成 `planned_path.csv`。
5. 将路径传入 AirSim 进行轨迹演示。

## 运行前配置

本仓库是现有研究项目的归档，尚未验证在全新环境中一键运行。主控脚本使用多个独立环境，主要涉及 Python、NumPy、pandas、Sionna RT、AirSim、ns-3、GridLAB-D 和 HELICS。具体版本与兼容性需要按原实验环境确认。

- 修改 `joint_platform/controller.py` 中的 `project_root`、`airsim_python` 和 `sionna_python`，使其指向本机项目和解释器。
- 修改 `joint_platform/vm_bridge.py` 中的 `shared_root`，配置 Windows 与虚拟机之间的共享目录。
- 检查其他实验脚本中的本机绝对路径，并按实际环境调整。
- 启动虚拟机侧仿真流程，确保其读取共享输入并生成约定的两份输出 CSV；主控脚本不会自动启动虚拟机侧服务。
- 准备并启动兼容的 AirSim 场景，再运行主控脚本。

配置完成后，在项目根目录执行：

```sh
python joint_platform/controller.py
```

仓库保留已有 CSV 实验数据和场景模型；运行仿真时可能覆盖部分输出文件。

## 第三方代码与许可

`ceshi/ns3-mmwave-5.0/` 内包含第三方代码，其作者信息、许可文件及版权声明保留在对应目录中。原目录中 HELICS 与 mmwave-energy 的嵌套 Git 元数据不包含在本上传副本中，实际文件以普通目录保存。

本项目未新增统一的开源许可证。第三方代码遵循各自许可；项目自有代码及场景资产的使用授权需由权利人明确。
