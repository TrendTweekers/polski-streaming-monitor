// Daily timer (Vercel Cron). GitHub starts its own timed jobs hours late, so this starts them on time.
// Starts the daily test only when today's result is not published yet. Also starts the CJ sales check.
// Needs GITHUB_DISPATCH_TOKEN (fine-grained token, this repo only, Actions: read and write).
const REPO = 'TrendTweekers/polski-streaming-monitor';

async function dispatch(file, token) {
  const r = await fetch(`https://api.github.com/repos/${REPO}/actions/workflows/${file}/dispatches`, {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json', 'User-Agent': 'polskistreaming-timer' },
    body: JSON.stringify({ ref: 'main' }),
  });
  return r.status; // 204 = started
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  const secret = process.env.CRON_SECRET;
  if (secret && req.headers.authorization !== 'Bearer ' + secret) return res.status(401).json({ error: 'not allowed' });
  const token = process.env.GITHUB_DISPATCH_TOKEN;
  if (!token) return res.status(500).json({ error: 'no GITHUB_DISPATCH_TOKEN' });
  const today = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Warsaw' }).format(new Date());
  let last = '';
  try { last = (await (await fetch('https://polskistreaming.pl/data/latest.json', { cache: 'no-store' })).json()).date; } catch (e) {}
  const out = { today, last };
  out.daily = last === today ? 'already done' : await dispatch('daily.yml', token);
  return res.status(200).json(out);
};
