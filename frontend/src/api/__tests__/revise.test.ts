import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as client from '../client';
import { reviseApi } from '../revise';

describe('reviseApi', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('getSession passes module_id when provided', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ items: [] } as never);
    await reviseApi.getSession('m1');
    expect(spy).toHaveBeenCalledWith('/revise/session?module_id=m1');
  });

  it('getSession omits module_id when absent', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ items: [] } as never);
    await reviseApi.getSession();
    expect(spy).toHaveBeenCalledWith('/revise/session');
  });

  it('postAnswer posts ref + selected_index', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({} as never);
    await reviseApi.postAnswer('REF', 2);
    expect(spy).toHaveBeenCalledWith('/revise/answer', {
      method: 'POST',
      body: JSON.stringify({ ref: 'REF', selected_index: 2 }),
    });
  });
});
