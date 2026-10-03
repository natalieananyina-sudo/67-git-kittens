"use client";

import { useEffect, useState } from "react";
import { Activity, FileSpreadsheet, FlaskConical, LockKeyhole } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { Analysis } from "@/lib/types";
import { acceptedFields } from "@/lib/fields";

type Row = { row: number; result?: Analysis; error?: string };
const names: Record<string,string> = {
  hemoglobin:"Гемоглобин, г/л", ferritin:"Ферритин", serum_iron:"Сывороточное железо",
  TSAT:"Насыщение трансферрина", vitamin_B12:"Витамин B12", folate:"Фолаты",
  CRP:"С-реактивный белок", MCV:"MCV", RDW:"RDW", RBC:"Эритроциты",
  hematocrit:"Гематокрит", MCH:"MCH", MCHC:"MCHC", platelets:"Тромбоциты",
  WBC:"Лейкоциты", reticulocytes:"Ретикулоциты", transferrin:"Трансферрин",
  TIBC:"ОЖСС", UIBC:"ЛЖСС", sTfR:"Растворимый рецептор трансферрина",
  Ret_He:"Гемоглобин ретикулоцитов", active_B12:"Активный B12",
  MMA:"Метилмалоновая кислота", homocysteine:"Гомоцистеин", vitamin_B6:"Витамин B6",
  copper:"Медь", ceruloplasmin:"Церулоплазмин", ESR:"СОЭ", creatinine:"Креатинин",
  eGFR:"рСКФ", TSH:"ТТГ", albumin:"Альбумин", LDH:"ЛДГ",
  indirect_bilirubin:"Непрямой билирубин", haptoglobin:"Гаптоглобин"
};
const primary = ["hemoglobin","ferritin","serum_iron","TSAT","vitamin_B12","folate","CRP","MCV","RDW"];
const extra = acceptedFields.filter(f => f !== "sex" && f !== "age_years" && !primary.includes(f));

