import { apiClient } from './apiClient';
import {
  BolaVerificationRequest,
  BolaVerificationResponse,
  ScanCreateRequest,
  ScanListResponse,
  ScanResponse,
} from '../types';

export interface ScanFilterParams {
  project_id?: string;
  limit?: number;
  offset?: number;
}

export const getScans = async (params: ScanFilterParams = {}): Promise<ScanListResponse> => {
  const response = await apiClient.get<ScanListResponse>('/scans', { params });
  return response.data;
};

export const createScan = async (projectId: string, data: ScanCreateRequest): Promise<ScanResponse> => {
  const response = await apiClient.post<ScanResponse>(`/projects/${encodeURIComponent(projectId)}/scans`, data);
  return response.data;
};

export const getScanById = async (scanId: string): Promise<ScanResponse> => {
  const response = await apiClient.get<ScanResponse>(`/scans/${encodeURIComponent(scanId)}`);
  return response.data;
};

export const verifyBola = async (data: BolaVerificationRequest): Promise<BolaVerificationResponse> => {
  const response = await apiClient.post<BolaVerificationResponse>('/verification/bola', data);
  return response.data;
};
