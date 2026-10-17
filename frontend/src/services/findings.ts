import { apiClient } from './apiClient';
import { FindingDetail, FindingListResponse } from '../types';

export interface FindingFilterParams {
  project_id?: string;
  scan_id?: string;
  severity?: string;
  status?: string;
  category?: string;
  limit?: number;
  offset?: number;
}

export const getFindings = async (params: FindingFilterParams = {}): Promise<FindingListResponse> => {
  const response = await apiClient.get<FindingListResponse>('/findings', { params });
  return response.data;
};

export const getFindingById = async (findingId: string): Promise<FindingDetail> => {
  const response = await apiClient.get<FindingDetail>(`/findings/${findingId}`);
  return response.data;
};
