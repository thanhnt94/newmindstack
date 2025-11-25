
(function (window, document) {
  const MIN_VIEWPORT_HEIGHT = 360;
  const MIN_CONTENT_HEIGHT = 240;
  const MOBILE_MAX_WIDTH = 1024;

  function getAdjustedViewportHeight() {
    const viewport = window.visualViewport;
    const rawHeight = viewport && typeof viewport.height === 'number' ? viewport.height : window.innerHeight;
    const offsetTop = viewport && typeof viewport.offsetTop === 'number' ? viewport.offsetTop : 0;

    return Math.max(rawHeight - offsetTop, MIN_VIEWPORT_HEIGHT);
  }

  function schedule(fn) {
    let frame;

    return function () {
      if (frame) {
        cancelAnimationFrame(frame);
      }

      frame = requestAnimationFrame(() => {
        frame = null;
        fn();
      });
    };
  }

  function setHeights(adjustedHeight) {
    const rootVh = adjustedHeight * 0.01;
    document.documentElement.style.setProperty('--vh', `${rootVh}px`);

    const shell = document.querySelector('.page-shell');
    if (shell) {
      const top = shell.getBoundingClientRect().top;
      const height = Math.max(adjustedHeight - top, MIN_VIEWPORT_HEIGHT);
      shell.style.height = `${height}px`;
      shell.style.minHeight = `${height}px`;
    }

    const layout = document.querySelector('.session-layout');
    if (layout) {
      const top = layout.getBoundingClientRect().top;
      const height = Math.max(adjustedHeight - top, MIN_VIEWPORT_HEIGHT);
      layout.style.height = `${height}px`;
      layout.style.minHeight = `${height}px`;
    }

    const wrapper = document.querySelector('.flashcard-wrapper');
    if (wrapper) {
      const top = wrapper.getBoundingClientRect().top;
      const height = Math.max(adjustedHeight - top, MIN_CONTENT_HEIGHT);
      wrapper.style.height = `${height}px`;
      wrapper.style.minHeight = `${height}px`;
    }

    const content = document.getElementById('flashcard-content');
    if (content) {
      const top = content.getBoundingClientRect().top;
      const height = Math.max(adjustedHeight - top, MIN_CONTENT_HEIGHT);
      content.style.maxHeight = `${height}px`;
    }
  }

  function resetHeights() {
    document.documentElement.style.removeProperty('--vh');

    const shell = document.querySelector('.page-shell');
    if (shell) {
      shell.style.height = '';
      shell.style.minHeight = '';
    }

    const layout = document.querySelector('.session-layout');
    if (layout) {
      layout.style.height = '';
      layout.style.minHeight = '';
    }

    const wrapper = document.querySelector('.flashcard-wrapper');
    if (wrapper) {
      wrapper.style.height = '';
      wrapper.style.minHeight = '';
    }

    const content = document.getElementById('flashcard-content');
    if (content) {
      content.style.maxHeight = '';
    }
  }

  const applyViewportSizing = schedule(() => {
    if (window.innerWidth > MOBILE_MAX_WIDTH) {
      resetHeights();
      return;
    }

    const adjustedHeight = getAdjustedViewportHeight();
    setHeights(adjustedHeight);
  });

  function initFlashcardViewportSizing() {
    applyViewportSizing();

    window.addEventListener('resize', applyViewportSizing, { passive: true });
    window.addEventListener('orientationchange', applyViewportSizing, { passive: true });

    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        applyViewportSizing();
      }
    });

    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', applyViewportSizing);
      window.visualViewport.addEventListener('scroll', applyViewportSizing);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFlashcardViewportSizing, { once: true });
  } else {
    initFlashcardViewportSizing();
  }

  window.flashcardViewport = {
    refresh: () => {
      applyViewportSizing();
    },
  };
})(window, document);
