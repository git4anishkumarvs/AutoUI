# Omniparser_AutoUI

Self-contained FastAPI project for UI control detection and grounding.

## APIs

- `POST /api/v1/find-controls`
  Returns normalized controls from an input image.
- `POST /api/v1/ground-controls`
  Returns normalized controls plus an annotated image with rectangles.
- `POST /v1/responses`
  OpenAI-like endpoint that accepts an image in an `input_image` item and returns both text and structured JSON.

## Project layout

- `app/main.py` FastAPI app and routes
- `app/service.py` parsing service and output normalization
- `app/core/` copied parser core used by this project
- `weights/` local detector and caption model weights used by this project

## Run

Set the device before starting the app. The service reads `$env:OMNIPARSER_DEVICE` at startup.

Recommended GPU startup:

```powershell
cd c:\Anish\Project\Omniparser_AutoUI
$env:OMNIPARSER_DEVICE="cuda"
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

CPU startup:

```powershell
cd c:\Anish\Project\Omniparser_AutoUI
$env:OMNIPARSER_DEVICE="cpu"
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Verify the active device after startup:

```powershell
curl http://127.0.0.1:8010/health
```

The response includes the resolved device, for example `cuda` or `cpu`. If `cuda` is requested but unavailable in the active Python environment, the service falls back to `cpu`.

## Example requests

`find-controls`

```json
{
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

`ground-controls`

```json
{
  "image_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "include_grounded_image": true
}
```

OpenAI-like `responses`

```json
{
  "model": "omniparser-autoui",
  "include": ["grounded_image"],
  "input": [
    {
      "role": "user",
      "content": [
        { "type": "input_text", "text": "Find every control in this UI." },
        { "type": "input_image", "image_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..." }
      ]
    }
  ]
}
```

## Notes

- Bounding boxes are returned as ratios in `[0, 1]`.
- The project loads weights from its own local `weights/` directory.
- Set `$env:OMNIPARSER_DEVICE` before starting Uvicorn if you want to force `cpu` or `cuda`.
- `/health` and control responses include the active device for timing comparisons.
