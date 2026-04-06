from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ImageRequest(BaseModel):
    image_base64: str | None = None
    image_url: str | None = None
    include_grounded_image: bool = False


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class Point(BaseModel):
    x: float
    y: float


class Control(BaseModel):
    id: int
    type: str
    interactivity: bool
    content: str | None = None
    source: str | None = None
    bbox: BoundingBox
    center: Point


class ControlsResponse(BaseModel):
    model: str
    device: str | None = None
    image_width: int
    image_height: int
    control_count: int
    controls: list[Control]
    grounded_image_base64: str | None = None
    latency_seconds: float | None = None


class OpenAIInputText(BaseModel):
    type: Literal["input_text"]
    text: str


class OpenAIInputImage(BaseModel):
    type: Literal["input_image"]
    image_url: str | None = None
    image_base64: str | None = None


class OpenAIMessage(BaseModel):
    role: str
    content: list[OpenAIInputText | OpenAIInputImage]


class OpenAIResponsesRequest(BaseModel):
    model: str | None = None
    input: list[OpenAIMessage]
    include: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
