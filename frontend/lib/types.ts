export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'admin' | 'supervisor' | 'agent' | 'viewer';
  is_active: boolean;
  organization_id: string | null;
  is_global_admin: boolean;
  timezone: string;
  avatar_url: string | null;
  phone: string | null;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  is_active: boolean;
}

export interface Lead {
  id: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  email: string | null;
  country: string | null;
  status: 'new' | 'contacted' | 'qualified' | 'converted' | 'discarded';
  source: 'csv_import' | 'manual' | 'api' | 'voicehire';
  assigned_to: string | null;
  campaign_id: string | null;
  organization_id: string;
  created_at: string;
  updated_at: string;
}

export interface Contact {
  id: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  email: string | null;
  company: string | null;
  position: string | null;
  country: string | null;
  status: 'active' | 'inactive' | 'do_not_contact';
  assigned_to: string | null;
  tags: string[];
  custom_fields: Record<string, unknown>;
  organization_id: string;
  created_at: string;
  updated_at: string;
}

export interface Deal {
  id: string;
  name: string;
  value: number | null;
  currency: string;
  contact_id: string;
  stage_id: string;
  pipeline_id: string;
  assigned_to: string | null;
  expected_close_date: string | null;
  closed_at: string | null;
  notes: string | null;
  organization_id: string;
  created_at: string;
  updated_at: string;
}

export interface Notification {
  id: string;
  type: string;
  priority: 'normal' | 'high';
  title: string;
  body: string;
  entity_type: string | null;
  entity_id: string | null;
  read_at: string | null;
  created_at: string;
}

export interface ApiError {
  detail: string;
}
