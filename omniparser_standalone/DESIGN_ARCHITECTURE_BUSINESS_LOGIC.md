# Omniparser_AutoUI Design, Architecture, and Business Logic

## 1. Purpose

`Omniparser_AutoUI` is a self-contained FastAPI service for parsing UI screenshots into structured control data.

Its current responsibilities are:

- accept an image as base64 or data URL
- detect UI controls and text regions from the image
- return normalized control metadata with bounding boxes and centers
- optionally return a grounded image with drawn rectangles
- expose both project-native APIs and an OpenAI-like response API

The project is intentionally image-first. It does not require browser DOM access, native accessibility trees, or direct application integration.

## 2. Goals

### Functional goals

- detect controls from a screenshot or UI image
- return machine-readable coordinates for downstream automation or analytics
- provide a visual grounded output for verification
- support batch testing over a folder of input images
- keep the project self-contained with local code and local weights

### Non-functional goals

- simple deployment and local execution
- predictable JSON schema for downstream consumers
- minimal external runtime dependencies beyond model libraries
- compatibility with OpenAI-like client integration patterns

## 3. Non-goals

The current project does not attempt to:

- perform mouse clicks or keyboard actions
- maintain a VM session or browser session
- infer every semantic state of a control with high certainty
- guarantee accessibility-grade role classification
- provide a training pipeline for new models

Those capabilities can be added later as separate modules.

## 4. High-Level Architecture

The system is organized into four main layers.

### 4.1 API Layer

Files:

- `app/main.py`
- `app/schemas.py`

Responsibilities:

- expose HTTP endpoints
- validate request payloads using Pydantic
- translate internal exceptions into API responses
- provide an OpenAI-like `/v1/responses` compatibility surface

### 4.2 Service Layer

File:

- `app/service.py`

Responsibilities:

- decode incoming image payloads
- orchestrate OCR and control detection
- normalize raw parser output into stable response objects
- optionally include the grounded image in the response

This layer is the business orchestration layer of the application.

### 4.3 Parsing Core

Files:

- `app/core/parser_utils.py`
- `app/core/box_annotator.py`

Responsibilities:

- run OCR
- run YOLO control detection
- merge OCR regions and detected boxes
- remove overlaps and duplicate-like boxes
- annotate grounded images with rectangles and numeric labels

### 4.4 Assets and Weights Layer

Folder:

- `weights/`

Responsibilities:

- hold the local detection model weights
- allow the project to run without referencing the original OmniParser folder at runtime

## 5. Current Runtime Flow

### 5.1 Request Flow

1. Client sends image payload to one of the APIs.
2. API layer validates the request.
3. Service layer decodes the image from base64 or data URL.
4. OCR runs to identify text boxes.
5. YOLO runs to identify interactive visual regions.
6. OCR boxes and detector boxes are merged and filtered.
7. Output controls are normalized into a consistent schema.
8. If grounding is requested, a labeled overlay image is generated.
9. JSON response is returned.

### 5.2 Detection Flow

Current detection path:

- OCR: EasyOCR is used for text extraction
- detector: YOLO model from local `weights/icon_detect/model.pt`
- grounding: box annotation and image rendering from `box_annotator.py`

### 5.3 Important Current Constraint

The original Florence caption step has been disabled in the current implementation because of local runtime compatibility issues with the installed `transformers` stack.

That means the system currently emphasizes:

- reliable control box detection
- OCR-backed text control labeling
- grounded image generation

rather than rich icon caption semantics.

## 6. API Design

### 6.1 Health

`GET /health`

Purpose:

- verify service availability

Response:

- status
- service name

### 6.2 Find Controls

`POST /api/v1/find-controls`

Purpose:

- detect controls and return normalized structured output without the grounded image

Input:

- `image_base64` or `image_url`

Output:

- image dimensions
- control count
- list of controls
- optional latency

### 6.3 Ground Controls

`POST /api/v1/ground-controls`

Purpose:

- detect controls and return the grounded overlay image alongside structured output

Input:

- `image_base64` or `image_url`
- optional grounding flag

Output:

- same structured control data as `find-controls`
- `grounded_image_base64`

### 6.4 OpenAI-like Responses

`POST /v1/responses`

Purpose:

- support clients that already speak an OpenAI-style multimodal payload format

Input:

- `model`
- `input` message array
- `input_image` item with `image_base64` or `image_url`
- optional `include` values

Output:

- top-level `response` object
- human-readable summary text
- structured JSON payload embedded as output content

## 7. Data Model

Primary normalized object: `Control`

Fields:

- `id`: sequential identifier in the returned list
- `type`: current parser type, typically `text` or `icon`
- `interactivity`: heuristic boolean from parser merge logic
- `content`: OCR text when available, otherwise whatever semantic content exists
- `source`: provenance such as OCR-derived or detector-derived
- `bbox`: normalized `[x1, y1, x2, y2]` ratio coordinates
- `center`: normalized center point derived from bounding box

Design decision:

- coordinates are stored as ratios, not absolute pixels, to keep outputs resolution-independent and easier to consume in downstream automation pipelines

## 8. Business Logic

### 8.1 What the system considers a control

A control is any visually detectable UI region that is likely meaningful for UI interaction or interpretation.

Today that includes:

- text boxes identified by OCR
- icon/button-like regions identified by YOLO
- merged OCR+detector boxes where text sits inside a detected interactive region

### 8.2 Box Merging Logic

The parser merges OCR and detector outputs using these business rules:

- preserve OCR text boxes as semantic anchors
- preserve detector boxes for probable interactive UI regions
- remove or suppress boxes that strongly overlap with smaller or more precise boxes
- if OCR text appears inside a detector box, prefer carrying that OCR text into the control content
- reduce duplicate detections by overlap filtering

