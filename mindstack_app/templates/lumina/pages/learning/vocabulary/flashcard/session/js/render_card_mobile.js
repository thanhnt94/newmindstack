window.renderMobileCardHtml = function (data, o) {
  // Lumina Mobile Card Renderer
  // o = options: { itemId, fTxt, bTxt, frontImg, backImg, frontAudioUrl, backAudioUrl, buttonsHtml, ... }

  // Audio Buttons
  const audioBtnFront = `<button class="lumina-audio-btn play-audio-btn ${o.hasFrontAudio ? '' : 'opacity-50'}" data-audio-target="#front-audio-mobile" data-side="front" data-item-id="${o.itemId}" ${o.hasFrontAudio ? '' : 'disabled'}><i class="fa-solid fa-volume-high"></i></button>`;
  const audioBtnBack = `<button class="lumina-audio-btn play-audio-btn ${o.hasBackAudio ? '' : 'opacity-50'}" data-audio-target="#back-audio-mobile" data-side="back" data-item-id="${o.itemId}" ${o.hasBackAudio ? '' : 'disabled'}><i class="fa-solid fa-volume-high"></i></button>`;

  // Flip Button (Overlay)

  const flipOverlay = `<button class="js-flip-card-btn absolute inset-0 w-full h-full cursor-pointer z-10 opacity-0" aria-label="Lật thẻ"></button>`;

  // Helper for Media
  const renderImg = (src) => src ? `<div class="lumina-card-image mb-4"><img src="${src}" class="rounded-xl max-h-48 object-contain mx-auto shadow-sm"></div>` : '';

  return `
    <div class="flashcard-card-container h-full w-full flex flex-col relative">
      <div class="js-flashcard-card flashcard-card relative w-full h-full transition-transform duration-500 transform-style-3d">
        
        <!-- FRONT FACE -->
        <div class="face front absolute inset-0 backface-hidden bg-white rounded-3xl shadow-sm border border-gray-100 flex flex-col overflow-hidden">
          
          <!-- Top Bar -->
          <div class="h-14 flex items-center justify-between px-5 relative z-20">
             <div class="text-sm font-bold text-gray-400">MẶT TRƯỚC</div>
             ${audioBtnFront}
          </div>

          <!-- Content -->
          <div class="flex-1 flex flex-col items-center justify-center p-6 text-center relative z-0">
             ${renderImg(o.frontImg)}
             <div class="lumina-card-text text-3xl font-bold text-gray-900 leading-tight select-none">
                ${o.fTxt}
             </div>
             <p class="mt-8 text-sm text-gray-400 font-medium animate-pulse">Chạm để lật</p>
          </div>

          <!-- Flip Trigger -->
          ${flipOverlay}

          <!-- Hidden Audio Element -->
          <audio id="front-audio-mobile" class="hidden" src="${o.frontAudioUrl || ''}"></audio>
        </div>

        <!-- BACK FACE -->
        <div class="face back absolute inset-0 backface-hidden rotate-y-180 bg-white rounded-3xl shadow-sm border border-gray-100 flex flex-col overflow-hidden">
           
           <!-- Top Bar -->
          <div class="h-14 flex items-center justify-between px-5 relative z-20">
             <div class="text-sm font-bold text-gray-400">MẶT SAU</div>
             ${audioBtnBack}
          </div>

          <!-- Content -->
          <div class="flex-1 flex flex-col items-center justify-center p-6 text-center relative z-0">
             ${renderImg(o.backImg)}
             <div class="lumina-card-text text-2xl font-medium text-gray-800 leading-relaxed select-none">
                ${o.bTxt}
             </div>
          </div>
          
           <!-- Actions Container (Sticks to bottom) -->
           <div class="lumina-actions-container p-4 pb-8 bg-white/90 backdrop-blur-sm z-30">
               <div class="actions js-internal-actions grid grid-cols-4 gap-3" data-button-count="${o.buttonCount}">
                   ${o.buttonsHtml}
               </div>
           </div>

          <!-- Hidden Audio Element -->
          <audio id="back-audio-mobile" class="hidden" src="${o.backAudioUrl || ''}"></audio>

        </div>
      </div>
    </div>`;
};
