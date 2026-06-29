import { http, HttpResponse } from 'msw';
import { MOCK_CAPABILITIES, MOCK_STATUSES, MOCK_HISTORY, MOCK_MODE, MOCK_VERIFY } from '../mocks';

/** MSW request handlers for ADL Lite API */
export const handlers = [
  // GET /api/v1/consensus/list - List all capabilities
  http.get('/api/v1/consensus/list', ({ request }) => {
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get('limit') || '20');
    const offset = parseInt(url.searchParams.get('offset') || '0');

    const paginatedCapabilities = MOCK_CAPABILITIES.slice(offset, offset + limit);

    return HttpResponse.json({
      capabilities: paginatedCapabilities,
      total: MOCK_CAPABILITIES.length,
      count: paginatedCapabilities.length,
      offset,
      limit,
    });
  }),

  // GET /api/v1/consensus/:adl_id/status - Get capability status
  http.get('/api/v1/consensus/:adl_id/status', ({ params }) => {
    const { adl_id } = params;
    const status = MOCK_STATUSES[adl_id as string];

    if (!status) {
      return HttpResponse.json(
        { detail: `Capability ${adl_id} not found` },
        { status: 404 }
      );
    }

    return HttpResponse.json({
      adl_id,
      status: status.status,
      confidence: status.confidence,
      validators: status.validators,
      dev_mode: status.dev_mode,
    });
  }),

  // GET /api/v1/consensus/:adl_id/history - Get capability history
  http.get('/api/v1/consensus/:adl_id/history', ({ params }) => {
    const { adl_id } = params;
    const history = MOCK_HISTORY[adl_id as string];

    if (!history) {
      return HttpResponse.json(
        { detail: `Capability ${adl_id} not found` },
        { status: 404 }
      );
    }

    return HttpResponse.json({
      adl_id,
      events: history,
    });
  }),

  // GET /api/v1/consensus/mode - Get system mode
  http.get('/api/v1/consensus/mode', () => {
    return HttpResponse.json(MOCK_MODE);
  }),

  // POST /api/v1/consensus/register - Register new capability
  http.post('/api/v1/consensus/register', async ({ request }) => {
    const body = await request.json() as { adl_id: string };
    const { adl_id } = body;

    // Mock registration - in reality this would add to the backend
    return HttpResponse.json({
      adl_id,
      status: 'provisional',
      confidence: 0.5,
      validators: [],
      dev_mode: true,
    });
  }),

  // POST /api/v1/consensus/transition - Transition capability status
  http.post('/api/v1/consensus/transition', async ({ request }) => {
    const body = await request.json() as { adl_id: string; to_status: string };
    const { adl_id, to_status } = body;

    const status = MOCK_STATUSES[adl_id];
    if (!status) {
      return HttpResponse.json(
        { detail: `Capability ${adl_id} not found` },
        { status: 404 }
      );
    }

    return HttpResponse.json({
      adl_id,
      status: to_status,
      confidence: status.confidence,
      validators: status.validators,
      dev_mode: status.dev_mode,
    });
  }),

  // POST /api/v1/consensus/verify - Verify capability integrity
  http.post('/api/v1/consensus/verify', async ({ request }) => {
    const body = await request.json() as { adl_id: string };
    const { adl_id } = body;

    const verify = MOCK_VERIFY[adl_id];
    if (!verify) {
      return HttpResponse.json(
        { detail: `Capability ${adl_id} not found` },
        { status: 404 }
      );
    }

    return HttpResponse.json(verify);
  }),

  // POST /api/v1/consensus/fork - Fork capability
  http.post('/api/v1/consensus/fork', async ({ request }) => {
    const body = await request.json() as { original_id: string; fork_id: string };
    const { original_id, fork_id } = body;

    return HttpResponse.json({
      original_id,
      fork_id,
      status: 'forked',
      confidence: 0.7,
      validators: [],
      dev_mode: true,
    });
  }),
];
