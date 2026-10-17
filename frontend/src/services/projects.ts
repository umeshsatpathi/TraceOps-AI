import { apiClient } from './apiClient';
import { ProjectListResponse, ProjectSummary } from '../types';

export const getProjects = async (limit = 50, offset = 0): Promise<ProjectListResponse> => {
  const response = await apiClient.get<ProjectListResponse>('/projects', {
    params: { limit, offset },
  });
  return response.data;
};

export const getProjectById = async (projectId: string): Promise<ProjectSummary> => {
  const response = await apiClient.get<ProjectSummary>(`/projects/${projectId}`);
  return response.data;
};
