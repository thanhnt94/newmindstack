(function (window, document) {
  const MIN_VIEWPORT_HEIGHT = 360;
  const MIN_CONTENT_HEIGHT = 240;

  function getAdjustedViewportHeight() {
    const viewport = window.visualViewport;
    const rawHeight = viewport ? viewport.height : window.innerHeight;
    const offsetTop = viewport ? viewport.offsetTop || 0 : 0;

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

  function applyViewportSizing() {
    const adjustedHeight = getAdjustedViewportHeight();
    const rootVh = adjustedHeight * 0.01;

    document.documentElement.style.setProperty('--vh', `${rootVh}px`);

    const pageShell = document.querySelector('.page-shell');
    if (pageShell) {
      const shellTop = pageShell.getBoundingClientRect().top;
      const shellHeight = Math.max(adjustedHeight - shellTop, MIN_VIEWPORT_HEIGHT);

      pageShell.style.height = `${shellHeight}px`;
      pageShell.style.minHeight = `${shellHeight}px`;
    }

    const sessionLayout = document.querySelector('.session-layout');
    if (sessionLayout) {
      const layoutTop = sessionLayout.getBoundingClientRect().top;
      const layoutHeight = Math.max(adjustedHeight - layoutTop, MIN_VIEWPORT_HEIGHT);

      sessionLayout.style.height = `${layoutHeight}px`;
      sessionLayout.style.minHeight = `${layoutHeight}px`;
      sessionLayout.style.maxHeight = `${layoutHeight}px`;
    }

    const flashcardWrapper = document.querySelector('.flashcard-wrapper');
    if (flashcardWrapper) {
      const wrapperTop = flashcardWrapper.getBoundingClientRect().top;
      const wrapperHeight = Math.max(adjustedHeight - wrapperTop, MIN_CONTENT_HEIGHT);

      flashcardWrapper.style.height = `${wrapperHeight}px`;
      flashcardWrapper.style.minHeight = `${wrapperHeight}px`;
    }

    const flashcardContent = document.getElementById('flashcard-content');
    if (flashcardContent) {
      const contentTop = flashcardContent.getBoundingClientRect().top;
      const contentHeight = Math.max(adjustedHeight - contentTop, MIN_CONTENT_HEIGHT);

      flashcardContent.style.maxHeight = `${contentHeight}px`;
    }
  }

  function initFlashcardViewportSizing() {
    const scheduledApply = schedule(applyViewportSizing);

    applyViewportSizing();

    window.addEventListener('resize', scheduledApply, { passive: true });
    window.addEventListener('orientationchange', scheduledApply, { passive: true });

    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        scheduledApply();
      }
    });

    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', scheduledApply);
      window.visualViewport.addEventListener('scroll', scheduledApply);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFlashcardViewportSizing, { once: true });
  } else {
    initFlashcardViewportSizing();
  }

  window.flashcardViewport = {
    refresh: applyViewportSizing,
  };
})(window, document);
