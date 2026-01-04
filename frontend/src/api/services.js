import api from './axios'

// Dashboard
export const dashboardAPI = {
  getSummary: () => api.get('/api/v1/dashboard/summary/'),
  getCharts: (hours = 24) => api.get(`/api/v1/dashboard/charts/?hours=${hours}`),
}

// Nodi
export const nodesAPI = {
  getAll: () => api.get('/api/v1/nodes/'),
  getById: (id) => api.get(`/api/v1/nodes/${id}/`),
  getHeartbeats: (id, hours = 24) => api.get(`/api/v1/nodes/${id}/heartbeats/?hours=${hours}`),
  getEvents: (id, days = 7) => api.get(`/api/v1/nodes/${id}/events/?days=${days}`),
  sendCommand: (id, command, params = {}) => api.post(`/api/v1/nodes/${id}/send_command/`, { command, params }),
}

// Sensori
export const sensorsAPI = {
  getReadings: (params = {}) => api.get('/api/v1/sensors/readings/', { params }),
  getLatest: () => api.get('/api/v1/sensors/readings/latest/'),
  getChartData: (nodeId, hours = 24) => api.get(`/api/v1/sensors/readings/chart_data/?node_id=${nodeId}&hours=${hours}`),
  getAlerts: (params = {}) => api.get('/api/v1/sensors/alerts/', { params }),
  acknowledgeAlert: (id) => api.post(`/api/v1/sensors/alerts/${id}/acknowledge/`),
  resolveAlert: (id) => api.post(`/api/v1/sensors/alerts/${id}/resolve/`),
}

// Sicurezza
export const securityAPI = {
  getEvents: (params = {}) => api.get('/api/v1/security/events/', { params }),
  getAlarms: (params = {}) => api.get('/api/v1/security/alarms/', { params }),
  getActiveAlarms: () => api.get('/api/v1/security/alarms/active/'),
  getAlarmById: (id) => api.get(`/api/v1/security/alarms/${id}/`),
  alarmAction: (id, action, notes = '') => api.post(`/api/v1/security/alarms/${id}/perform_action/`, { action, notes }),
  getStatistics: (days = 30) => api.get(`/api/v1/security/alarms/statistics/?days=${days}`),
  
  // Armamento
  getArmState: () => api.get('/api/v1/security/arm/'),
  setArmState: (mode, nodes = [], notes = '') => api.post('/api/v1/security/arm/', { mode, nodes, notes }),
  
  // Zone
  getZones: () => api.get('/api/v1/security/zones/'),
  armZone: (id) => api.post(`/api/v1/security/zones/${id}/arm/`),
  disarmZone: (id) => api.post(`/api/v1/security/zones/${id}/disarm/`),
}

export default {
  dashboard: dashboardAPI,
  nodes: nodesAPI,
  sensors: sensorsAPI,
  security: securityAPI,
}
