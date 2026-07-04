

// ---- Catálogo de productos (generado por JS para mantener el HTML limpio) ----
const productos = [
  {icon:'💾', nombre:'Memorias y micros', desc:'Distintas capacidades para tu teléfono o cámara.'},
  {icon:'🎧', nombre:'Audífonos y bocinas Bluetooth', desc:'Para llamadas, música y todo el día.'},
  {icon:'🔗', nombre:'OTG, PopSocket y cadenitas', desc:'Los detalles que le hacen falta a tu equipo.'},
  {icon:'🔌', nombre:'Cargadores, power bank y dock de carga', desc:'Cargadores de pared, power banks y estaciones de carga.'},
  {icon:'🌀', nombre:'Ventiladores recargables', desc:'Para los días de más calor.'},
  {icon:'🛡️', nombre:'Micas, covers, pantallas y baterías', desc:'Piezas y protección para tu equipo.'},
  {icon:'📱', nombre:'Teléfonos nuevos', desc:'Según disponibilidad. Pregunta por el modelo que buscas.'},
];

const grid = document.getElementById('catalogo-grid');
productos.forEach(p => {
  const msg = encodeURIComponent(`Hola, quiero información sobre: ${p.nombre}.`);
  const card = document.createElement('div');
  card.className = 'ticket';
  card.innerHTML = `
    <span class="ticket-icon">${p.icon}</span>
    <h3>${p.nombre}</h3>
    <p>${p.desc}</p>
    <a class="product-cta" href="https://wa.me/5356401889?text=${msg}" target="_blank" rel="noopener">Preguntar disponibilidad →</a>
  `;
  grid.appendChild(card);
});

// ---- Scroll reveal ----
const revealEls = document.querySelectorAll('.fade-up, .ticket');
const io = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if(e.isIntersecting){
      e.target.classList.add('in-view');
      io.unobserve(e.target);
    }
  });
}, {threshold:0.15});
revealEls.forEach(el => io.observe(el));

// ---- Ember particles on hero canvas ----
const canvas = document.getElementById('ember-canvas');
const ctx = canvas.getContext('2d');
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
let particles = [];

function resizeCanvas(){
  const hero = document.querySelector('.hero');
  canvas.width = hero.offsetWidth;
  canvas.height = hero.offsetHeight;
}
resizeCanvas();
window.addEventListener('resize', resizeCanvas);

function makeParticle(){
  return {
    x: Math.random() * canvas.width,
    y: canvas.height + 10,
    r: Math.random() * 2 + 1,
    speed: Math.random() * 0.6 + 0.3,
    drift: (Math.random() - 0.5) * 0.4,
    alpha: Math.random() * 0.5 + 0.3,
    color: Math.random() > 0.5 ? '255,90,31' : '255,178,56'
  };
}

if(!reduceMotion){
  for(let i=0;i<36;i++){
    const p = makeParticle();
    p.y = Math.random() * canvas.height;
    particles.push(p);
  }

  function animate(){
    ctx.clearRect(0,0,canvas.width,canvas.height);
    particles.forEach(p => {
      p.y -= p.speed;
      p.x += p.drift;
      if(p.y < -10){
        Object.assign(p, makeParticle());
      }
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI*2);
      ctx.fillStyle = `rgba(${p.color},${p.alpha})`;
      ctx.fill();
    });
    requestAnimationFrame(animate);
  }
  animate();
}
