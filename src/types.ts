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

export interface HotWord {
  word: string;
  count: number;
}

export interface Digest {
  date: string;
  weekday: string;
  title: string;
  summary?: string;
  sections: DigestSection[];
  hot_words?: HotWord[];
  generated_at?: string;
  version: 2;
}

export interface Manifest {
  dates: string[];
  updated: string;
}
