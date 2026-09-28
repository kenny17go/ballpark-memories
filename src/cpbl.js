const LOCAL="./data/schedule-2026.json";
export async function getGamesByDate(date){try{const r=await fetch(LOCAL,{cache:"no-store"});if(!r.ok)throw Error("schedule");const all=await r.json();const games=all.filter(g=>g.date===date).map(g=>({...g,source:"CPBL"}));return{date,games,status:"local"}}catch(e){return{date,games:[],status:"unavailable"}}}

const RESULTS="./data/results-2026.json";
let resultCache=null;
async function loadResults(){if(resultCache)return resultCache;try{const r=await fetch(RESULTS,{cache:"no-store"});if(!r.ok)throw Error("results");resultCache=await r.json();return resultCache}catch(e){return{}}}
export async function getGameResult(id){const all=await loadResults();return all[id]||null}
