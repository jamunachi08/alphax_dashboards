window.AXD = window.AXD || {};

AXD.fmt = function (n, digits=0){
  try{
    const num = Number(n || 0);
    return num.toLocaleString(undefined, {minimumFractionDigits: digits, maximumFractionDigits: digits});
  }catch(e){ return String(n ?? ""); }
};

AXD.today = function(){
  const d = new Date();
  const y=d.getFullYear(), m=String(d.getMonth()+1).padStart(2,'0'), day=String(d.getDate()).padStart(2,'0');
  return `${y}-${m}-${day}`;
};

AXD.daysAgo = function(days){
  const d = new Date();
  d.setDate(d.getDate()-days);
  const y=d.getFullYear(), m=String(d.getMonth()+1).padStart(2,'0'), day=String(d.getDate()).padStart(2,'0');
  return `${y}-${m}-${day}`;
};

AXD.svgSparkline = function(el, points){
  // points: [{x: label, y: number}]
  const w = el.clientWidth || 600;
  const h = el.clientHeight || 90;
  const pad = 6;
  const ys = points.map(p => Number(p.y || 0));
  const minY = Math.min(...ys, 0);
  const maxY = Math.max(...ys, 1);
  const scaleX = (i) => pad + (points.length<=1 ? 0 : (i*(w-2*pad)/(points.length-1)));
  const scaleY = (y) => (h-pad) - ((y-minY) * (h-2*pad) / (maxY-minY || 1));
  let d = "";
  points.forEach((p,i)=>{
    const x = scaleX(i);
    const y = scaleY(Number(p.y||0));
    d += (i===0?`M ${x} ${y}`:` L ${x} ${y}`);
  });
  const svg = `
    <svg width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg">
      <path d="${d}" fill="none" stroke="var(--ax-accent)" stroke-width="3" stroke-linecap="round"/>
      <path d="M ${pad} ${h-pad} L ${w-pad} ${h-pad}" stroke="rgba(18,33,43,0.12)" stroke-width="1"/>
    </svg>`;
  el.innerHTML = svg;
};

AXD.call = function(method, args){
  return new Promise((resolve, reject)=>{
    frappe.call({
      method: method,
      args: args || {},
      callback: function(r){ resolve(r.message); },
      error: function(err){ reject(err); }
    });
  });
};

AXD.ensureLogin = function(){
  if (!frappe.session || frappe.session.user === "Guest"){
    window.location.href = "/login";
    return false;
  }
  return true;
};
