// [CRITICAL] Mobile viewport height fix
function setMobileHeight() {
    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--vh', `${vh}px`);
}
setMobileHeight();
window.addEventListener('resize', setMobileHeight);
window.addEventListener('orientationchange', () => { setTimeout(setMobileHeight, 100); });
