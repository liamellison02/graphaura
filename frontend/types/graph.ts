export type NodeType = 'person' | 'event' | 'location';

export interface GraphNode {
  id: string;
  name: string;
  type: NodeType;
  val: number;
  color: string;
  metadata?: Record<string, any>;
  x?: number;
  y?: number;
  z?: number;
  fx?: number;
  fy?: number;
  fz?: number;
}

export interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  relationship: string;
  strength?: number;
  color?: string;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface PersonNode extends Omit<GraphNode, 'type' | 'metadata'> {
  type: 'person';
  metadata?: {
    role?: string;
    organization?: string;
    [key: string]: any;
  };
}

export interface EventNode extends Omit<GraphNode, 'type' | 'metadata'> {
  type: 'event';
  metadata?: {
    date?: string;
    location?: string;
    [key: string]: any;
  };
}

export interface LocationNode extends Omit<GraphNode, 'type' | 'metadata'> {
  type: 'location';
  metadata?: {
    coordinates?: {
      lat: number;
      lng: number;
    };
    type?: string;
    [key: string]: any;
  };
}

export const NODE_COLORS: Record<NodeType, string> = {
  person: '#3B82F6',
  event: '#10B981',
  location: '#EF4444',
};

export const DEFAULT_NODE_SIZE = 5;
export const MIN_NODE_SIZE = 3;
export const MAX_NODE_SIZE = 15;