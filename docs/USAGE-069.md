# Topázio Microscope — public usage boundary

## What is verified by the repository

The application is a Python/ OpenCV Windows-oriented microscope inspection tool. Its capture layer targets UVC cameras through DirectShow (`CAP_DSHOW`) and Media Foundation (`CAP_MSMF`), with local image processing for zoom, sharpness, filters and focus heuristics.

## Without a microscope

You can install the dependencies and run the processing tests without camera hardware:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The diagnostics command may report that no camera is available; that is expected on a machine without a UVC device and does not prove camera compatibility.

## With a UVC microscope

Connect the device, allow Windows to expose it as a camera, then run:

```powershell
.\.venv\Scripts\python.exe -m topazio_microscope.diagnostics --json
.\.venv\Scripts\python.exe run_app.py
```

The application can capture PNG frames and record AVI when a compatible device and backend produce valid frames. Focus scoring is heuristic and is not a calibrated measurement.

## Portable builds and limits

The repository documents a PyInstaller command, but no portable executable is published or guaranteed by this document. Build one locally only after validating the target machine, camera backend and bundled assets. Do not treat the Repair Assistant branch as part of `main` until its PR is reviewed.

The project declares Apache-2.0 in `LICENSE`; third-party dependencies and any device firmware retain their own terms.
