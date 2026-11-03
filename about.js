// Keep the About dialog usable independently of map/data loading.
(() => {
  const dialog = document.getElementById('brandDialog');
  const trigger = document.getElementById('about');
  const close = document.getElementById('closeAbout');
  if (!dialog || !trigger || !close) return;
  trigger.setAttribute('aria-controls', dialog.id);
  trigger.setAttribute('aria-haspopup', 'dialog');
  trigger.onclick = () => {
    if (!dialog.open) dialog.showModal();
    dialog.scrollTop = 0;
  };
  close.onclick = () => dialog.close();
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const box = dialog.getBoundingClientRect();
    if (event.clientX < box.left || event.clientX > box.right ||
        event.clientY < box.top || event.clientY > box.bottom) dialog.close();
  });
})();
