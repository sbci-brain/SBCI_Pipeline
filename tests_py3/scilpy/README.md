# scilpy compatibility tests

This directory contains sample FreeSurfer surfaces, annotations, an ROI mesh,
and scripts used to compare the legacy and Python 3 surface-processing paths.

## Test data

The bundled files are a small test fixture derived from subject `100307`:

- `lh.pial`, `rh.pial`: left and right pial surfaces
- `lh.white`, `rh.white`: left and right white-matter surfaces
- `lh.aparc.a2009s.annot`, `rh.aparc.a2009s.annot`: cortical annotations
- `roi_00004.vtk`: a subcortical ROI surface used as a test placeholder

## Running the scripts

From the repository root, run the Python 3 path with:

```bash
bash tests_py3/scilpy/test_new_scilpy.sh
```

Results default to `tests_py3/scilpy/results/new`. Override that location with
`SBCI_NEW_TEST_RESULTS`. The legacy comparison script uses
`SBCI_OLD_TEST_RESULTS` and requires the legacy scilpy commands on `PATH`:

```bash
bash tests_py3/scilpy/test_old_scilpy.sh
```

Use `compare_vtk_files.py` and `compare_np_files.py` to compare generated VTK,
NPY, and NPZ outputs by content rather than relying only on file checksums.
