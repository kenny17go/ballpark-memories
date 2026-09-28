// CPBL data adapter. Keep UI independent from upstream changes.
export async function getGamesByDate(date){return {date,games:[],status:"adapter-pending"}}