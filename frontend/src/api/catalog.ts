import { api } from "./client";
import type {
  ApiParams,
  Component,
  ComponentInput,
  Paginated,
  Product,
  ProductInput,
  ProductVariant,
  VariantInput,
} from "./types";

export async function listProducts(
  params?: ApiParams,
): Promise<Paginated<Product>> {
  const { data } = await api.get<Paginated<Product>>("/products/", { params });
  return data;
}

export async function createProduct(input: ProductInput): Promise<Product> {
  const { data } = await api.post<Product>("/products/", input);
  return data;
}

export async function getProduct(id: number): Promise<Product> {
  const { data } = await api.get<Product>(`/products/${id}/`);
  return data;
}

export async function updateProduct(
  id: number,
  input: Partial<ProductInput>,
): Promise<Product> {
  const { data } = await api.patch<Product>(`/products/${id}/`, input);
  return data;
}

export async function archiveProduct(id: number): Promise<void> {
  await api.delete(`/products/${id}/`);
}

export async function listVariants(
  params?: ApiParams,
): Promise<Paginated<ProductVariant>> {
  const { data } = await api.get<Paginated<ProductVariant>>("/variants/", {
    params,
  });
  return data;
}

export async function createVariant(input: VariantInput): Promise<ProductVariant> {
  const { data } = await api.post<ProductVariant>("/variants/", input);
  return data;
}

export async function getVariant(id: number): Promise<ProductVariant> {
  const { data } = await api.get<ProductVariant>(`/variants/${id}/`);
  return data;
}

export async function updateVariant(
  id: number,
  input: Partial<VariantInput>,
): Promise<ProductVariant> {
  const { data } = await api.patch<ProductVariant>(`/variants/${id}/`, input);
  return data;
}

export async function deleteVariant(id: number): Promise<void> {
  await api.delete(`/variants/${id}/`);
}

export async function listProductVariants(
  productId: number,
  params?: ApiParams,
): Promise<Paginated<ProductVariant>> {
  const { data } = await api.get<Paginated<ProductVariant>>(
    `/products/${productId}/variants/`,
    { params },
  );
  return data;
}

export async function createProductVariant(
  productId: number,
  input: Omit<VariantInput, "product">,
): Promise<ProductVariant> {
  const { data } = await api.post<ProductVariant>(
    `/products/${productId}/variants/`,
    input,
  );
  return data;
}

export async function listComponents(
  params?: ApiParams,
): Promise<Paginated<Component>> {
  const { data } = await api.get<Paginated<Component>>("/components/", {
    params,
  });
  return data;
}

export async function createComponent(
  input: ComponentInput,
): Promise<Component> {
  const { data } = await api.post<Component>("/components/", input);
  return data;
}

export async function getComponent(id: number): Promise<Component> {
  const { data } = await api.get<Component>(`/components/${id}/`);
  return data;
}

export async function updateComponent(
  id: number,
  input: Partial<ComponentInput>,
): Promise<Component> {
  const { data } = await api.patch<Component>(`/components/${id}/`, input);
  return data;
}

export async function deactivateComponent(id: number): Promise<void> {
  await api.delete(`/components/${id}/`);
}

export async function listProductComponents(
  productId: number,
  params?: ApiParams,
): Promise<Paginated<Component>> {
  const { data } = await api.get<Paginated<Component>>(
    `/products/${productId}/components/`,
    { params },
  );
  return data;
}

export async function createProductComponent(
  productId: number,
  input: Omit<ComponentInput, "product">,
): Promise<Component> {
  const { data } = await api.post<Component>(
    `/products/${productId}/components/`,
    input,
  );
  return data;
}
