export const numericFields = [
  "age_years","hemoglobin","RBC","hematocrit","MCV","MCH","MCHC","RDW",
  "platelets","WBC","reticulocytes","ferritin","serum_iron","transferrin",
  "TIBC","UIBC","TSAT","sTfR","Ret_He","vitamin_B12","active_B12","MMA",
  "homocysteine","folate","vitamin_B6","copper","ceruloplasmin","CRP",
  "ESR","creatinine","eGFR","TSH","albumin","LDH","indirect_bilirubin","haptoglobin"
] as const;
export const acceptedFields = ["sex", ...numericFields];
