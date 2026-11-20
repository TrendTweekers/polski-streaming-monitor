(function(){
  var LOGO={proton:'https://cdn.simpleicons.org/protonvpn',nord:'https://cdn.simpleicons.org/nordvpn',surf:'https://cdn.simpleicons.org/surfshark',expr:'https://cdn.simpleicons.org/expressvpn',cybr:'logos/cyberghost-icon.png'};
  var SLOGO={tvpvod:'logos/tvpvod.png',player:'logos/player.svg',polsat:'logos/polsat.svg',canal:'logos/canal.svg'};
  var PRICE={proton:['0 zł','plan darmowy']};
  var C={
    uk:{label:'Wielka Brytania',short:'UK',where:'w UK',flag:'gb'},
    de:{label:'Niemcy',short:'Niemcy',where:'w Niemczech',flag:'de'},
    nl:{label:'Holandia',short:'Holandia',where:'w Holandii',flag:'nl'},
    us:{label:'USA',short:'USA',where:'w USA',flag:'us'}
  };
  var LABEL={okr:'Działa<small class="stn">po odświeżeniu</small>',ok:'Działa',blocked:'Nie działa',unstable:'Niestabilny',none:'Nie przetestowano'};
  var DESC={ok:'Film grał 60 sekund bez przerwy w pierwszej próbie.',unstable:'Film zatrzymał się albo ruszył dopiero w drugiej próbie.',blocked:'Film nie ruszył w dwóch próbach. Powód może być po stronie VPN albo serwisu.',none:'Test się nie odbył. Nie liczymy tego jako blokady.'};
  var ICON={
    ok:'<path d="M20 6 9 17l-5-5"/>',
    okr:'<path d="M20 6 9 17l-5-5"/>',
    blocked:'<path d="M18 6 6 18M6 6l12 12"/>',
    unstable:'<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
    none:'<path d="M5 12h14"/>'
  };
  function st(s){return '<span class="st '+(s==='okr'?'ok':s)+'"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+ICON[s]+'</svg>'+LABEL[s]+'</span>'}
  function esc(x){return String(x==null?'':x).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function slogo(x){return SLOGO[x.id]?'<span class="slogo"><img src="'+SLOGO[x.id]+'" alt="'+esc(x.name)+'"></span>':'<span class="slogo stext">'+esc(x.name)+'</span>'}
  function logo(id){return '<img src="'+LOGO[id]+'" alt="" width="30" height="30">'}
  function fmtDT(iso){if(!iso)return '—';return iso.slice(8,10)+'.'+iso.slice(5,7)+'.'+iso.slice(0,4)+', '+iso.slice(11,16)}
  function fmtT(iso){return iso?iso.slice(11,19):'—'}
  function addDays(d,n){var x=new Date(d+'T12:00:00Z');x.setUTCDate(x.getUTCDate()+n);return x.toISOString().slice(0,10)}
  function dm(d){return d.slice(8,10)+'.'+d.slice(5,7)}
  var $=function(id){return document.getElementById(id)};
  var all=function(sel,fn){Array.prototype.forEach.call(document.querySelectorAll(sel),fn)};
  var cur='uk',sortBy='works',hp=null,hs=null,open=null,es=null,RUN=null,HIST={days:{}},SV=[],SVON=[];

  function stat(p,sid){var r=p.services&&p.services[sid];if(!r)return 'none';if(r.status==='ok'&&r.reloaded)return 'okr';if(r.status==='unstable'&&p.plan==='plan płatny'&&/^Pierwsza próba/.test(r.reason||''))return 'okr';return r.status}
  function works(p){return SVON.filter(function(s){var x=stat(p,s.id);return x==='ok'||x==='okr'}).length}
  function sorted(){
    var d=RUN.providers.slice();
    d.sort(function(a,b){
      if(a.tested!==b.tested)return a.tested?-1:1;
      if(sortBy==='speed')return (b.speed_mbps||0)-(a.speed_mbps||0);
      if(sortBy==='price')return (PRICE[a.id]?0:1)-(PRICE[b.id]?0:1);
      return works(b)-works(a)||(b.speed_mbps||0)-(a.speed_mbps||0);
    });
    return d;
  }
  function best(){return sorted()[0]}

  function renderTable(){
    var c=C[cur],data=sorted(),tested=RUN.providers.filter(function(p){return p.tested});
    $('hero').hidden=cur!=='uk';$('credit').hidden=cur!=='uk';$('open').classList.toggle('solo',cur!=='uk');
    $('crumb').textContent=c.label;$('where').textContent=c.where;$('tcountry').textContent=c.label;
    $('last').textContent=fmtDT(RUN.finished_at);$('next').textContent=dm(addDays(RUN.date,1))+'.'+addDays(RUN.date,1).slice(0,4)+', rano';
    $('s1').textContent=tested.filter(function(p){return stat(p,'tvpvod')==='ok'}).length+'/'+tested.length;
    var tried=0;tested.forEach(function(p){SVON.forEach(function(s){if(stat(p,s.id)!=='none')tried++})});
    $('s2').textContent=tried;$('s3').textContent=Object.keys(HIST.days).length;
    $('scope').textContent='Testujemy na razie '+tested.length+' z '+RUN.providers.length+' dostawców i '+SVON.length+' darmowe serwisy. Płatnych serwisów (Polsat Box Go, Canal+ Online) jeszcze nie testujemy.';
    var CN={PL:'Polska',US:'USA',GB:'Wielka Brytania',DE:'Niemcy',NL:'Holandia',IE:'Irlandia'};var where=RUN.runner&&RUN.runner.country?(CN[RUN.runner.country]||RUN.runner.country):'—';
    var h='',m='';
    data.forEach(function(p){
      var w=works(p),sub=p.tested?(w+' z '+SVON.length+' testowanych serwisów działa'):'jeszcze nie testujemy';
      var pr=PRICE[p.id];
      h+='<tr class="row"><td><button class="prov" type="button" data-open="'+p.id+'" aria-expanded="'+(open===p.id)+'">'+logo(p.id)+'<span>'+esc(p.name)+'<small>'+sub+'</small></span></button></td>';
      SVON.forEach(function(s){h+='<td>'+st(stat(p,s.id))+'</td>'});
      h+='<td class="mono">'+(p.speed_mbps?p.speed_mbps+' Mb/s<span class="sub">pomiar z: '+esc(where)+'</span>':'<span class="muted">—</span>')+'</td>';
      h+='<td class="mono">'+(pr?pr[0]+'<span class="sub">'+pr[1]+'</span>':'<span class="muted">—</span>')+'</td>';
      h+='<td><button class="btn" type="button" data-cta aria-label="Sprawdź ofertę '+esc(p.name)+'">Sprawdź ofertę</button></td></tr>';
      var det='';
      if(p.tested){
        det='<div><span>Serwer VPN</span><b class="mono">'+esc(p.server||'—')+'</b></div>'+
            '<div><span>Adres IP serwera</span><b class="mono">'+esc(p.exit&&p.exit.ip||'—')+'</b></div>'+
            '<div><span>Lokalizacja IP</span><b>'+esc(p.exit?p.exit.city+', '+p.exit.country:'—')+'</b></div>'+
            '<div><span>Sieć</span><b>'+esc(p.exit&&p.exit.org||'—')+'</b></div>';
        SVON.forEach(function(s){var r=p.services[s.id];if(!r)return;det+='<div><span>'+esc(s.name)+'</span><b class="mono">'+(r.played_seconds!=null?Math.round(r.played_seconds)+' s filmu, '+esc(r.resolution||''):'')+(r.reason?' '+esc(r.reason):'')+'</b></div>'});
      }else det='<div><span>Status</span><b>'+esc(p.note||'Nie mamy jeszcze konta testowego u tego dostawcy.')+'</b></div>';
      h+='<tr class="detail"'+(open===p.id?'':' hidden')+'><td colspan="'+(SVON.length+4)+'"><div class="dgrid">'+det+'</div></td></tr>';
      var sum=!p.tested?'none':w===SVON.length?'ok':w===0?'blocked':'unstable';
      m+='<details><summary>'+logo(p.id)+'<b>'+esc(p.name)+'<small>'+sub+'</small></b><span class="st '+sum+'">'+(sum==='unstable'?'Częściowo':LABEL[sum])+'</span></summary><div class="rows">';
      SVON.forEach(function(s){m+='<div>'+slogo(s)+st(stat(p,s.id))+'</div>'});
      m+='<div><span>Pobieranie</span><span class="mono">'+(p.speed_mbps?p.speed_mbps+' Mb/s':'—')+'</span></div><div><span>Cena za miesiąc</span><span class="mono">'+(pr?pr[0]:'—')+'</span></div></div>'+
         '<button class="btn" type="button" data-cta>Sprawdź ofertę '+esc(p.name)+'</button></details>';
    });
    $('rows').innerHTML=h;$('mlist').innerHTML=m;
    all('[data-c]',function(b){b.setAttribute('aria-pressed',b.dataset.c===cur)});
    all('[data-sort]',function(b){b.setAttribute('aria-pressed',b.dataset.sort===sortBy)});
    renderEvidence();
  }

  function renderEvidence(){
    var top=best(),r=top.services&&top.services[es],s=SVON.filter(function(x){return x.id===es})[0]||{},t='';
    SVON.forEach(function(x){var rr=top.services[x.id]||{};t+='<button type="button" data-es="'+x.id+'" aria-pressed="'+(x.id===es)+'">'+(rr.shot?'<img class="t" src="'+esc(rr.shot)+'" alt="" loading="lazy">':'<div class="t"></div>')+slogo(x)+st(rr.status||'none')+'</button>'});
    $('thumbs').innerHTML=t;
    $('shot').innerHTML=r&&r.shot?'<a href="'+esc(r.shot)+'" target="_blank" rel="noopener"><img src="'+esc(r.shot)+'" alt="Zrzut ekranu z testu: '+esc(s.name)+' przez '+esc(top.name)+'" width="1440" height="900"></a>':'<div class="slot"><span><b>Brak zrzutu ekranu</b>Dla tego testu nie ma jeszcze zrzutu.</span></div>';
    $('e0').textContent=s.name||'—';$('e1').textContent=top.name+(top.plan?' ('+top.plan+')':'');
    $('e2').textContent=top.exit?top.exit.city+', Polska ('+(top.exit.ip||'')+')':'—';$('e2b').textContent=top.server||'—';
    $('e4').textContent=r?fmtDT(r.tested_at).slice(0,10):'—';$('e5').textContent=r?fmtT(r.tested_at):'—';
    $('e3').innerHTML=st(r?r.status:'none');
    $('e6').textContent=r?((r.played_seconds!=null?Math.round(r.played_seconds)+' s filmu, '+(r.resolution||'')+(r.drm?', z DRM':'')+'. ':'')+(r.reason||'')).trim()||'—':'—';
  }

  function renderHistory(){
    var days=[];for(var i=29;i>=0;i--)days.push(addDays(RUN.date,-i));
    function ds(pid,d){var x=HIST.days[d]&&HIST.days[d][pid];var v=x&&x[hs]?x[hs]:'none';return v==='okr'?'ok':v}
    var mine=days.map(function(d){return ds(hp,d)}),n=mine.filter(function(s){return s!=='none'}).length,ok=mine.filter(function(s){return s==='ok'}).length,bl=mine.filter(function(s){return s==='blocked'}).length;
    $('h1').textContent=n?ok+'/'+n:'—';$('h2').textContent=n?bl:'—';$('h3').textContent=n;
    if(n<7){
      $('chart').innerHTML='<div class="empty"><b>Za mało danych na wykres</b>Mamy '+n+' '+(n===1?'dzień':'dni')+' testów dla tego VPN. Wykres pojawi się po 7 dniach. Każdy dzień widać w tabeli poniżej.</div>';
    }else{
      var W=1100,H=280,L=48,R=12,T=14,B=30,pw=W-L-R,ph=H-T-B,g='',path='';
      var x=function(i){return L+pw*(i+.5)/30},y=function(v){return T+ph*(1-v)};
      [0,.25,.5,.75,1].forEach(function(v){g+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+y(v)+'" y2="'+y(v)+'" stroke="var(--line)" stroke-width="1"/><text x="'+(L-10)+'" y="'+(y(v)+4)+'" text-anchor="end" font-size="12" fill="var(--muted)" font-family="IBM Plex Mono,monospace">'+(v*100)+'%</text>'});
      [0,7,14,21,29].forEach(function(i){g+='<text x="'+x(i)+'" y="'+(H-8)+'" text-anchor="middle" font-size="12" fill="var(--muted)" font-family="IBM Plex Mono,monospace">'+dm(days[i])+'</text>'});
      mine.forEach(function(s,i){
        var a=0,c=0;for(var j=Math.max(0,i-6);j<=i;j++){if(mine[j]!=='none'){c++;a+=mine[j]==='ok'?1:mine[j]==='unstable'?.5:0}}
        if(c)path+=(path?'L':'M')+x(i).toFixed(1)+' '+y(a/c).toFixed(1)+' ';
        if(s==='blocked'||s==='unstable')g+='<rect x="'+(x(i)-pw/60+2)+'" y="'+T+'" width="'+(pw/30-4)+'" height="'+ph+'" fill="'+(s==='blocked'?'var(--bad)':'var(--warn)')+'" opacity=".12"/>';
      });
      g+='<path d="'+path+'" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linejoin="round"/>';
      $('chart').innerHTML='<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="Średnia skuteczność z 7 dni">'+g+'</svg>';
    }
    var mx='';
    RUN.providers.forEach(function(p){
      var o=0,t=0,cells='';
      days.forEach(function(d){var s=ds(p.id,d);cells+='<i class="'+(s==='ok'?'':s)+'" title="'+dm(d)+': '+LABEL[s]+'"></i>';if(s!=='none'){t++;if(s==='ok')o++}});
      mx+='<div class="mrow'+(p.id===hp?' on':'')+'"><button type="button" data-hp="'+p.id+'">'+esc(p.name)+'</button><div class="cells" role="img" aria-label="'+esc(p.name)+': '+o+' z '+t+' dni testów">'+cells+'</div><div class="pct">'+(t?Math.round(o/t*100)+'%':'—')+'</div></div>';
    });
    $('matrix').innerHTML=mx;$('ax0').textContent=dm(days[0]);$('ax1').textContent=dm(days[15]);$('ax2').textContent=dm(days[29]);
    all('#hprov [data-hp]',function(b){b.setAttribute('aria-pressed',b.dataset.hp===hp)});
    all('[data-hs]',function(b){b.setAttribute('aria-pressed',b.dataset.hs===hs)});
  }
  function render(){renderTable();renderHistory()}

  function boot(){
    SV=RUN.services;SVON=SV.filter(function(s){return s.enabled});
    hs=es=SVON[0].id;hp=(RUN.providers.filter(function(p){return p.tested})[0]||RUN.providers[0]).id;
    var cn='',cs='';
    Object.keys(C).forEach(function(k){
      cn+='<button type="button" data-c="'+k+'">'+C[k].short+'</button>';
      cs+='<button type="button" data-c="'+k+'"><img src="https://flagcdn.com/'+C[k].flag+'.svg" alt="" width="66" height="44"><span><b>'+C[k].label+'</b><span>ten sam wynik testu</span></span></button>';
    });
    $('thead').innerHTML='<th>Dostawca VPN</th>'+SVON.map(function(x){return '<th>'+esc(x.name)+'</th>'}).join('')+'<th>Pobieranie</th><th>Cena za miesiąc</th><th>Oferta partnera</th>';
    $('cnav').innerHTML=cn;$('countries').innerHTML=cs;
    $('hprov').innerHTML=RUN.providers.map(function(p){return '<button type="button" data-hp="'+p.id+'">'+esc(p.name)+'</button>'}).join('');
    $('hserv').innerHTML=SVON.map(function(s){return '<button type="button" data-hs="'+s.id+'">'+esc(s.name)+'</button>'}).join('');
    $('legend').innerHTML=['ok','unstable','blocked','none'].map(st).join('');
    $('cats').innerHTML=['ok','unstable','blocked','none'].map(function(s){return '<li>'+st(s)+'<span>'+DESC[s]+'</span></li>'}).join('');
    render();
  }

  var tt;
  document.addEventListener('click',function(e){
    var t=e.target.closest('button');if(!t||!RUN)return;
    if(t.dataset.c){cur=t.dataset.c;render()}
    else if(t.dataset.sort){sortBy=t.dataset.sort;renderTable()}
    else if(t.dataset.open){open=open===t.dataset.open?null:t.dataset.open;renderTable()}
    else if(t.dataset.hp){hp=t.dataset.hp;renderHistory()}
    else if(t.dataset.hs){hs=t.dataset.hs;renderHistory()}
    else if(t.dataset.es){es=t.dataset.es;renderEvidence()}
    else if(t.hasAttribute('data-cta')){var x=$('toast');x.textContent='Linki partnerskie nie są jeszcze aktywne. To wersja testowa strony.';x.hidden=false;clearTimeout(tt);tt=setTimeout(function(){x.hidden=true},3200)}
  });
  function get(u){return fetch(u,{cache:'no-store'}).then(function(r){if(!r.ok)throw new Error(u);return r.json()})}
  Promise.all([get('data/latest.json'),get('data/history.json').catch(function(){return {days:{}}})]).then(function(a){RUN=a[0];HIST=a[1];boot()}).catch(function(){
    $('rows').innerHTML='<tr><td colspan="8" style="height:120px;text-align:center" class="muted">Brak danych z testu. Bot nie opublikował jeszcze wyników.</td></tr>';
  });
})();
