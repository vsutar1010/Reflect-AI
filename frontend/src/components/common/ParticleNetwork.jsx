import { useEffect, useRef } from 'react';
import { usePrefersReducedMotion } from '../../hooks/usePrefersReducedMotion';

// Same two accent hues used across the UI (tech chips, buttons), plus a
// soft near-white for a few "sparkle" nodes — keeps the network reading
// as part of the existing theme rather than a bolted-on effect.
const PARTICLE_COLORS = ['#4F8BFF', '#4F8BFF', '#8B5CF6', '#8B5CF6', '#E2E8F0'];
const LINE_COLOR = '#8FB4FF';

const MAX_LINK_DISTANCE = 130;
const CURSOR_RADIUS = 150;
const CURSOR_FORCE = 0.045;
const MAX_SPEED = 0.5;
const VELOCITY_DAMPING = 0.985;
const RIPPLE_MAX_RADIUS = 160;
const RIPPLE_RING_WIDTH = 40;

// Desktop gets the full network; tablet/mobile scale down so the effect
// stays subtle and cheap on smaller/weaker devices.
function particleCountFor(width) {
  if (width < 640) return 22;
  if (width < 1024) return 46;
  return 85;
}

function randomBetween(min, max) {
  return min + Math.random() * (max - min);
}

function createParticle(width, height) {
  const angle = Math.random() * Math.PI * 2;
  const speed = randomBetween(0.05, 0.22);
  return {
    x: Math.random() * width,
    y: Math.random() * height,
    vx: Math.cos(angle) * speed,
    vy: Math.sin(angle) * speed,
    radius: randomBetween(1, 2.2),
    color: PARTICLE_COLORS[Math.floor(Math.random() * PARTICLE_COLORS.length)],
  };
}

/**
 * Canvas-based particle/network backdrop — small drifting nodes with
 * thin connecting lines, a gentle cursor-repulsion field, and a subtle
 * click ripple. One <canvas>, not per-particle DOM nodes, so it stays
 * cheap even at ~85 particles.
 *
 * `position: fixed` (not absolute) deliberately: every page that mounts
 * AnimatedBackground is a plain, non-transformed ancestor chain up to
 * <body> (no motion.div wraps it), so `fixed` here anchors to the real
 * viewport. That keeps the canvas exactly viewport-sized regardless of
 * how tall the page's content is — avoids ever rasterizing a
 * many-times-viewport-height canvas — and means clientX/clientY from
 * window mouse events map onto it with zero coordinate conversion.
 */
