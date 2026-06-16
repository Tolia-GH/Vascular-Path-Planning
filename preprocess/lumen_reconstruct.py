import numpy as np
import pyvista as pv
from scipy.ndimage import distance_transform_edt


class VesselSDFReconstructor:
    def __init__(self,
                 voxel_resolution=0.5,
                 padding=5.0):
        """
        voxel_resolution: 体素大小 (mm)
        padding: 扩展边界 (mm)
        """
        self.voxel_resolution = voxel_resolution
        self.padding = padding

    def _create_grid(self, mesh):
        bounds = mesh.bounds  # (xmin,xmax,ymin,ymax,zmin,zmax)

        xmin, xmax, ymin, ymax, zmin, zmax = bounds

        xmin -= self.padding
        xmax += self.padding
        ymin -= self.padding
        ymax += self.padding
        zmin -= self.padding
        zmax += self.padding

        self.origin = np.array([xmin, ymin, zmin])

        self.dim = np.ceil([
            (xmax - xmin) / self.voxel_resolution,
            (ymax - ymin) / self.voxel_resolution,
            (zmax - zmin) / self.voxel_resolution
        ]).astype(int)

        return self.origin, self.dim

    def _rasterize_surface(self, mesh):
        """
        将surface voxel化
        """
        grid = np.zeros(self.dim, dtype=np.uint8)

        points = mesh.points

        idx = ((points - self.origin) /
               self.voxel_resolution).astype(int)

        idx = np.clip(idx, 0, self.dim - 1)

        grid[idx[:, 0], idx[:, 1], idx[:, 2]] = 1

        return grid

    def _compute_sdf(self, binary_grid):
        """
        计算Signed Distance Field
        """

        outside = binary_grid == 0
        inside = binary_grid == 1

        dist_out = distance_transform_edt(outside)
        dist_in = distance_transform_edt(inside)

        sdf = dist_out - dist_in

        sdf = sdf * self.voxel_resolution

        return sdf

    def _extract_surface(self, sdf, level):
        """
        Marching Cubes提取等值面
        """
        grid = pv.ImageData()

        grid.dimensions = np.array(sdf.shape)

        grid.origin = self.origin

        grid.spacing = (self.voxel_resolution,
                        self.voxel_resolution,
                        self.voxel_resolution)

        grid.point_data["sdf"] = sdf.flatten(order="F")

        surface = grid.contour([level], scalars="sdf")

        return surface

    def reconstruct(self,
                    mesh: pv.PolyData,
                    outside_thickness: float):
        """
        主函数：生成血管壁
        """

        # 1. 建立体素网格
        self._create_grid(mesh)

        # 2. 表面体素化
        binary = self._rasterize_surface(mesh)

        # 3. SDF计算
        sdf = self._compute_sdf(binary)

        # 4. 提取内壁（0）
        inner_surface = self._extract_surface(sdf, level=0)

        # 5. 提取外壁（thickness）
        outer_surface = self._extract_surface(
            sdf, level=outside_thickness
        )

        # 6. 合并成血管壁
        vessel_wall = inner_surface + outer_surface

        # 7. 清理网格
        vessel_wall = vessel_wall.clean()

        return inner_surface, outer_surface, vessel_wall

if __name__ == "__main__":
    mesh = pv.read("../source/vtk/blood_vessels.vtk")

    reconstructor = VesselSDFReconstructor(voxel_resolution=0.5, padding=5.0)

    inner, outer, wall = reconstructor.reconstruct(mesh, outside_thickness=0.75)

    plotter = pv.Plotter()

    outer.save("../source/vtk/blood_vessels_hollow.vtk")

    # plotter.add_mesh(inner)
    plotter.add_mesh(outer, color="red", opacity=0.3)
    # plotter.add_mesh(wall, color="red", opacity=0.3)

    plotter.show()