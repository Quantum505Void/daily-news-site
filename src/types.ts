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
  sections: DigestSection[];
  generated_at?: string;
  version: 2;
}

export interface Manifest {
  dates: string[];
  updated: string;
}
