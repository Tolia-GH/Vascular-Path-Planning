import vtk

# 读取你的中心线数据
reader = vtk.vtkPolyDataReader()
reader.SetFileName("D:/SIAT/slicer_files/Centerline/Centerline_model.vtk")
reader.Update()
polyData = reader.GetOutput()

# 创建平滑滤波器（使用 vtkSmoothPolyDataFilter）
smoother = vtk.vtkSmoothPolyDataFilter()
smoother.SetInputData(polyData)
smoother.SetNumberOfIterations(400)   # 可调整
smoother.SetRelaxationFactor(0.3)    # 控制平滑程度
smoother.FeatureEdgeSmoothingOff()
smoother.BoundarySmoothingOn()
smoother.Update()

# 将结果保存或导入 Slicer
smoothedPolyData = smoother.GetOutput()

# 导出为 .vtk 文件
writer = vtk.vtkPolyDataWriter()
writer.SetFileName("D:/SIAT/slicer_files/Centerline/smoothed_centerline.vtk")
writer.SetInputData(smoothedPolyData)
writer.Write()
