# 全局 5 mm 栅格扫描

坐标约定：X 为 3 m 长度方向，Y 为 2 m 面内方向，Z 为板厚方向。A 面全局范围为 X=0.1…3.1、Y=0.1…2.1、Z=0.5 m。

- 测线间距：100 mm；21 条测线；Y 从 0.1 m 到 2.1 m。
- 道间距：5 mm；每条 3 m；601 道。
- 扫描顺序：从 A 面右下角开始，沿 X 由右向左；完成一条后 Y 向上 100 mm。
- Tx 起点：`(3.100, Y, 0.500)` m；Rx 起点：`(3.054, Y, 0.500)` m。
- Tx/Rx：46 mm；`#src_steps` 与 `#rx_steps` 均为 `-0.005 0 0`。
- 极化：X；几何：`simulation/geometry_5mm/geometry.h5`。

输入文件位于 `global_5mm/line_###/input.in`，完整参数见 `global_5mm/raster_manifest.json`。运行命令：

```powershell
C:\env\gprmax_v4\Scripts\python.exe simulation/scripts/run_raster_scan.py --grid global_5mm --ntraces 601 --skip-complete
```
