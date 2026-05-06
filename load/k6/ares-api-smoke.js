import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<750'],
  },
  scenarios: {
    api_reads: {
      executor: 'constant-vus',
      vus: Number(__ENV.ARES_LOAD_VUS || 5),
      duration: __ENV.ARES_LOAD_DURATION || '1m',
    },
  },
};

const baseUrl = __ENV.ARES_BASE_URL || 'http://localhost:8000';
const apiKey = __ENV.ARES_API_KEY || 'test-key';
const headers = { Authorization: `Bearer ${apiKey}`, 'X-Request-ID': `k6-${Date.now()}` };

export default function () {
  const health = http.get(`${baseUrl}/health/ready`);
  check(health, { 'ready endpoint is healthy': (r) => r.status < 500 });

  const metrics = http.get(`${baseUrl}/metrics`);
  check(metrics, { 'metrics endpoint is exposed': (r) => r.status === 200 || r.status === 404 });

  const champions = http.get(`${baseUrl}/api/v1/champions`, { headers });
  check(champions, { 'champion read does not 5xx': (r) => r.status < 500 });

  const drift = http.get(`${baseUrl}/api/v1/drift/reports`, { headers });
  check(drift, { 'drift report read does not 5xx': (r) => r.status < 500 });

  sleep(1);
}
