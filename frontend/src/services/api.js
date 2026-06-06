import axios from 'axios';

// Point explicitly to your local running FastAPI instance gateway port
const API_BASE_URL = 'http://127.0.0.1:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const agentApi = {
  /**
   * Transmits conversation message data payloads to the Multi-Agent Core Graph
   */
  sendChatMessage: async (message, awaitingConfirmation = false, suggestedCorrection = null) => {
    const response = await apiClient.post('/chat', {
      message: message,
      awaiting_confirmation: awaitingConfirmation,
      suggested_correction: suggestedCorrection,
    });
    return response.data;
  },

  /**
   * Streams a binary multipart snippet query file to the Multimodal Input Vision Agent
   */
  uploadQueryImage: async (fileObject) => {
    const formData = new FormData();
    formData.append('file', fileObject);
    
    const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Retrieves high-level indexed metrics directly from the root relational catalog
   */
  getDatabaseAnalytics: async () => {
    const response = await apiClient.get('/analytics');
    return response.data;
  },

  /**
   * Uploads multiple documents for OCR indexing into the spatial DB
   */
  indexDocuments: async (files, bookName) => {
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }
    formData.append('book_name', bookName);
    
    const response = await axios.post(`${API_BASE_URL}/index-document`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};