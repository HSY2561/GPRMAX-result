# GPRMAX-result

钢筋混凝土探地雷达正演项目，模型来自 ParaView/SolidWorks 工作流。

## 当前模型

- 混凝土板：3.0 m（X）× 2.0 m（Y）× 0.4 m（Z）。
- 双层 HRB400 基础钢筋，以及桌面最新模型中的附加钢筋和边缘钢筋均已同步到 `model/paraview/`。
- 泡沫缺陷和 3 块泡沫板按最新 ParaView 模型保留。
- ParaView 状态文件：`model/paraview/东至南模型.pvsm`。

## GPU 与体素化

本机 gprMax 4.0.1 使用 CUDA GPU（RTX 5060）。统一入口为 `simulation/run_gpu.cmd`，它会先加载 VS2022 BuildTools，再调用 `C:\env\gprmax_v4` 环境。

5 mm 体素模型已根据最新 VTP/JSON 重新生成：`simulation/geometry_5mm/geometry.h5`。体素化脚本同时读取基础钢筋、`additional_rebars_metadata.json` 和 `edge_rebars_metadata.json`。

```powershell
C:\env\gprmax_v4\Scripts\python.exe simulation/scripts/voxelize_current_model.py --dx 0.005 --outdir simulation/geometry_5mm
```

## 全局栅格正演

当前唯一保留的栅格任务是 `simulation/raster_scan/global_5mm/`：

- 21 条测线，Y=0.1…2.1 m，测线间距 100 mm；
- 每条测线 3.0 m，X=3.1→0.1 m，5 mm 道间距，共 601 道；
- 从 A 面右下角开始，逐道右向左，逐线由下向上；
- Tx/Rx 间距 46 mm，天线贴合 A 面 Z=0.5 m；
- X 极化，15 ns 时间窗，使用 5 mm 几何体素。

启动 21 条测线：

```powershell
C:\env\gprmax_v4\Scripts\python.exe simulation/scripts/run_raster_scan.py --grid global_5mm --ntraces 601 --skip-complete
```

每条线的状态和 HDF5 输出保存在对应 `line_###/` 目录。计算完成后再生成 B-scan 图像和结果压缩包。

后台整理器会把已完成测线转换为编号结果：`simulation/results/global_5mm/line_001_Ex.npz`、`line_001_Ex.jpg` 和对应的 `line_001_trace_coordinates.csv`。编号中的 `001…021` 对应 Y=0.1…2.1 m；每条线内部的道号 `001…601` 保持右向左顺序。某条线成功整理后，其临时 `input*.h5` 会从本地删除，GitHub 只保留压缩矩阵、JPG、坐标和清单。
