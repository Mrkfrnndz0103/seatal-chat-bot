-- Supabase schema for backlogs_update
-- Create table for filtered backlog rows

create table if not exists backlogs_rows (
  id bigserial primary key,
  source_file_id text not null,
  to_number text,
  spx_tracking_number text,
  receiver_name text,
  to_order_quantity text,
  operator text,
  create_time text,
  complete_time text,
  remark text,
  receive_status text,
  staging_area_id text,
  imported_at timestamptz default now()
);

create index if not exists idx_backlogs_rows_source_file_id
  on backlogs_rows (source_file_id);
