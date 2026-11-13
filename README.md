# GPRMAX-result

钢筋混凝土探地雷达正演项目，模型来自 ParaView/SolidWorks 工作流。

## 当前模型

- 混凝土板：3.0 m（X）× 2.0 m（Y）× 0.4 m（Z）。
- 双层 HRB400 基础钢筋、附加钢筋、边缘钢筋、泡沫缺陷和泡沫板均同步自桌面最新模型。
- ParaView 状态文件：`model/paraview/东至南模型.pvsm`。

## GPU 与体素化

本机 gprMax 4.0.1 使用 RTX 5060 CUDA GPU。统一入口为 `simulation/run_gpu.cmd`。当前体素模型为 10 mm：

```powershell
C:\env\gprmax_v4\Scripts\python.exe simulation/scripts/voxelize_current_model.py --dx 0.01 --outdir simulation/geometry_10mm
```

## 当前全局栅格正演

当前任务为 `simulation/raster_scan/global_10mm/`：

- 21 条测线，Y=0.1…2.1 m，测线间距 100 mm；
- 每条测线 3.0 m，X=3.1→0.1 m，10 mm 道间距，共 301 道；
- 从 A 面右下角开始，逐道右向左，逐线由下向上；
- 名义 Tx/Rx 间距 46 mm，天线贴合 A 面 Z=0.5 m；
- X 极化，10 ns 时间窗；
- FDTD 计算域缩小到 `3.3×2.3×0.7 m`，10 个 PML 网格单元，几何插入点仍为 `(0.1,0.1,0.1) m`。

10 mm Yee 网格不能精确表达 5 mm 道间距，因此本次扫描采用与网格一致的 10 mm 实际道间距；Tx/Rx 的 46 mm 为名义值，gprMax 会吸附到最近网格位置。

启动命令：

```powershell
C:\env\gprmax_v4\Scripts\python.exe simulation/scripts/run_raster_scan.py --grid global_10mm --ntraces 301 --skip-complete
```

后台整理器会把完成测线转换为 `simulation/results/global_10mm/line_001_Ex.npz`、`line_001_Ex.jpg` 和坐标 CSV，并在整理成功后删除该线的临时 HDF5。
