// Counts a click on a partner button and tells the owner in Telegram.
// Stores nothing. Sends: provider, page, country, city, device type, where the visit came from, network type. No IP address.
const NAMES = { nord: 'NordVPN', surf: 'Surfshark', proton: 'Proton VPN', cybr: 'CyberGhost', expr: 'ExpressVPN', pia: 'PIA' };
const HOSTS = ['polskistreaming.pl', 'www.polskistreaming.pl'];
// Networks of hosting firms and VPN providers. A click from one of these is a robot or a person who already uses a VPN.
const DC = new Set([16509, 14618, 15169, 396982, 8075, 14061, 16276, 24940, 212238, 60068, 9009, 63949, 20473, 51167, 13335, 45102,
  132203, 31898, 12876, 60781, 136787, 62240, 206092, 49981, 174, 3223, 43350, 207137, 141039, 147049, 39351, 9002, 202425, 211252]);

function clean(s, max) {
  return String(s || '').replace(/[<>&]/g, '').slice(0, max);
}
function flag(cc) {
  return /^[A-Z]{2}$/.test(cc) ? String.fromCodePoint(...[...cc].map((c) => 127397 + c.charCodeAt(0))) : '';
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
    const cc = clean(req.headers['x-vercel-ip-country'], 2).toUpperCase();
    let country = cc;
    try { country = new Intl.DisplayNames(['en'], { type: 'region' }).of(cc) || cc; } catch (e) {}
    let city = '';
    try { city = clean(decodeURIComponent(req.headers['x-vercel-ip-city'] || ''), 40); } catch (e) {}
    const device = /ipad|tablet/i.test(ua) ? 'tablet' : /mobile|android|iphone/i.test(ua) ? 'phone' : 'computer';
    const asn = parseInt(req.headers['x-vercel-ip-as-number'], 10);
    const net = !asn ? '' : DC.has(asn) ? '\n⚠️ Network: data center or VPN (AS' + asn + ')' : '';
    const text =
      '💰 <b>Click: ' + name + '</b>\n' +
      '📄 ' + clean(b.u, 80) + '\n' +
      '🌍 ' + flag(cc) + ' ' + country + (city ? ', ' + city : '') + ' · ' + device + '\n' +
      '↩️ From: ' + (clean(b.r, 60) || 'direct') + net;
    try {
      const ctl = new AbortController();
      const t = setTimeout(() => ctl.abort(), 4000);
      await fetch('https://api.telegram.org/bot' + token + '/sendMessage', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, signal: ctl.signal,
        body: JSON.stringify({ chat_id: chat, text, parse_mode: 'HTML', disable_web_page_preview: true }),
      });
      clearTimeout(t);
    } catch (e) {}
  }
  return res.status(204).end();
};
