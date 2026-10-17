import { apiClient } from './apiClient';
import { GraphResponse, NeighborsResponse } from '../types';

export interface GraphQueryParams {
  project_id?: string;
  finding_id?: string;
  depth?: number;
  limit?: number;
}

export interface NeighborOptions {
  direction?: 'in' | 'out' | 'both';
  relationship_type?: string;
  depth?: number;
  limit?: number;
}

export const getGraphView = async (params: GraphQueryParams = {}): Promise<GraphResponse> => {
  const response = await apiClient.get<GraphResponse>('/graph', { params });
  return response.data;
};

export const getNodeNeighbors = async (
  nodeId: string,
  optionsOrDirection: NeighborOptions | 'in' | 'out' | 'both' = 'both',
  relationshipType?: string,
  limit = 50
): Promise<NeighborsResponse> => {
  let params: any = {};
  if (typeof optionsOrDirection === 'object') {
    params = { ...optionsOrDirection };
  } else {
    params = {
      direction: optionsOrDirection,
      relationship_type: relationshipType,
      limit,
    };
  }
  const response = await apiClient.get<NeighborsResponse>(`/graph/nodes/${encodeURIComponent(nodeId)}/neighbors`, {
    params,
  });
  return response.data;
};
