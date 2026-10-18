import axios, { AxiosError } from 'axios';
import { ErrorResponse } from '../types';

export const apiClient = axios.create({
  baseURL: (import.meta.env.VITE_API_URL || 'http://localhost:8000/api').replace(/\/+$/, ''),
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor to normalize error envelopes
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ErrorResponse>) => {
    if (error.response?.data?.error) {
      const errDetail = error.response.data.error;
      const customError = new Error(errDetail.message || 'API request failed');
      (customError as any).code = errDetail.code;
      (customError as any).details = errDetail.details;
      (customError as any).requestId = errDetail.request_id;
      (customError as any).status = error.response.status;
      return Promise.reject(customError);
    }
    return Promise.reject(error);
  }
);