function parseCsv(text:string):string[][] {
  const rows:string[][]=[]; let row:string[]=[]; let cell=""; let quoted=false;
  const first=text.split(/\r?\n/,1)[0];
  const separator=(first.match(/;/g)||[]).length>(first.match(/,/g)||[]).length?";":",";
  for(let i=0;i<text.length;i++){
    const c=text[i];
    if(c==='"'){if(quoted && text[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}
    else if(c===separator && !quoted){row.push(cell);cell="";}
    else if((c==="\n"||c==="\r")&&!quoted){
      if(c==="\r"&&text[i+1]==="\n")i++;
      row.push(cell);if(row.some(Boolean))rows.push(row);row=[];cell="";
    } else cell+=c;
  }
  if(quoted)throw new Error("Незакрытые кавычки в CSV");
  row.push(cell);if(row.some(Boolean))rows.push(row);
  return rows;
}

function Report({data}:{data:Analysis}){
  const [audience,setAudience]=useState<"doctor"|"patient">("doctor");
  return <section className="report" aria-live="polite">
    <div className="report-heading"><span className="overline">Результат оценки</span><span className="pill">Учебный прототип</span></div>
    <div className="report-title"><span className={data.anemia?"result-icon alert":"result-icon"}><Activity/></span><div><small>Гемоглобин {data.hemoglobin} г/л · порог {data.threshold} г/л</small><h2>{data.anemia?"Есть признак анемии":"Анемия по гемоглобину не выявлена"}</h2></div></div>
    <div className="finding"><small>Предполагаемое состояние</small><strong>{data.className??(data.status==="discordant"?"Причина требует уточнения":"Для оценки причины недостаточно анализов")}</strong></div>
    <div className="audience"><button className={audience==="doctor"?"active":""} onClick={()=>setAudience("doctor")}>Для врача</button><button className={audience==="patient"?"active":""} onClick={()=>setAudience("patient")}>Для пациента</button></div>
    {audience==="doctor"?
      <div className="report-copy"><p>Оценка анемии основана на пороге гемоглобина из задания. {data.status==="predicted"?`Модель предполагает: ${data.className?.toLowerCase()}.`:"Причина не классифицирована."}</p><p>Передано профильных показателей: {data.measuredMarkers.length}. {data.note}</p></div>:
      <div className="report-copy"><p>{data.anemia?"Уровень гемоглобина ниже указанного в задании порога.":"По указанному гемоглобину признака анемии нет. Для оценки скрытого дефицита могут потребоваться другие анализы."}</p><p>{data.status==="predicted"?`Программа предполагает: ${data.className?.toLowerCase()}. Это предварительный результат, обсудите его с врачом.`:data.status==="discordant"?"Результаты разных проверок не согласуются. Обсудите анализы с врачом.":"Чтобы оценить возможную причину, добавьте другие анализы и обсудите их с врачом."}</p></div>}
    <p className="caution">Модель обучена на частично синтетической выборке из 840 записей. Сервис не назначает лечение и не подтверждает диагноз.</p>
  </section>;
}

export default function Home(){
  const [form,setForm]=useState<Record<string,string>>({sex:"F",age_years:"",hemoglobin:""});
  const [result,setResult]=useState<Analysis|null>(null);
  const [rows,setRows]=useState<Row[]|null>(null);
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);
  const [expanded,setExpanded]=useState(false);
  const [file,setFile]=useState<File|null>(null);
  async function submitOne(event:React.FormEvent){
    event.preventDefault();setError("");setResult(null);setBusy(true);
    try{
      const response=await fetch("/api/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(form),cache:"no-store"});
      const data=await response.json() as {result:Analysis;error:string};if(!response.ok)throw new Error(data.error);
      setResult(data.result);
    }catch(e){setError(e instanceof Error?e.message:"Ошибка обработки");}
    finally{setBusy(false);}
  }
  async function submitCsv(){
    if(!file)return;setError("");setRows(null);setBusy(true);
    try{
      if(file.size>750000)throw new Error("CSV должен быть меньше 750 КБ");
      const grid=parseCsv((await file.text()).replace(/^\uFEFF/,""));
      const headers=grid.shift()?.map(h=>h.trim())||[];
      if(new Set(headers).size!==headers.length)throw new Error("В CSV повторяются заголовки");
      if(!["sex","age_years","hemoglobin"].every(h=>headers.includes(h)))throw new Error("Нужны столбцы sex, age_years и hemoglobin");
      if(grid.length<1||grid.length>1000)throw new Error("В файле должно быть от 1 до 1000 строк");
      const allowed=new Set<string>(acceptedFields);
      const records=grid.map(cells=>Object.fromEntries(headers.map((h,i)=>[h,cells[i]?.trim()||""]).filter(([h])=>allowed.has(h))));
      const response=await fetch("/api/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({records}),cache:"no-store"});
      const data=await response.json() as {results:Row[];error:string};if(!response.ok)throw new Error(data.error);
      setRows(data.results);
    }catch(e){setError(e instanceof Error?e.message:"Ошибка файла");}
    finally{setBusy(false);}
  }
  useEffect(()=>{
    const context=(document as Document & {modelContext?:{registerTool?:(tool:unknown,options?:unknown)=>Promise<void>|void}}).modelContext;
    if(!context?.registerTool)return;
    const controller=new AbortController();
    void Promise.resolve(context.registerTool({
      name:"analyze_laboratory_values",title:"Оценить анализы",
      description:"Рассчитать предварительный результат по лабораторным значениям и показать его на странице.",
      inputSchema:{type:"object",properties:{sex:{type:"string",enum:["F","M"]},age_years:{type:"number"},hemoglobin:{type:"number"},ferritin:{type:"number"},vitamin_B12:{type:"number"},folate:{type:"number"},CRP:{type:"number"}},required:["sex","age_years","hemoglobin"],additionalProperties:false},
      annotations:{readOnlyHint:false,untrustedContentHint:false},
      async execute(input:Record<string,string|number>){
        const response=await fetch("/api/analyze",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(input)});
        const data=await response.json() as {result:Analysis;error:string};if(!response.ok)throw new Error(data.error);
        setForm(Object.fromEntries(Object.entries(input).map(([k,v])=>[k,String(v)])));
        setResult(data.result);setError("");
        return {anemia:data.result.anemia,className:data.result.className};
      }
    },{signal:controller.signal})).catch(()=>{});
    return ()=>controller.abort();
  },[]);
  const input=(key:string)=><label key={key}>{names[key]} {key==="hemoglobin"?"*":""}<Input className="control" type="number" inputMode="decimal" step="any" min="0" value={form[key]??""} onChange={e=>setForm({...form,[key]:e.target.value})} required={key==="hemoglobin"} placeholder="—"/></label>;
  return <main>
    <header className="topbar"><div className="brand"><span className="brand-icon"><FlaskConical size={23}/></span><div><strong>Лабораторный скрининг</strong><small>Дефицитные состояния · прототип</small></div></div><span className="privacy"><LockKeyhole size={15}/> Без хранения анализов</span></header>
    <div className="workspace"><div className="intro"><div className="overline">РАБОЧАЯ ОБЛАСТЬ</div><h1>Оценка показателей крови</h1><p>Введите данные взрослого пациента или загрузите таблицу. Сервис проверит гемоглобин и, если анализов достаточно, предположит возможное состояние.</p></div>
      <div className="main-grid"><section className="panel entry"><Tabs defaultValue="manual"><TabsList className="mode-tabs"><TabsTrigger value="manual">Один пациент</TabsTrigger><TabsTrigger value="csv"><FileSpreadsheet size={17}/> Загрузить CSV</TabsTrigger></TabsList>
        <TabsContent value="manual"><form onSubmit={submitOne}><div className="section-title"><h2>Данные пациента</h2><small>Поля со звёздочкой обязательны</small></div><div className="form-grid"><label>Пол *<Select value={form.sex} onValueChange={v=>setForm({...form,sex:v??"F"})}><SelectTrigger className="control"><SelectValue placeholder="Выберите пол"/></SelectTrigger><SelectContent><SelectItem value="F">Женский</SelectItem><SelectItem value="M">Мужской</SelectItem></SelectContent></Select></label><label>Возраст, лет *<Input className="control" type="number" min="18" max="120" value={form.age_years} onChange={e=>setForm({...form,age_years:e.target.value})} required/></label></div>
          <hr/><div className="section-title"><h2>Лабораторные показатели</h2><small>Дополнительные поля можно оставить пустыми</small></div><div className="form-grid">{primary.map(input)}</div>
          <button className="more" type="button" onClick={()=>setExpanded(!expanded)} aria-expanded={expanded}>{expanded?"Скрыть остальные показатели":"Добавить остальные показатели"}</button>{expanded&&<div className="form-grid extra">{extra.map(input)}</div>}
          <div className="actions"><Button className="action" disabled={busy} type="submit">{busy?"Считаем…":"Получить оценку"}</Button><small>Данные не записываются в базу</small></div></form></TabsContent>
        <TabsContent value="csv"><div className="section-title"><h2>Пакетная проверка</h2><small>До 1000 строк</small></div><p className="upload-help">CSV с заголовками как в исходной таблице. Обязательны <code>sex</code>, <code>age_years</code>, <code>hemoglobin</code>. Идентификаторы и готовые диагнозы отбрасываются в браузере перед отправкой.</p><label className="upload-area"><FileSpreadsheet size={32}/><strong>{file?.name||"Выберите CSV-файл"}</strong><span>Используйте синтетические данные или данные, согласованные для обработки</span><Input type="file" accept=".csv,text/csv" onChange={e=>{setFile(e.target.files?.[0]||null);setRows(null);}}/></label><div className="actions"><Button className="action" onClick={submitCsv} disabled={!file||busy}>{busy?"Обрабатываем…":"Обработать CSV"}</Button><small>Файл не сохраняется</small></div>{rows&&<div className="batch"><h3>Результаты · {rows.length} строк</h3><div className="table-wrap"><table><thead><tr><th>Строка</th><th>Анемия</th><th>Предположение / ошибка</th></tr></thead><tbody>{rows.map(r=><tr key={r.row}><td>{r.row}</td><td>{r.result?(r.result.anemia?"Есть признак":"Не выявлена"):"—"}</td><td>{r.error||r.result?.className||(r.result?.status==="discordant"?"Причина требует уточнения":"Недостаточно анализов")}</td></tr>)}</tbody></table></div></div>}</TabsContent></Tabs>{error&&<p className="error" role="alert">{error}</p>}</section>
        <aside className="side panel"><div className="side-main"><span className="side-icon"><Activity size={22}/></span><h2>Как читается результат</h2><p>Первый вывод — проверка порога гемоглобина. Второй — предварительное предположение модели по доступным анализам.</p><div className="steps"><div><b>01</b> Проверка входных значений</div><div><b>02</b> Расчёт признака анемии</div><div><b>03</b> Оценка возможной причины</div></div></div><div className="side-note"><strong>О единицах измерения</strong><p>Гемоглобин — в г/л. Единицы остальных столбцов не описаны в исходном наборе: перед использованием с реальными лабораториями их необходимо согласовать.</p></div></aside>
      </div>{result&&<Report data={result}/>}<footer>Учебный прототип на частично синтетических данных. Вывод не заменяет врача.</footer></div>
  </main>;
}
