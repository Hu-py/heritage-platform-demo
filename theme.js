// Apply saved appearance before styles load, without touching the map's data layers.
function updateThemeButton(){
 const button=document.getElementById('theme');if(!button)return;
 const dark=document.documentElement.dataset.theme==='dark';
 const en=typeof language!=='undefined'&&language==='en';
 button.textContent=dark?(en?'☀ Light':'☀ 浅色'):(en?'☾ Dark':'☾ 深色');
 button.setAttribute('aria-pressed',String(dark));
 button.setAttribute('aria-label',en?'Toggle dark theme':'切换深色主题');
}
try{document.documentElement.dataset.theme=localStorage.getItem('heritage-theme')||'dark'}catch{document.documentElement.dataset.theme='dark'}
document.addEventListener('DOMContentLoaded',()=>{
 updateThemeButton();document.getElementById('theme').onclick=()=>{
 const next=document.documentElement.dataset.theme==='dark'?'light':'dark';
 document.documentElement.dataset.theme=next;
 try{localStorage.setItem('heritage-theme',next)}catch{}
 updateThemeButton();
 };
});
