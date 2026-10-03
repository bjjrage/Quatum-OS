-- Trading / Quant OS control plane, migration 0002.
-- Atomic Compare-And-Swap (CAS) RPC function for concurrent writers.
-- PostgREST RPC endpoint: POST /rest/v1/rpc/quant_os_cas_put

-- Add data_hash column to mutable tables for fast, canonical hash matching
alter table if exists public.system_instances add column if not exists data_hash text;
alter table if exists public.strategy_registry add column if not exists data_hash text;
alter table if exists public.strategy_rule_evidence add column if not exists data_hash text;
alter table if exists public.counterparty_theses add column if not exists data_hash text;
alter table if exists public.paper_accounts add column if not exists data_hash text;
alter table if exists public.paper_orders add column if not exists data_hash text;
alter table if exists public.paper_positions add column if not exists data_hash text;
alter table if exists public.capital_pockets add column if not exists data_hash text;
alter table if exists public.prop_rule_profiles add column if not exists data_hash text;
alter table if exists public.event_clusters add column if not exists data_hash text;
alter table if exists public.market_data_files add column if not exists data_hash text;
alter table if exists public.execution_orders add column if not exists data_hash text;

create or replace function public.quant_os_cas_put(
  p_table text,
  p_pk text,
  p_key text,
  p_row jsonb,
  p_expected_hash text,
  p_new_hash text
) returns jsonb
language plpgsql
security definer
as $$
declare
  v_current_hash text;
  v_current_payload jsonb;
begin
  -- 1. Query with row-level lock (FOR UPDATE) to prevent concurrent TOCTOU race
  execute format(
    'select data_hash, payload from public.%I where %I = $1 for update',
    p_table, p_pk
  ) into v_current_hash, v_current_payload using p_key;

  -- 2. Handle non-existent record
  if v_current_payload is null then
    if p_expected_hash is not null and p_expected_hash <> '' then
      raise exception 'CAS_RECORD_NOT_FOUND: expected hash % but record does not exist on %[%%]', p_expected_hash, p_table, p_key
        using errcode = 'P0001';
    end if;

    -- Insert new row
    execute format(
      'insert into public.%I select * from jsonb_populate_record(null::public.%I, $1)',
      p_table, p_table
    ) using (p_row || jsonb_build_object('data_hash', p_new_hash));

    return jsonb_build_object('status', 'INSERTED', 'data_hash', p_new_hash);
  end if;

  -- 3. Check for identical payload / hash (idempotent no-op)
  if v_current_hash = p_new_hash then
    return jsonb_build_object('status', 'UNCHANGED', 'data_hash', v_current_hash);
  end if;

  -- 4. Verify expected hash matches current hash
  if p_expected_hash is not null and p_expected_hash <> '' then
    if v_current_hash is not null and v_current_hash <> p_expected_hash then
      raise exception 'CAS_CONFLICT: expected hash % but found % on %[%%]', p_expected_hash, v_current_hash, p_table, p_key
        using errcode = 'P0001';
    end if;
  end if;

  -- 5. Perform update under the held row lock
  execute format(
    'update public.%I set payload = $1, data_hash = $2, synced_at = now() where %I = $3',
    p_table, p_pk
  ) using (p_row->'payload'), p_new_hash, p_key;

  return jsonb_build_object('status', 'UPDATED', 'data_hash', p_new_hash);
end;
$$;
