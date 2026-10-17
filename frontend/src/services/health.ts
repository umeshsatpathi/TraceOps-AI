import { apiClient } from './apiClient';
import { HealthResponse } from '../types';

export const getHealth = async (): Promise<HealthResponse> => {
  const response = await apiClient.get<HealthResponse>('/health');
  return response.data;
};
