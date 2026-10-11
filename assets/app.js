'use strict';

const dialog = document.querySelector('#contents-dialog');
const menuButton = document.querySelector('[data-open-menu]');
const closeButton = document.querySelector('[data-close-menu]');
const toast = document.querySelector('#toast');
let toastTimer;

function announce(message) {
  if (!toast) return;
  clearTimeout(toastTimer);
  toast.textContent = message;
  toast.hidden = false;
  toastTimer = setTimeout(() => { toast.hidden = true; }, 3200);
}

if (dialog && menuButton) {
  menuButton.addEventListener('click', () => {
    dialog.showModal();
    menuButton.setAttribute('aria-expanded', 'true');
    const search = dialog.querySelector('input');
    if (search) search.focus();
  });
  if (closeButton) closeButton.addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => {
    menuButton.setAttribute('aria-expanded', 'false');
    menuButton.focus();
  });
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
  });
}

document.querySelectorAll('[data-filter]').forEach(input => {
  const target = document.getElementById(input.dataset.filter);
  if (!target) return;
  input.addEventListener('input', () => {
    const query = input.value.trim().toLocaleLowerCase();
    let visible = 0;
    target.querySelectorAll('[data-search-item]').forEach(item => {
      const text = (item.dataset.search || item.textContent || '').toLocaleLowerCase();
      item.hidden = !text.includes(query);
      if (!item.hidden) visible += 1;
    });
    const empty = document.querySelector(`[data-empty-for="${target.id}"]`);
    if (empty) empty.hidden = visible !== 0;
  });
});

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    try { await navigator.clipboard.writeText(text); return true; } catch (_) { /* Use legacy fallback. */ }
  }
  const field = document.createElement('textarea');
  field.value = text;
  field.setAttribute('readonly', '');
  field.style.position = 'fixed';
  field.style.top = '-9999px';
  document.body.appendChild(field);
  field.select();
  const ok = document.execCommand('copy');
  field.remove();
  return ok;
}

document.querySelectorAll('[data-copy]').forEach(button => {
  button.addEventListener('click', async () => {
    const code = document.getElementById(button.dataset.copy);
    if (!code) return;
    const text = code.textContent || '';
    try {
      const copied = await copyText(text);
      if (!copied) throw new Error('Copy unavailable');
      const original = button.textContent;
      button.textContent = 'Copied';
      button.classList.add('copied');
      button.setAttribute('aria-label', 'Prompt copied to clipboard');
      announce('Prompt copied. Paste it into Notebook chat.');
      setTimeout(() => {
        button.textContent = original;
        button.classList.remove('copied');
        button.setAttribute('aria-label', button.dataset.copyLabel || 'Copy prompt');
      }, 2500);
    } catch (_) {
      announce('Select the prompt text and copy it manually.');
      const selection = window.getSelection();
      if (selection) {
        const range = document.createRange();
        range.selectNodeContents(code);
        selection.removeAllRanges();
        selection.addRange(range);
      }
    }
    button.focus();
  });
});

document.querySelectorAll('[data-print]').forEach(button => {
  button.addEventListener('click', () => window.print());
});

document.addEventListener('keydown', event => {
  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || (dialog && dialog.open)) return;
  const target = event.target;
  if (target instanceof Element && target.closest('input, textarea, select, button, a, summary, [contenteditable]')) return;
  const direction = event.key === 'ArrowRight' ? 'next' : event.key === 'ArrowLeft' ? 'previous' : null;
  if (!direction) return;
  const link = document.querySelector(`a[data-page-${direction}]`);
  if (link) { event.preventDefault(); window.location.assign(link.href); }
});