The practical goal is to produce cleaner controls for automation than raw detector output alone.

### 8.3 Interactivity Logic

Current interactivity is heuristic.

- OCR-only text regions are usually marked non-interactive
- YOLO-derived UI regions are treated as interactive candidates
- merged OCR-within-icon controls are interactive if the parent detector box is interactive

This is useful for first-pass UI grounding, but it is not equivalent to native accessibility metadata.

### 8.4 Grounded Image Logic

When grounding is requested:

- boxes are drawn on the image
- each box receives a numeric label
- output is encoded as base64 PNG

Purpose:

- debugging
- evaluation
- human verification
- visual audit trail for downstream action systems

### 8.5 Error Handling Logic

The API returns HTTP 400 when parsing fails.

Typical causes:

- malformed image payload
- unsupported or corrupted image bytes
- model/runtime compatibility issues
- OCR/model dependency errors

Design note:

- current error responses are intentionally simple and expose the exception string for local debugging
- for production hardening, error classes should be normalized into safer public messages with internal structured logging

## 9. Testing Architecture

Folder:

- `testing/`

### 9.1 Input and Output Layout

- `testing/assets/`: input images
- `testing/output/json/`: JSON outputs
- `testing/output/images/`: grounded overlay images

### 9.2 Test Scripts

- `test_health.py`: availability check
- `test_find_controls.py`: calls `find-controls`
- `test_ground_controls.py`: calls `ground-controls` and saves overlay image
- `test_openai_like.py`: calls `/v1/responses`
- `run_all_tests.py`: runs the full batch over every supported image in `assets`

### 9.3 Batch Testing Logic

The batch runner:

1. validates service health
2. enumerates all supported images in `assets`
3. runs each endpoint test for each image
4. saves JSON under `output/json`
5. saves grounded overlay images under `output/images`

This design keeps the testing root clean and makes visual verification easy.

## 10. Deployment and Operational Notes

### 10.1 Runtime Dependencies

Core runtime depends on:

- FastAPI
- Uvicorn
- PyTorch
- Ultralytics YOLO
- EasyOCR
- Pillow
- OpenCV
- supporting ML libraries

### 10.2 Startup Characteristics

On first use, OCR and detection components may take time to initialize.

Operational considerations:

- CPU mode is supported but slower
- GPU is preferable for larger batch volumes
- OCR initialization cost should be expected in cold start scenarios

### 10.3 Device Selection

The service reads the PowerShell environment variable `$env:OMNIPARSER_DEVICE` at startup.

Supported values:

- `cuda`
- `cpu`

Examples:

GPU startup:

```powershell
cd c:\Anish\Project\Omniparser_AutoUI
$env:OMNIPARSER_DEVICE="cuda"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

CPU startup:

```powershell
cd c:\Anish\Project\Omniparser_AutoUI
$env:OMNIPARSER_DEVICE="cpu"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Verification:

- `GET /health` returns the resolved device
- control responses also include the resolved `device` field

Important behavior:

- if `$env:OMNIPARSER_DEVICE` is set to `cuda` but CUDA is not available in the active Python environment, the service falls back to `cpu`
- for timing comparisons, set the variable explicitly before every run so the benchmark output is unambiguous

### 10.4 Self-contained Packaging

The project was intentionally copied into its own structure so runtime behavior does not depend on importing from the original OmniParser repo.

Benefits:

- easier distribution
- clearer ownership of code
- lower risk of accidental behavior drift from upstream files

## 11. Known Limitations

Current limitations include:

- no click or keyboard action execution layer
- no VM control subsystem
- no native accessibility metadata
- limited semantic interpretation for non-text icons in the current runtime path
- disabled caption model path due to compatibility constraints
- heuristic interactivity labels rather than true application state
- no explicit confidence score surfaced in the public API today

## 12. Recommended Future Architecture Extensions

### 12.1 Action Execution Layer

A future action layer could provide:

- mouse move
- click
- double click
- right click
- drag
- scroll
- type
- key combinations

This should remain separate from the parsing service for safety and composability.

### 12.2 State Inference Layer

A future control-state module could estimate:

- disabled
- highlighted
- focused
- selected
- hovered

Suggested logic:

- compare color, border, contrast, and opacity against sibling controls
- inspect focus rings or accent outlines
- use multi-frame screenshots when available
- prefer accessibility tree data if a native automation backend exists

### 12.3 Better Semantic Classification

Future improvements may include:

- restoring a caption model with a verified compatible stack
- dedicated control-type classification
- confidence scoring
- grouping controls into forms, menus, toolbars, and panels

### 12.4 Production Hardening

Recommended improvements:

- structured logging
- typed error classes
- request tracing
- model warmup endpoint
- configurable thresholds via environment variables
- request size limits and input validation hardening

## 13. Security Considerations

The current service accepts client-provided image payloads and performs ML inference locally.

Important considerations for production use:

- enforce request size limits
- add authentication and authorization
- avoid returning raw exception strings publicly
- add rate limiting
- isolate model runtime resources
- log requests safely without storing sensitive screenshots by default

## 14. Summary

`Omniparser_AutoUI` is a self-contained screenshot-to-controls service built around OCR, YOLO-based UI detection, and grounded visual verification.

Its current business value is:

- quickly convert UI screenshots into structured control coordinates
- support downstream automation and evaluation workflows
- provide visual grounding for inspection and debugging
- run batch tests on folders of UI images with organized outputs

The architecture is intentionally modular so future capabilities such as action execution, state inference, richer semantic labeling, and production hardening can be added without rewriting the current API contract.
