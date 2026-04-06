# Testing

Run the API first:

```powershell
cd c:\Anish\Project\Omniparser_AutoUI
$env:OMNIPARSER_DEVICE="cuda"
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Then in a second terminal run the whole batch over every image in `assets`:

```powershell
cd c:\Anish\Project\Omniparser_AutoUI\testing
..\venv\Scripts\python.exe run_all_tests.py
```

The batch runner:

- reads every supported image in `testing/assets`
- writes JSON outputs into `testing/output/json`
- writes grounded overlay PNG images with bounding rectangles into `testing/output/images`
- does not write result files into the testing root folder

Run a custom folder batch:

```powershell
..\venv\Scripts\python.exe run_all_tests.py --base-url http://127.0.0.1:8010 --assets-dir .\assets --output-dir .\output
```

Run one image manually:

```powershell
..\venv\Scripts\python.exe test_ground_controls.py --image .\assets\sample_ui.png --output-dir .\output
```

Compare CPU and GPU timings:

1. Start a CPU run in one terminal:

```powershell
cd c:\Anish\Project\Omniparser_AutoUI
$env:OMNIPARSER_DEVICE="cpu"
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

2. In a second terminal, save CPU outputs:

```powershell
cd c:\Anish\Project\Omniparser_AutoUI\testing
..\venv\Scripts\python.exe run_all_tests.py --output-dir .\benchmarks\cpu
```

3. Stop the API, then start a GPU run:

```powershell
cd c:\Anish\Project\Omniparser_AutoUI
$env:OMNIPARSER_DEVICE="cuda"
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

4. Save GPU outputs:

```powershell
cd c:\Anish\Project\Omniparser_AutoUI\testing
..\venv\Scripts\python.exe run_all_tests.py --output-dir .\benchmarks\gpu
```

5. Compare the two runs:

```powershell
..\venv\Scripts\python.exe compare_timings.py --cpu-dir .\benchmarks\cpu\json --gpu-dir .\benchmarks\gpu\json
```

Files in this folder:

- `assets/`: input images for testing
- `output/json/`: generated JSON responses
- `output/images/`: generated grounded overlay images
- `common.py`: shared helpers
- `test_health.py`: checks `/health`
- `test_find_controls.py`: calls `/api/v1/find-controls`
- `test_ground_controls.py`: calls `/api/v1/ground-controls` and saves overlay PNG
- `test_openai_like.py`: calls `/v1/responses`
- `run_all_tests.py`: runs the whole batch for every image in `assets`
- `compare_timings.py`: compares CPU and GPU benchmark JSON outputs
