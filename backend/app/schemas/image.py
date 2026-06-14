from datetime import datetime
from pydantic import BaseModel, field_validator


class PanelResultSchema(BaseModel):
    panel_id: int
    area_m2: float
    kwh_month: float
    centroid_x: int
    centroid_y: int
    bbox_x: int
    bbox_y: int
    bbox_width: int
    bbox_height: int
    confidence_mean: float

    model_config = {"from_attributes": True}


class ResultSchema(BaseModel):
    id: int
    panel_count: int
    detected_area_m2: float
    estimated_kwh_month: float
    gsd_used_m_px: float | None = None
    processed_at: datetime
    panels: list[PanelResultSchema] | None = []

    @field_validator("panels", mode="before")
    @classmethod
    def coerce_panels(cls, v):
        return v if v is not None else []

    model_config = {"from_attributes": True}


class ImageResponse(BaseModel):
    id: int
    original_name: str
    file_size_kb: float
    status: str
    uploaded_at: datetime
    result: ResultSchema | None = None

    model_config = {"from_attributes": True}


class PaginatedImages(BaseModel):
    items: list[ImageResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class DashboardStats(BaseModel):
    total_images: int
    total_processed: int
    total_panels: int
    highest_kwh_month: float
    ranking: list[dict]
