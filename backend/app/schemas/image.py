from datetime import datetime
from pydantic import BaseModel


class ResultSchema(BaseModel):
    id: int
    panel_count: int
    detected_area_m2: float
    estimated_kwh_month: float
    processed_at: datetime

    model_config = {"from_attributes": True}


class ImageResponse(BaseModel):
    id: int
    consumer_unit: str
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
