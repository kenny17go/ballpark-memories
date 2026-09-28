const LOCAL="./data/schedule-2026.json";
export async function getGamesByDate(date){try{const r=await fetch(LOCAL,{cache:"no-store"});if(!r.ok)throw Error("schedule");const all=await r.json();const games=all.filter(g=>g.date===date).map(g=>({...g,source:"CPBL"}));return{date,games,status:"local"}}catch(e){return{date,games:[],status:"unavailable"}}}
