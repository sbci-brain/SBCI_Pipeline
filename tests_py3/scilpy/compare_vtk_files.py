import argparse

import numpy as np
from vtkmodules.vtkIOLegacy import vtkPolyDataReader
from vtkmodules.util.numpy_support import vtk_to_numpy


def read_vtk_file(filename):
    if filename.endswith('.vtk'):
        reader = vtkPolyDataReader()
    else:
        raise ValueError(f'Unsupported file extension for file: {filename}')

    reader.SetFileName(filename)
    reader.Update()
    return reader.GetOutput()


def get_numpy_data(dataset):
    data = {}

    # 提取点坐标
    points = dataset.GetPoints()
    if points:
        data['points'] = vtk_to_numpy(points.GetData())

    # 提取点数据
    point_data = dataset.GetPointData()
    for i in range(point_data.GetNumberOfArrays()):
        array = point_data.GetArray(i)
        data[f'point_data_{array.GetName()}'] = vtk_to_numpy(array)

    # 提取单元格数据
    cell_data = dataset.GetCellData()
    for i in range(cell_data.GetNumberOfArrays()):
        array = cell_data.GetArray(i)
        data[f'cell_data_{array.GetName()}'] = vtk_to_numpy(array)

    # 提取多边形单元
    polys = dataset.GetPolys()
    if polys:
        data['polys'] = vtk_to_numpy(polys.GetData())

    # 提取线单元
    lines = dataset.GetLines()
    if lines:
        data['lines'] = vtk_to_numpy(lines.GetData())

    # 提取顶点单元
    verts = dataset.GetVerts()
    if verts:
        data['verts'] = vtk_to_numpy(verts.GetData())

    # 提取三角带单元
    strips = dataset.GetStrips()
    if strips:
        data['strips'] = vtk_to_numpy(strips.GetData())

    return data


def compare_vtk_data(data1, data2, atol=1e-8):
    if set(data1.keys()) != set(data2.keys()):
        print('Data keys do not match.')
        print(f'Keys in first file: {set(data1.keys())}')
        print(f'Keys in second file: {set(data2.keys())}')
        return False

    for key in data1:
        array1 = data1[key]
        array2 = data2[key]
        if array1.shape != array2.shape:
            print(f'Shape mismatch for {key}: {array1.shape} vs {array2.shape}')
            return False
        if np.issubdtype(array1.dtype, np.floating):
            if not np.allclose(array1, array2, atol=atol):
                print(f'Data mismatch in floating point array: {key}')
                return False
        else:
            if not np.array_equal(array1, array2):
                print(f'Data mismatch in array: {key}')
                return False
    return True


def main():
    parser = argparse.ArgumentParser(description='Compare two VTK files for data consistency.')
    parser.add_argument('file1', type=str, help='Path to the first VTK file (.vtk)')
    parser.add_argument('file2', type=str, help='Path to the second VTK file (.vtk)')
    parser.add_argument('--atol', type=float, default=1e-8,
                        help='Absolute tolerance for floating point comparison (default: 1e-8)')
    args = parser.parse_args()

    file1 = args.file1
    file2 = args.file2
    atol = args.atol

    dataset1 = read_vtk_file(file1)
    dataset2 = read_vtk_file(file2)

    data1 = get_numpy_data(dataset1)
    data2 = get_numpy_data(dataset2)

    if compare_vtk_data(data1, data2, atol=atol):
        print(f'The two VTK files {file1} and {file2} contain exactly the same data.')
    else:
        print('The two VTK files differ.')


if __name__ == '__main__':
    main()
