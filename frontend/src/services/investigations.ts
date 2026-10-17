import { apiClient } from './apiClient';
import { InvestigationRequest, InvestigationResponse } from '../types';

export const startInvestigation = async (data: InvestigationRequest): Promise<InvestigationResponse> => {
  const response = await apiClient.post<InvestigationResponse>('/investigations', data);
  return response.data;
};

export const getInvestigationById = async (investigationId: string): Promise<InvestigationResponse> => {
  const response = await apiClient.get<InvestigationResponse>(`/investigations/${encodeURIComponent(investigationId)}`);
  return response.data;
};
