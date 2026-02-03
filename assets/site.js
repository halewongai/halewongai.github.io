function setYear(){
  const y = document.getElementById('y');
  if(y) y.textContent = new Date().getFullYear();
}
function markActiveNav(){
  const here = location.pathname.replace(/\/index\.html$/, '/');
  document.querySelectorAll('.nav a').forEach(a => {
    const href = a.getAttribute('href');
    if(!href) return;
    const norm = href.replace(/\/index\.html$/, '/');
    if(norm === here) a.classList.add('active');
  });
}
setYear();
markActiveNav();
