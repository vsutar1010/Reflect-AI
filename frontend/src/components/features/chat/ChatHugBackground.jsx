import React from 'react';
import hugArtwork from '../../../assets/chat-hug-artwork.png';

/**
 * Chat panel backdrop — the actual reference artwork (a real image file,
 * not a generated illustration or particle simulation) of two glowing
 * figures embracing. `object-fit: cover` keeps the centered subject
 * (figures + heart) intact on any panel aspect ratio by cropping the
 * empty outer edges instead of stretching — the artwork is horizontally
 * centered within itself, so a center-cropped slice on narrow/tall
 * panels (phones) still keeps both figures and the heart in frame. The
 * only motion is a whole-image CSS animation (see `hug-breathe` in
 * index.css); the image file itself never changes.
 */
export default function ChatHugBackground() {
  return (
    <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
      <img
        src={hugArtwork}
        alt=""
        aria-hidden="true"
        draggable="false"
        className="chat-hug-img absolute inset-0 w-full h-full object-cover select-none"
      />
    </div>
  );
}
