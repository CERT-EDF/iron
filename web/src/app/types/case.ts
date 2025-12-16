export interface CaseMetadata {
  guid: string;
  created?: string;
  updated?: string;
  closed?: string;
  tsid?: string;
  name: string;
  description?: string;
  acs: string[];
  webhooks: string[];

  unseenNew?: boolean; //Injected value in API getCases
}
export interface FusionEvent {
  source: string;
  category: string;
  case: CaseMetadata;
  ext: any;
}
