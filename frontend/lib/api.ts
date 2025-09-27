import axios from 'axios';
import { z } from 'zod';
import { GraphData, GraphNode, GraphLink } from '@/types/graph';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

const GraphNodeSchema = z.object({
  id: z.string(),
  name: z.string(),
  type: z.enum(['person', 'event', 'location']),
  val: z.number(),
  color: z.string(),
  metadata: z.record(z.any()).optional(),
});

const GraphLinkSchema = z.object({
  source: z.string(),
  target: z.string(),
  relationship: z.string(),
  strength: z.number().optional(),
});

const GraphDataSchema = z.object({
  nodes: z.array(GraphNodeSchema),
  links: z.array(GraphLinkSchema),
});

export const graphApi = {
  async getGraph(): Promise<GraphData> {
    const response = await api.get('/graph');
    return GraphDataSchema.parse(response.data);
  },

  async getNode(nodeId: string): Promise<GraphNode> {
    const response = await api.get(`/graph/nodes/${nodeId}`);
    return GraphNodeSchema.parse(response.data);
  },

  async createNode(node: Omit<GraphNode, 'id'>): Promise<GraphNode> {
    const response = await api.post('/graph/nodes', node);
    return GraphNodeSchema.parse(response.data);
  },

  async updateNode(nodeId: string, updates: Partial<GraphNode>): Promise<GraphNode> {
    const response = await api.patch(`/graph/nodes/${nodeId}`, updates);
    return GraphNodeSchema.parse(response.data);
  },

  async deleteNode(nodeId: string): Promise<void> {
    await api.delete(`/graph/nodes/${nodeId}`);
  },

  async createLink(link: Omit<GraphLink, 'color'>): Promise<GraphLink> {
    const response = await api.post('/graph/links', link);
    return GraphLinkSchema.parse(response.data);
  },

  async deleteLink(sourceId: string, targetId: string): Promise<void> {
    await api.delete(`/graph/links/${sourceId}/${targetId}`);
  },

  async searchNodes(query: string): Promise<GraphNode[]> {
    const response = await api.get('/graph/search', { params: { q: query } });
    return z.array(GraphNodeSchema).parse(response.data);
  },

  async getNeighbors(nodeId: string, depth: number = 1): Promise<GraphData> {
    const response = await api.get(`/graph/nodes/${nodeId}/neighbors`, {
      params: { depth },
    });
    return GraphDataSchema.parse(response.data);
  },
};

export const r2rApi = {
  async uploadDocument(file: File, metadata?: Record<string, any>): Promise<string> {
    const formData = new FormData();
    formData.append('file', file);
    if (metadata) {
      formData.append('metadata', JSON.stringify(metadata));
    }

    const response = await api.post('/r2r/documents', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data.document_id;
  },

  async query(query: string, documentId?: string): Promise<any> {
    const response = await api.post('/r2r/query', {
      query,
      document_id: documentId,
      search_settings: {
        use_hybrid_search: true,
        limit: 10,
      },
    });
    return response.data;
  },

  async extractEntities(documentId: string): Promise<GraphData> {
    const response = await api.post(`/r2r/documents/${documentId}/extract`);
    return GraphDataSchema.parse(response.data);
  },
};

export const authApi = {
  async login(email: string, password: string): Promise<{ token: string; user: any }> {
    const response = await api.post('/auth/login', { email, password });
    localStorage.setItem('auth_token', response.data.token);
    return response.data;
  },

  async logout(): Promise<void> {
    await api.post('/auth/logout');
    localStorage.removeItem('auth_token');
  },

  async register(email: string, password: string, name: string): Promise<any> {
    const response = await api.post('/auth/register', { email, password, name });
    return response.data;
  },

  async getCurrentUser(): Promise<any> {
    const response = await api.get('/auth/me');
    return response.data;
  },
};