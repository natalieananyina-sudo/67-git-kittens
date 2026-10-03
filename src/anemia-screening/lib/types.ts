export type Analysis = {
  anemia: boolean;
  threshold: number;
  hemoglobin: number;
  status: "predicted" | "insufficient_data" | "discordant";
  classCode: string | null;
  className: string | null;
  measuredMarkers: string[];
  note: string;
};
