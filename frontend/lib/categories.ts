import { requestJson } from "./api";

export interface Category {
  id: string;
  name: string;
  color: string;
  is_global: boolean;
  created_at: string;
}

interface CategoryListResponse {
  items: Category[];
}

export async function listCategories(): Promise<Category[]> {
  return (await requestJson<CategoryListResponse>("/categories")).items;
}
