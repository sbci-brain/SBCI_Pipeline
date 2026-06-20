import argparse
import os

import numpy as np


def load_numpy_file(filename):
    if filename.endswith('.npy'):
        data = np.load(filename, allow_pickle=True)
        return data
    elif filename.endswith('.npz'):
        data = np.load(filename, allow_pickle=True)
        return {key: data[key] for key in data.files}
    else:
        raise ValueError(f'Unsupported file extension for file: {filename}')


def compare_arrays(arr1, arr2, atol=1e-8):
    if arr1.shape != arr2.shape:
        print(f'  - Shape mismatch: {arr1.shape} vs {arr2.shape}')
        return False

    if arr1.dtype != arr2.dtype:
        print(f'  - Dtype mismatch: {arr1.dtype} vs {arr2.dtype}')
        return False

    if np.issubdtype(arr1.dtype, np.floating):
        if not np.allclose(arr1, arr2, atol=atol):
            diff_indices = np.where(~np.isclose(arr1, arr2, atol=atol))
            print('  - Floating point arrays are not equal within the given tolerance.')
            print(f'    Differences found at indices: {diff_indices}')
            return False
    else:
        if not np.array_equal(arr1, arr2):
            diff_indices = np.where(arr1 != arr2)
            print('  - Arrays are not equal.')
            print(f'    Differences found at indices: {diff_indices}')
            return False

    return True


def compare_np_files(file1, file2, atol=1e-8):
    ext1 = os.path.splitext(file1)[1].lower()
    ext2 = os.path.splitext(file2)[1].lower()
    if ext1 != ext2:
        print(f'File extension mismatch: {file1} is {ext1} while {file2} is {ext2}.')
        return False

    data1 = load_numpy_file(file1)
    data2 = load_numpy_file(file2)

    is_npz1 = isinstance(data1, dict)
    is_npz2 = isinstance(data2, dict)
    assert is_npz2 == is_npz1, f'File types mismatch.'

    if not is_npz1:  # .npy files
        if compare_arrays(data1, data2, atol=atol):
            return True
        else:
            return False
    else:  # .npz files
        keys1 = set(data1.keys())
        keys2 = set(data2.keys())

        if keys1 != keys2:
            print(f'  - Key mismatch between .npz files:')
            print(f'    Keys in {file1}: {sorted(keys1)}')
            print(f'    Keys in {file2}: {sorted(keys2)}')
            return False

        all_equal = True
        for key in sorted(keys1):
            arr1 = data1[key]
            arr2 = data2[key]
            if not compare_arrays(arr1, arr2, atol=atol):
                print(f'  - Arrays {key} are different.')
                all_equal = False
        return all_equal


def main():
    parser = argparse.ArgumentParser(description='Compare two .npy or .npz files for data consistency.')
    parser.add_argument('file1', type=str, help='Path to the first .npy or .npz file')
    parser.add_argument('file2', type=str, help='Path to the second .npy or .npz file')
    parser.add_argument('--atol', type=float, default=1e-8,
                        help='Absolute tolerance for floating point comparison (default: 1e-8)')
    args = parser.parse_args()

    file1 = args.file1
    file2 = args.file2
    atol = args.atol

    if compare_np_files(file1, file2, atol=atol):
        print(f'The two files {file1} and {file2} contain exactly the same data.')
    else:
        print('The two files differ.')


if __name__ == '__main__':
    main()
