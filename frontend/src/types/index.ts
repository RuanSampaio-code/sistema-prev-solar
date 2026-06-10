export type UserRole = "admin" | "operator";

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
}

export type ImageStatus = "pending" | "processing" | "done" | "error";

export interface Panel {
  panel_id: number;
  area_m2: number;
  kwh_month: number;
  centroid_x: number;
  centroid_y: number;
  bbox_x: number;
  bbox_y: number;
  bbox_width: number;
  bbox_height: number;
  confidence_mean: number;
}

export interface Result {
  id: number;
  panel_count: number;
  detected_area_m2: number;
  estimated_kwh_month: number;
  processed_at: string;
  panels?: Panel[];
}

export interface ImageRecord {
  id: number;
  original_name: string;
  file_size_kb: number;
  status: ImageStatus;
  uploaded_at: string;
  result: Result | null;
}

export interface PaginatedImages {
  items: ImageRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DashboardStats {
  total_images: number;
  total_processed: number;
  total_panels: number;
  highest_kwh_month: number;
  ranking: { original_name: string; kwh_month: number }[];
}
