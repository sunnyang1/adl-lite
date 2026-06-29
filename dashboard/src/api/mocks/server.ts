import { setupServer } from 'msw/node';
import { handlers } from './handlers';

/** MSW server instance for API mocking */
export const server = setupServer(...handlers);
