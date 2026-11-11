// Counts a click on a partner button and tells the owner in Telegram.
// Stores nothing. Sends: provider, page, country, device type, where the visit came from. No IP address.
const NAMES = { nord: 'NordVPN', surf: 'Surfshark', proton: 'Proton VPN', cybr: 'CyberGhost', expr: 'ExpressVPN' };
const HOSTS = ['polskistreaming.pl', 'www.polskistreaming.pl'];

function clean(s, max) {
  return String(s || '').replace(/[^\w\-./:ąćęłńóśźżĄĆĘŁŃÓŚŹŻ ]/g, '').slice(0, max);
}

module.exports = async (req, res) => {
  res.setHeader('Cache-Control', 'no-store');
  if (req.method !== 'POST') return res.status(405).end();
  let origin = '';
  try { origin = new URL(req.headers.origin || req.headers.referer || '').hostname; } catch (e) {}
  const ua = String(req.headers['user-agent'] || '');
  if (!HOSTS.includes(origin) || /bot|crawl|spider|headless|preview|monitor/i.test(ua)) return res.status(204).end();
  let b = req.body;
  if (typeof b === 'string') { try { b = JSON.parse(b); } catch (e) { b = {}; } }
  b = b || {};
  const name = NAMES[b.p];
  if (!name) return res.status(204).end();
  const token = process.env.TELEGRAM_BOT_TOKEN, chat = process.env.TELEGRAM_CHAT_ID;
  if (token && chat) {
    const device = /mobile|android|iphone/i.test(ua) ? 'telefon' : /ipad|tablet/i.test(ua) ? 'tablet' : 'komputer';
    const text = [
      'Klik: ' + name,
      'Strona: ' + clean(b.u, 80),
      'Kraj: ' + clean(req.headers['x-vercel-ip-country'], 2) + ' · ' + device,
      'Wejście z: ' + (clean(b.r, 60) || 'bezpośrednio'),
    ].join('\n');
    try {
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), 4000);
      await fetch('https://api.telegram.org/bot' + token + '/sendMessage', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: ctl.signal,
        body: JSON.stringify({ chat_id: chat, text, disable_web_page_preview: true }),
      });
      clearTimeout(t);
    } catch (e) {}
  }
  return res.status(204).end();
};
