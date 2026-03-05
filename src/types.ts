export interface DigestItem {
  title: string;
  body: string;
  tag: string;
  url: string;
}

export interface DigestSection {
  id: string;
  title: string;
  icon: string;
  color: string;
  items: DigestItem[];
}

export interface Digest {
  date: string;
  weekday: string;
  title: string;
  summary?: string;
  sections?: DigestSection[];
  /** v1 legacy */
  html?: string;
  version?: number;
  generated_at?: string;
}

export interface Manifest {
  dates: string[];
  updated: string;
}
