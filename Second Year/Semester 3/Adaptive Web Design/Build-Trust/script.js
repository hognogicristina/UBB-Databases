(function () {
  'use strict';

  if (!('querySelector' in document)) return;

  if ('scrollRestoration' in history) {
    history.scrollRestoration = 'manual';
  }

  window.addEventListener('load', () => {
    window.scrollTo(0, 0);
  });

  const trustProgress = document.getElementById('trustProgress');
  const trustScoreEl = document.getElementById('trustScore');
  const trustStateEl = document.getElementById('trustState');
  const trustNarrativeEl = document.getElementById('trustNarrative');
  const trustTrackEl = document.querySelector('.trust-meter__track');
  const trustTapButton = document.getElementById('trustTap');
  const trustExperimentEl = document.querySelector('.trust-experiment');
  const trustResetWrap = document.getElementById('trustResetWrap');
  const trustResetButton = document.getElementById('trustReset');
  const fireworksEl = document.getElementById('fireworks');

  const navToggle = document.querySelector('.nav__toggle');
  const primaryNav = document.getElementById('primary-nav');

  const defaultStateMessage = trustStateEl ? trustStateEl.textContent : '';
  const defaultNarrativeMessage = trustNarrativeEl ? trustNarrativeEl.textContent : '';

  let trustScore = 0;
  const threshold = 100;
  const penaltyWindow = 900;
  const increment = 6;
  let lastTap = 0;
  let isBroken = false;

  const stateCopy = score => {
    if (isBroken) return 'Status: trust collapsed. Start over slowly.';
    if (score >= threshold) return 'Status: trust bar full.';
    if (score >= 60) return 'Status: patience showing results.';
    if (score >= 30) return 'Status: steady progress.';
    if (score > 0) return 'Status: first signals appearing.';
    return 'Gently begin. Trust grows with steady steps.';
  };

  const renderTrust = () => {
    const clamped = Math.max(0, Math.min(threshold, trustScore));

    if (trustProgress) {
      trustProgress.style.width = `${(clamped / threshold) * 100}%`;
    }
    if (trustScoreEl) {
      trustScoreEl.textContent = `${Math.round((clamped / threshold) * 100)}%`;
    }
    if (trustTrackEl) {
      trustTrackEl.setAttribute('aria-valuenow', String(clamped));
    }
    if (trustStateEl) {
      trustStateEl.textContent = stateCopy(clamped);
    }
  };

  const breakTrust = () => {
    trustScore = 0;
    isBroken = true;

    if (trustTrackEl) trustTrackEl.classList.add('is-broken');
    if (trustProgress) trustProgress.classList.add('is-broken');

    if (trustNarrativeEl) {
      trustNarrativeEl.textContent =
        'Too fast. Trust cracked and reset. Breathe, slow down, try again.';
    }

    renderTrust();

    setTimeout(() => {
      isBroken = false;
      if (trustTrackEl) trustTrackEl.classList.remove('is-broken');
      if (trustProgress) trustProgress.classList.remove('is-broken');
      renderTrust();
    }, 800);
  };

  const celebrate = () => {
    if (trustNarrativeEl) {
      trustNarrativeEl.textContent =
        'Learning: trust thrives when patience, transparency, and care move in rhythm.';
    }
    if (trustTapButton) {
      trustTapButton.disabled = true;
      trustTapButton.classList.add('is-used');
    }
    if (trustExperimentEl) {
      trustExperimentEl.classList.add('is-complete');
    }
    if (trustResetWrap) {
      trustResetWrap.hidden = false;
    }
    if (trustResetButton) {
      trustResetButton.disabled = false;
      try {
        trustResetButton.focus({preventScroll: true});
      } catch (e) {
        trustResetButton.focus();
      }
    }

    if (fireworksEl) {
      fireworksEl.innerHTML = '';
      const bursts = 56;
      const spread = Math.max(window.innerWidth, window.innerHeight) * 0.52;
      const palette = [
        '#ffd27d',
        '#ff9f76',
        '#ff7cc4',
        '#8fd3ff',
        '#9fffa0',
        '#f6f06d',
        '#ffa3b5',
        '#d9a6ff'
      ];
      fireworksEl.classList.add('is-active');

      const createParticle = (className, options) => {
        const particle = document.createElement('span');
        particle.className = `firework ${className}`;
        particle.style.left = `${options.originX}%`;
        particle.style.top = `${options.originY}%`;
        particle.style.transformOrigin = 'center';
        particle.style.setProperty('--spark-delay', `${options.delay}s`);
        particle.style.setProperty('--spark-color', options.color);
        particle.style.setProperty('--spark-rotate', `${options.rotate}deg`);
        particle.style.setProperty('--spark-scale', `${options.scale}`);
        particle.style.setProperty('--tx', `${options.tx}px`);
        particle.style.setProperty('--ty', `${options.ty}px`);
        fireworksEl.appendChild(particle);
      };

      for (let i = 0; i < bursts; i++) {
        const angle = Math.random() * 2 * Math.PI;
        const distance = spread * (0.32 + Math.random() * 0.85);
        const color = palette[Math.floor(Math.random() * palette.length)];
        const originX = 10 + Math.random() * 80;
        const originY = 12 + Math.random() * 76;
        const delay = +(Math.random() * 0.55).toFixed(2);
        const rotate = Math.random() * 360;
        const scale = +(0.85 + Math.random() * 1.6).toFixed(2);
        const tx = Math.cos(angle) * distance;
        const ty = Math.sin(angle) * distance;

        createParticle('firework--particle', {
          originX,
          originY,
          delay,
          color,
          rotate,
          scale,
          tx,
          ty
        });
        createParticle('firework--shard', {
          originX,
          originY,
          delay,
          color,
          rotate: rotate + 24,
          scale,
          tx: tx * 1.1,
          ty: ty * 1.1
        });

        if (Math.random() > 0.35) {
          createParticle('firework--flash', {
            originX,
            originY,
            delay: delay + 0.08,
            color,
            rotate,
            scale,
            tx: tx * 0.7,
            ty: ty * 0.7
          });
        }
      }

      setTimeout(() => {
        fireworksEl.classList.remove('is-active');
        fireworksEl.innerHTML = '';
      }, 2600);
    }
  };

  const resetTrustExperience = () => {
    trustScore = 0;
    isBroken = false;
    lastTap = 0;

    if (trustExperimentEl) {
      trustExperimentEl.classList.remove('is-complete');
    }
    if (trustResetWrap) {
      trustResetWrap.hidden = true;
    }
    if (trustNarrativeEl) {
      trustNarrativeEl.textContent = defaultNarrativeMessage;
    }
    if (trustStateEl) {
      trustStateEl.textContent = defaultStateMessage;
    }
    if (trustTapButton) {
      trustTapButton.disabled = false;
      trustTapButton.classList.remove('is-used');
    }
    if (trustTrackEl) {
      trustTrackEl.classList.remove('is-broken');
    }
    if (trustProgress) {
      trustProgress.classList.remove('is-broken');
    }

    renderTrust();

    if (trustTapButton && typeof trustTapButton.focus === 'function') {
      try {
        trustTapButton.focus({preventScroll: true});
      } catch (e) {
        trustTapButton.focus();
      }
    }
  };

  if (navToggle && primaryNav) {
    const isNavToggleVisible = () => {
      return window.getComputedStyle(navToggle).display !== 'none';
    };

    const playToggleCloseFeedback = () => {
      if (!isNavToggleVisible()) return;
      navToggle.classList.remove('nav__toggle--closing');
      void navToggle.offsetWidth;
      navToggle.classList.add('nav__toggle--closing');
      navToggle.addEventListener(
        'animationend',
        () => navToggle.classList.remove('nav__toggle--closing'),
        {once: true}
      );
    };

    const closeNav = (animate = true) => {
      navToggle.setAttribute('aria-expanded', 'false');

      const shouldAnimate = animate && isNavToggleVisible();

      if (!shouldAnimate) {
        primaryNav.classList.remove('is-open', 'is-closing');
        return;
      }

      primaryNav.classList.remove('is-open');
      primaryNav.classList.add('is-closing');
      primaryNav.addEventListener(
        'animationend',
        () => {
          primaryNav.classList.remove('is-closing');
        },
        {once: true}
      );
    };

    navToggle.addEventListener('click', () => {
      const expanded = navToggle.getAttribute('aria-expanded') === 'true';
      navToggle.setAttribute('aria-expanded', String(!expanded));

      if (expanded) {
        playToggleCloseFeedback();
        closeNav(true);
        return;
      }

      primaryNav.classList.remove('is-closing');
      primaryNav.classList.add('is-open');

      if (!expanded) {
        const firstLink = primaryNav.querySelector('a');
        if (firstLink && typeof firstLink.focus === 'function') {
          try {
            firstLink.focus({preventScroll: true});
          } catch (e) {
            firstLink.focus();
          }
        }
      }
    });

    primaryNav.addEventListener('click', event => {
      const target = event.target;
      if (!target || !target.tagName) return;
      if (target.tagName.toLowerCase() !== 'a') return;
      closeNav(true);
    });

    if (typeof window.matchMedia === 'function') {
      const desktopMedia = window.matchMedia('(min-width: 721px)');
      const handleDesktopChange = event => {
        if (!event.matches) return;
        closeNav(false);
      };

      if (typeof desktopMedia.addEventListener === 'function') {
        desktopMedia.addEventListener('change', handleDesktopChange);
      }
    }

    closeNav();
  }

  const flipCards = Array.from(document.querySelectorAll('.scenario-card, .variation-card'));
  const clickFlipMedia = typeof window.matchMedia === 'function'
    ? window.matchMedia('(hover: none), (pointer: coarse)')
    : null;
  let clickFlipEnabled = clickFlipMedia ? clickFlipMedia.matches : false;

  const setExpandedState = (card, expanded) => {
    card.setAttribute('aria-expanded', String(expanded));
  };

  const handleCardFlip = event => {
    if (!clickFlipEnabled) return;
    const card = event.currentTarget;
    const isActive = card.classList.toggle('is-flipped');
    setExpandedState(card, isActive);
  };

  const syncFlipMode = shouldUseClick => {
    clickFlipEnabled = shouldUseClick;
    document.documentElement.classList.toggle('supports-card-taps', shouldUseClick);

    flipCards.forEach(card => {
      card.removeEventListener('click', handleCardFlip);
      card.classList.remove('is-flipped');

      if (shouldUseClick) {
        setExpandedState(card, false);
        card.addEventListener('click', handleCardFlip);
      } else {
        card.removeAttribute('aria-expanded');
      }
    });
  };

  if (flipCards.length) {
    syncFlipMode(clickFlipEnabled);

    if (clickFlipMedia) {
      const handleMediaChange = event => {
        syncFlipMode(event.matches);
      };

      if (typeof clickFlipMedia.addEventListener === 'function') {
        clickFlipMedia.addEventListener('change', handleMediaChange);
      } else if (typeof clickFlipMedia.addListener === 'function') {
        clickFlipMedia.addListener(handleMediaChange);
      }
    }
  }

  if (trustTapButton) {
    trustTapButton.addEventListener('click', () => {
      const now = Date.now();
      const delta = now - lastTap;
      lastTap = now;

      if (delta < penaltyWindow && delta > 0) {
        breakTrust();
        trustTapButton.disabled = false;
        trustTapButton.classList.remove('is-used');
        return;
      }

      trustScore = Math.min(threshold, trustScore + increment);
      renderTrust();
      if (trustNarrativeEl) {
        trustNarrativeEl.textContent = 'Nice, another calm signal logged.';
      }
      if (trustScore >= threshold) {
        celebrate();
      }
    });
    renderTrust();
  }

  if (trustResetButton) {
    trustResetButton.addEventListener('click', resetTrustExperience);
  }
})();
