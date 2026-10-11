'use strict';
(() => {
  const canvas = $('artworkCanvas'), ctx = canvas.getContext('2d');
  let template = 'plain', picture = null, pan = [0, 0], dragging = null, imageGeneration = 0, exporting = false;
  function showWorkspace(artwork) {
    $('locationWorkspace').hidden = artwork; $('artworkWorkspace').hidden = !artwork;
    $('locationTab').setAttribute('aria-pressed', String(!artwork));
    $('artworkTab').setAttribute('aria-pressed', String(artwork));
    if (!artwork) requestAnimationFrame(() => map.invalidateSize());
  }
  $('locationTab').onclick = () => showWorkspace(false);
  $('artworkTab').onclick = () => showWorkspace(true);
  document.querySelector('.brand').onclick = event => { event.preventDefault(); showWorkspace(false); };
  function imageBounds() {
    const scale = Math.max(canvas.width / picture.width, canvas.height / picture.height) * Number($('artworkZoom').value);
    return [picture.width * scale, picture.height * scale];
  }
  function draw() {
    const w = canvas.width, h = canvas.height, fg = $('artworkForeground').value;
    ctx.clearRect(0, 0, w, h); ctx.fillStyle = $('artworkBackground').value; ctx.fillRect(0, 0, w, h);
    if (picture) {
      const [iw, ih] = imageBounds();
      pan[0] = Math.max(-(iw - w) / 2, Math.min((iw - w) / 2, pan[0]));
      pan[1] = Math.max(-(ih - h) / 2, Math.min((ih - h) / 2, pan[1]));
      ctx.save(); ctx.globalAlpha = Number($('artworkOpacity').value);
      ctx.drawImage(picture, (w - iw) / 2 + pan[0], (h - ih) / 2 + pan[1], iw, ih); ctx.restore();
    }
    ctx.save(); ctx.strokeStyle = fg; ctx.lineWidth = 2; ctx.globalAlpha = .16;
    if (template === 'lines') {
      for (let i = -5; i < 15; i++) { ctx.beginPath(); ctx.moveTo(i * 140, h); ctx.lineTo(i * 140 + 650, 0); ctx.stroke(); }
    } else if (template === 'orbit') {
      for (let r = 100; r < 1050; r += 100) { ctx.beginPath(); ctx.arc(w * .78, h * .56, r, 0, 2 * Math.PI); ctx.stroke(); }
    }
    ctx.restore(); ctx.fillStyle = fg;
    ctx.font = '500 30px Inter, sans-serif'; ctx.fillText('LS / DESIGN STUDIO', 96, 110);
    ctx.font = '500 85px Inter, sans-serif';
    const title = $('artworkTitle').value.trim();
    // Keep even long Unicode titles inside the artwork.
    let fontSize = 85;
    while (ctx.measureText(title).width > w - 192 && fontSize > 24) { fontSize--; ctx.font = `500 ${fontSize}px Inter, sans-serif`; }
    ctx.fillText(title, 96, h - 245);
    ctx.font = '400 27px Inter, sans-serif'; ctx.fillText($('artworkCaption').value.trim(), 100, h - 171, w - 200);
    ctx.save(); ctx.globalAlpha = .3; ctx.strokeStyle = fg; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(96, h - 112); ctx.lineTo(w - 96, h - 112); ctx.stroke(); ctx.restore();
    ctx.font = '400 22px Inter, sans-serif'; ctx.fillText('LARP STUDIO', 96, h - 64);
    ctx.textAlign = 'right'; ctx.fillText(template.toUpperCase() + ' / 01', w - 96, h - 64); ctx.textAlign = 'left';
    canvas.classList.toggle('has-picture', Boolean(picture));
    $('artworkPanHint').textContent = picture ? 'Drag the image on the card to adjust the crop.' : template.toUpperCase() + ' / 01';
  }
  document.querySelectorAll('[data-template]').forEach(button => button.onclick = () => {
    template = button.dataset.template;
    document.querySelectorAll('[data-template]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
    draw();
  });
  ['artworkTitle', 'artworkCaption', 'artworkBackground', 'artworkForeground', 'artworkZoom', 'artworkOpacity'].forEach(id => $(id).addEventListener('input', draw));
  $('artworkImage').onchange = async event => {
    const file = event.target.files[0], generation = ++imageGeneration;
    if (!file) return;
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size > 15 * 1024 * 1024) {
      toast('Choose a PNG, JPEG or WebP image up to 15 MB.', true); event.target.value = ''; return;
    }
    const url = URL.createObjectURL(file);
    try {
      const loaded = new Image(); loaded.src = url; await loaded.decode();
      if (generation !== imageGeneration) return;
      if (loaded.width * loaded.height > 40000000 || !loaded.width || !loaded.height) throw new Error('Choose an image with no more than 40 megapixels.');
      picture = loaded; pan = [0, 0]; $('artworkZoom').value = '1';
      $('artworkImageControls').hidden = false; $('artworkImageNote').textContent = file.name;
      draw();
    } catch (error) { if (generation === imageGeneration) toast('Could not load image: ' + error.message, true); }
    finally { URL.revokeObjectURL(url); event.target.value = ''; }
  };
  $('artworkRemoveImage').onclick = () => {
    imageGeneration++; picture = null; pan = [0, 0]; $('artworkImageControls').hidden = true;
    $('artworkImageNote').textContent = 'PNG, JPEG or WebP · up to 15 MB.'; draw();
  };
  canvas.addEventListener('pointerdown', event => {
    if (!picture) return;
    dragging = {x: event.clientX, y: event.clientY, pan: pan.slice()}; canvas.setPointerCapture(event.pointerId);
  });
  canvas.addEventListener('pointermove', event => {
    if (!dragging) return;
    const box = canvas.getBoundingClientRect();
    pan = [dragging.pan[0] + (event.clientX - dragging.x) * canvas.width / box.width,
           dragging.pan[1] + (event.clientY - dragging.y) * canvas.height / box.height]; draw();
  });
  ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(name => canvas.addEventListener(name, () => { dragging = null; }));
  $('exportArtwork').onclick = async () => {
    if (exporting) return; exporting = true; $('exportArtwork').disabled = true;
    try {
      await document.fonts.ready; draw();
      if (window.pywebview?.api) {
        const result = await window.pywebview.api.save_artwork(canvas.toDataURL('image/png'));
        if (!result.ok) throw new Error(result.error || 'Export failed.');
        if (result.data.saved) toast('Card artwork saved as PNG.');
      } else {
        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
        if (!blob) throw new Error('Could not create the PNG.');
        const url = URL.createObjectURL(blob), link = document.createElement('a');
        link.href = url; link.download = 'Larp-Studio-Artwork.png'; document.body.append(link); link.click(); link.remove();
        setTimeout(() => URL.revokeObjectURL(url), 30000); toast('PNG export started.');
      }
    } catch (error) { toast(error.message, true); }
    finally { exporting = false; $('exportArtwork').disabled = false; }
  };
  draw(); document.fonts.ready.then(draw);
})();
