export interface SourceProof {
  url: string | null
  observed_at: string
}

export interface OwnershipEvidence {
  valid_from: string | null
  valid_to: string | null
  source: SourceProof | null
}

export interface Account {
  id: string
  platform: string
  platform_id: string
  id_namespace: string
  handle: string | null
  name: string | null
  url: string
  ownership_evidence: OwnershipEvidence[]
}

export interface Affiliation {
  organization: string
  valid_from: string | null
  valid_to: string | null
  source: SourceProof | null
}

export interface LifecycleEvent {
  event_type: string
  event_date: string | null
  date_precision: string | null
  source: SourceProof | null
}

export interface Creator {
  id: string
  name: string
  format: string
  roles: string[]
  thai_relation: string
  review_status: string
  sources: SourceProof[]
  accounts: Account[]
  affiliations: Affiliation[]
  events: LifecycleEvent[]
  platforms: string[]
}

export interface RegistryInventory {
  personas: number
  verified_personas: number
  accounts: number
  accounts_by_platform: Record<string, number>
}

export interface RegistryPublished {
  personas: number
  accounts: number
  persona_account_pairs: number
  reviewed_link_records: number
  excluded_unsafe_url_pairs: number
  accounts_by_platform: Record<string, number>
}

export interface RegistryData {
  schema_version: number
  generated_at: string
  source_registry_sha256: string
  count_semantics: Record<string, string>
  inventory: RegistryInventory
  published: RegistryPublished
  creators: Creator[]
}
