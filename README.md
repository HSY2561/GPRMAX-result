# GPRMAX-result

钢筋混凝土探地雷达正演项目，模型来自 ParaView/SolidWorks 工作流。

## 当前模型

- 混凝土板：3.0 m × 2.0 m × 0.4 m，坐标单位为 m。
- 双层 HRB400 钢筋：直径 20 mm，保护层参考厚度 40 mm，间距 500 mm。
- 泡沫缺陷：23 个 EPS 立方体/球体对象。
- 泡沫板：3 个，参数见 `model/paraview/foam_plates_metadata.json`。
- ParaView 状态：`model/东至南模型.pvsm`。

## gprMax 与 GPU

本机环境已经实测连接到 CUDA：NVIDIA GeForce RTX 5060 8 GB、CUDA Toolkit 13.4、gprMax 4.0.1、PyCUDA 2026.1。运行 gprMax 前需要先调用 VS2022 BuildTools 的 `VsDevCmd.bat`，否则 nvcc 找不到 `cl.exe`。统一入口是 `simulation/run_gpu.cmd`。

实际日志包含：`CUDA backend using Device 0: NVIDIA GeForce RTX 5060`。

## 模型检查与体素化

```powershell
python simulation/scripts/inspect_paraview_model.py
python simulation/scripts/voxelize_current_model.py --dx 0.005 --outdir simulation/geometry_5mm
```

当前体素材料为混凝土、空气、钢筋和 EPS。钢筋 VTP 表面存在开放边，因此体素化脚本按模型尺寸和钢筋圆柱参数生成封闭等效体素；原始 VTP 仍保留在 `model/paraview`。

## 正演参数

- 中心频率：2.5 GHz，Ricker 波形。
- 天线：Z 极化理想 Hertzian dipole 代理，Tx/Rx 间距 40 mm；实际 CK-2500 天线结构、极化和带宽仍需实测校准。
- 扫描方向：X/试块长度方向。
- 扫描间距：100 mm，31 道。
- FDTD 域：3.4 m × 2.4 m × 0.8 m，几何体插入点为 (0.1, 0.1, 0.1) m。
- 材料初值：混凝土 εr=6、σ=0.01 S/m；EPS εr=1.05、σ=0；空气 εr=1；钢筋 σ=1e6 S/m 的有限导电近似。

## 已完成结果

`simulation/results/20mm_bscan/` 包含 20 mm 验证网格的单道 HDF5、31 道原始 HDF5、合成 Ez B-scan 和参数记录。20 mm 网格只用于验证导入、GPU 求解和输出链路；它不能作为最终定量结果，因为钢筋和 2.5 GHz 波长均欠分辨。

5 mm 全尺寸单道和全长度 31 道 B-scan 已在 RTX 5060 上完成，约 5222 万网格单元，显存估算约 3.9 GB。结果位于 `simulation/results/5mm_ascan/` 和 `simulation/results/5mm_bscan/`，包含原始 HDF5、压缩 Ez 矩阵、B-scan PNG 和参数记录。 JPG 图像已分别整理在 `20mm_ascan/`、`20mm_bscan/`、`5mm_ascan/` 和 `5mm_bscan/` 子目录，清单见 `simulation/results/JPG_RESULTS.json`。

## 运行命令

```powershell
cmd /d /c "simulation\run_gpu.cmd simulation\inputs\current_model_20mm_ascan.in -gpu 0 --allow-underresolved"
cmd /d /c "simulation\run_gpu.cmd simulation\inputs\current_model_20mm_bscan.in -n 31 -gpu 0 --allow-underresolved"
cmd /d /c "simulation\run_gpu.cmd simulation\inputs\current_model_5mm_ascan.in -gpu 0 --allow-underresolved"
```

`--allow-underresolved` 是当前钢筋有限电导率近似下的数值链路选项。正式定量结果需要进一步做钢筋材料模型、天线参数和网格收敛性校准。

## 修正后的 A 面栅格扫描

当前栅格路径已经改为从 A 面右下侧开始，沿 X 方向由右向左扫描，完成一条线后沿 Y 方向向上移动 100 mm。Tx/Rx 间距为 **46 mm**，Tx 起点为 `(3.100, Y, 0.550)` m，Rx 起点为 `(3.054, Y, 0.550)` m，使用 X 极化理想偶极子。配置、路径清单和运行脚本位于 `simulation/raster_scan/`；20 mm 全部 PML-safe 栅格结果位于 `simulation/results/raster_20mm/`。

## X/Ex 与 Y/Ey 单道对照

为排查旧 Z 向偶极子造成的法向辐射轴向零点，新增了同一位置、同一 5 mm 网格、同一 Tx/Rx=46 mm 间距的两组单道：

- `simulation/polarization_check/x_polarization_5mm.in`：X 极化，比较 `Ex`；
- `simulation/polarization_check/y_polarization_5mm.in`：Y 极化，比较 `Ey`；
- 天线位置：Tx `(1.55, 1.10, 0.55)` m，Rx `(1.504, 1.10, 0.55)` m；
- 对照图和时间窗指标：`simulation/results/polarization_check/`。

两组都能看到明显的早期直达/耦合波，Y/Ey 的早期峰值更大；后续 1–8 ns 信号仍然较弱，说明仅修正极化方向还不能解决全部反射问题，还需要继续校准天线模型、钢筋材料和信号处理。

## 局部 5 mm B-scan（Dewow + 带通）

当前局部扫描配置位于 `simulation/local_bscan/local_bscan_5mm.in`：X=1.20–2.80 m、Y=1.10 m、5 mm 道间距、Tx/Rx=46 mm、天线贴面 Z=0.500 m。后处理使用 1.5 ns moving-average Dewow，并使用 0.25–2.60 GHz 四阶零相位 Butterworth 带通。
