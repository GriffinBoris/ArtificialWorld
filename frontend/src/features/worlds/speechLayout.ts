export interface SpeechBounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

export function placeSpeechBubble(preferred: SpeechBounds, viewport: SpeechBounds, placed: SpeechBounds[]) {
  const gap = 10;
  const candidates = [
    preferred,
    ...placed.flatMap((other) => [
      { ...preferred, x: other.x - preferred.width - gap, y: other.y },
      { ...preferred, x: other.x + other.width + gap, y: other.y },
      { ...preferred, x: other.x, y: other.y - preferred.height - gap },
      { ...preferred, x: other.x, y: other.y + other.height + gap },
    ]),
  ];

  const bounded = candidates.map((candidate) => ({
    ...candidate,
    x: Math.max(viewport.x, Math.min(candidate.x, viewport.x + viewport.width - candidate.width)),
    y: Math.max(viewport.y, Math.min(candidate.y, viewport.y + viewport.height - candidate.height)),
  }));
  bounded.sort(
    (a, b) => Math.hypot(a.x - preferred.x, a.y - preferred.y) - Math.hypot(b.x - preferred.x, b.y - preferred.y)
  );

  return bounded.find(
    (candidate) =>
      candidate.width <= viewport.width &&
      candidate.height <= viewport.height &&
      placed.every(
        (other) =>
          candidate.x + candidate.width + gap <= other.x ||
          candidate.x >= other.x + other.width + gap ||
          candidate.y + candidate.height + gap <= other.y ||
          candidate.y >= other.y + other.height + gap
      )
  );
}
