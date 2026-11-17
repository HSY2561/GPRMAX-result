# 竖向测线 — 最新灰度 B-scan

30/30 条已完成，测线长2m，线间距50mm，道间距名义5mm，X局部坐标1.25–2.70m。正演参数保持10ns、2.5GHz Ricker、X极化源、Tx/Rx z=0.58m、名义间距46mm、10mm计算网格。模型板厚0.45m。

- [最新五类灰度图和30张上下对比图](paper_grayscale/README.md)
- [全部30条总览](paper_grayscale/overview_30_lines.jpg)
- [原始三分量NPZ](radar_profiles/)
- [几何剖面](geometry_sections/)
- [C-scan](c_scan/)

旧紫色图、旧绝对值灰度图、旧重复排版已从当前文件目录移除；不重写Git历史。新图直接读取gprMax数值场，Ex/Ey/Ez保留正负号，合成模值明确为非负。详情和限制见paper_grayscale/processing_manifest.json。
