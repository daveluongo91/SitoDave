document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-carousel]').forEach((carousel) => {
    const slides = Array.from(carousel.querySelectorAll('[data-slide]'));
    const status = carousel.querySelector('.carousel-status');
    const prevBtn = carousel.querySelector('[data-carousel-prev]');
    const nextBtn = carousel.querySelector('[data-carousel-next]');
    let activeIndex = 0;
    let isRotating = false;

    carousel.tabIndex = 0;
    carousel.setAttribute('aria-label', 'Carosello articoli: passa sulla card laterale, toccala oppure usa le frecce della tastiera per visualizzarla');

    const wrappedDistance = (index) => {
      let distance = index - activeIndex;
      const half = slides.length / 2;
      if (distance > half) distance -= slides.length;
      if (distance < -half) distance += slides.length;
      return distance;
    };

    const render = () => {
      slides.forEach((slide, index) => {
        const distance = wrappedDistance(index);
        slide.classList.remove('is-active', 'is-previous', 'is-next', 'is-hidden');
        if (distance === 0) slide.classList.add('is-active');
        else if (distance === -1) slide.classList.add('is-previous');
        else if (distance === 1) slide.classList.add('is-next');
        else slide.classList.add('is-hidden');
        slide.setAttribute('aria-hidden', Math.abs(distance) > 1 ? 'true' : 'false');
      });

      if (status) {
        status.textContent = `${activeIndex + 1} / ${slides.length}`;
      }
    };

    const rotateTo = (index) => {
      if (index === activeIndex || isRotating) return;
      isRotating = true;
      activeIndex = (index + slides.length) % slides.length;
      render();
      window.setTimeout(() => { isRotating = false; }, 400);
    };

    if (prevBtn) {
      prevBtn.addEventListener('click', (e) => {
        e.preventDefault();
        rotateTo(activeIndex - 1);
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', (e) => {
        e.preventDefault();
        rotateTo(activeIndex + 1);
      });
    }

    slides.forEach((slide, index) => {
      slide.addEventListener('pointerenter', (event) => {
        const isSideCard = slide.classList.contains('is-previous') || slide.classList.contains('is-next');
        if (event.pointerType === 'mouse' && isSideCard) rotateTo(index);
      });

      slide.addEventListener('click', (event) => {
        const isSideCard = slide.classList.contains('is-previous') || slide.classList.contains('is-next');
        if (isSideCard) {
          event.preventDefault();
          rotateTo(index);
        }
      });
    });

    carousel.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowLeft') rotateTo(activeIndex - 1);
      if (event.key === 'ArrowRight') rotateTo(activeIndex + 1);
    });

    render();
  });
});