export default function ParticleNetwork() {
  const canvasRef = useRef(null);
  const prefersReducedMotion = usePrefersReducedMotion();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let width = window.innerWidth;
    let height = window.innerHeight;
    let particles = [];
    let ripples = [];
    let frameId = null;
    let resizeFrame = null;
    const mouse = { x: -9999, y: -9999, active: false };

    function applySize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function seedParticles() {
      const targetCount = particleCountFor(width);
      particles = Array.from({ length: targetCount }, () => createParticle(width, height));
    }

    function handleResize() {
      if (resizeFrame) return;
      resizeFrame = requestAnimationFrame(() => {
        resizeFrame = null;
        width = window.innerWidth;
        height = window.innerHeight;
        applySize();
        const targetCount = particleCountFor(width);
        if (particles.length < targetCount) {
          particles = particles.concat(
            Array.from({ length: targetCount - particles.length }, () => createParticle(width, height))
          );
        } else if (particles.length > targetCount) {
          particles = particles.slice(0, targetCount);
        }
        if (prefersReducedMotion) drawStaticFrame();
      });
    }

    // Particles fade toward the screen center so the middle of the
    // viewport — where the main UI content usually sits — stays visually
    // calm, while the network reads clearly near the edges.
    function centerFade(x, y) {
      const cx = width / 2;
      const cy = height / 2;
      const maxR = Math.max(width, height) * 0.32;
      const t = Math.min(Math.hypot(x - cx, y - cy) / maxR, 1);
      return 0.18 + t * 0.82;
    }

    function drawLinks() {
      for (let i = 0; i < particles.length; i++) {
        const a = particles[i];
        for (let j = i + 1; j < particles.length; j++) {
          const b = particles[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const distSq = dx * dx + dy * dy;
          if (distSq >= MAX_LINK_DISTANCE * MAX_LINK_DISTANCE) continue;
          const dist = Math.sqrt(distSq);
          const proximity = 1 - dist / MAX_LINK_DISTANCE;
          const fade = (centerFade(a.x, a.y) + centerFade(b.x, b.y)) / 2;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.strokeStyle = LINE_COLOR;
          ctx.globalAlpha = proximity * fade * 0.18;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }
      ctx.globalAlpha = 1;
    }

    function drawParticle(p) {
      const fade = centerFade(p.x, p.y);
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.globalAlpha = fade * 0.75;
      ctx.fill();

      // Very subtle glow, only on the slightly-larger particles.
      if (p.radius > 1.8) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius * 3, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = fade * 0.06;
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    }

    function drawStaticFrame() {
      ctx.clearRect(0, 0, width, height);
      drawLinks();
      for (const p of particles) drawParticle(p);
    }

    function step() {
      ctx.clearRect(0, 0, width, height);

      for (const p of particles) {
        if (mouse.active) {
          const dx = p.x - mouse.x;
          const dy = p.y - mouse.y;
          const dist = Math.hypot(dx, dy);
          if (dist < CURSOR_RADIUS && dist > 0.001) {
            const push = (1 - dist / CURSOR_RADIUS) * CURSOR_FORCE;
            p.vx += (dx / dist) * push;
            p.vy += (dy / dist) * push;
          }
        }

        for (const ripple of ripples) {
          const dx = p.x - ripple.x;
          const dy = p.y - ripple.y;
          const dist = Math.hypot(dx, dy);
          if (dist > 0.001 && Math.abs(dist - ripple.radius) < RIPPLE_RING_WIDTH) {
            const push = (1 - Math.abs(dist - ripple.radius) / RIPPLE_RING_WIDTH) * 0.05 * ripple.alpha;
            p.vx += (dx / dist) * push;
            p.vy += (dy / dist) * push;
          }
        }

        // Damping so cursor/ripple nudges decay back to baseline drift
        // instead of accumulating into fast, mechanical-looking motion.
        p.vx *= VELOCITY_DAMPING;
        p.vy *= VELOCITY_DAMPING;
        const speed = Math.hypot(p.vx, p.vy);
        if (speed > MAX_SPEED) {
          p.vx = (p.vx / speed) * MAX_SPEED;
          p.vy = (p.vy / speed) * MAX_SPEED;
        }

        p.x += p.vx;
        p.y += p.vy;

        if (p.x < -20) p.x = width + 20;
        if (p.x > width + 20) p.x = -20;
        if (p.y < -20) p.y = height + 20;
        if (p.y > height + 20) p.y = -20;

        drawParticle(p);
      }

      drawLinks();

      ripples = ripples.filter((r) => r.alpha > 0.02 && r.radius < RIPPLE_MAX_RADIUS);
      for (const r of ripples) {
        ctx.beginPath();
        ctx.arc(r.x, r.y, r.radius, 0, Math.PI * 2);
        ctx.strokeStyle = '#8B5CF6';
        ctx.globalAlpha = r.alpha * 0.35;
        ctx.lineWidth = 1;
        ctx.stroke();
        r.radius += 2.2;
        r.alpha *= 0.94;
      }
      ctx.globalAlpha = 1;

      frameId = requestAnimationFrame(step);
    }

    function handleMouseMove(e) {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
      mouse.active = true;
    }

    function handleMouseLeave() {
      mouse.active = false;
    }

    function handleClick(e) {
      ripples.push({ x: e.clientX, y: e.clientY, radius: 4, alpha: 0.9 });
    }

    function handleVisibilityChange() {
      if (prefersReducedMotion) return;
      if (document.hidden) {
        if (frameId) cancelAnimationFrame(frameId);
        frameId = null;
      } else if (!frameId) {
        frameId = requestAnimationFrame(step);
      }
    }

    applySize();
    seedParticles();
    window.addEventListener('resize', handleResize, { passive: true });
    document.addEventListener('visibilitychange', handleVisibilityChange);

    if (prefersReducedMotion) {
      drawStaticFrame();
    } else {
      window.addEventListener('mousemove', handleMouseMove, { passive: true });
      window.addEventListener('mouseleave', handleMouseLeave, { passive: true });
      window.addEventListener('click', handleClick, { passive: true });
      frameId = requestAnimationFrame(step);
    }

    return () => {
      if (frameId) cancelAnimationFrame(frameId);
      if (resizeFrame) cancelAnimationFrame(resizeFrame);
      window.removeEventListener('resize', handleResize);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
      window.removeEventListener('click', handleClick);
    };
  }, [prefersReducedMotion]);

  return <canvas ref={canvasRef} className="fixed inset-0 pointer-events-none" aria-hidden="true" />;
}
