// `modern-screenshot` is heavy and only needed when a user actually captures a
// feedback screenshot — import it lazily so it stays out of the app's boot bundle.

// Bounds for the attached image: long edge ≤ MAX_DIM, JPEG at QUALITY. Keeps the
// base64 payload comfortably small (well under the backend's ~1.4M-char cap) so it
// rides along in the feedback notification email.
const MAX_DIM = 1280;
const QUALITY = 0.7;

// Backend rejects the whole request (422) if `screenshot` exceeds this many
// chars. Callers check against it and drop the image (keeping the text) rather
// than losing the entire feedback submission. Mirrors schemas/feedback.py.
export const SCREENSHOT_MAX_CHARS = 1_400_000;

/** Downscale + JPEG-compress any image source to a bounded data URL. */
async function compress(src: string): Promise<string> {
  const img = new Image();
  img.src = src;
  await img.decode();
  const longest = Math.max(img.width, img.height) || 1;
  const scale = Math.min(1, MAX_DIM / longest);
  const width = Math.max(1, Math.round(img.width * scale));
  const height = Math.max(1, Math.round(img.height * scale));
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (!ctx) return src;
  // Flatten transparency onto white so JPEG doesn't render black.
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, width, height);
  ctx.drawImage(img, 0, 0, width, height);
  return canvas.toDataURL('image/jpeg', QUALITY);
}

/**
 * Capture the current page as a compressed JPEG data URL. The caller is expected
 * to hide any modal/overlay first so the screenshot shows the underlying screen.
 * Throws if the DOM can't be rendered (caller should fall back to upload).
 */
export async function captureScreen(): Promise<string> {
  const { domToCanvas } = await import('modern-screenshot');
  const canvas = await domToCanvas(document.body, { backgroundColor: '#ffffff' });
  return compress(canvas.toDataURL('image/png'));
}

/** Read a user-selected image file and return a compressed JPEG data URL. */
export async function fileToScreenshot(file: File): Promise<string> {
  const dataUrl = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new Error('read failed'));
    reader.readAsDataURL(file);
  });
  return compress(dataUrl);
}
