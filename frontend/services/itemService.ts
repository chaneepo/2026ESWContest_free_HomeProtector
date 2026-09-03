import { mockItems } from '@/mocks/mockData';
import type { Item } from '@/types';

export interface ItemService {
  getItems(): Promise<Item[]>;
  createItem(input: Omit<Item, 'id'>, items: Item[]): Promise<Item>;
  updateItem(item: Item): Promise<Item>;
  deleteItem(id: number): Promise<number>;
}

export const itemService: ItemService = {
  async getItems() { return mockItems.map((item) => ({ ...item })); },
  async createItem(input, items) { return { ...input, id: Math.max(0, ...items.map((item) => item.id)) + 1 }; },
  async updateItem(item) { return { ...item }; },
  async deleteItem(id) { return id; },
};
