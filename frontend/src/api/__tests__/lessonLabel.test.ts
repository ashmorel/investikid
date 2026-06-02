import { describe, it, expect } from 'vitest';
import { lessonLabel } from '@/api/admin';

describe('lessonLabel', () => {
  it('uses the card title', () => {
    expect(lessonLabel({ type: 'card', content_json: { title: 'A stock is a slice' } })).toBe('A stock is a slice');
  });

  it('uses the quiz question', () => {
    expect(lessonLabel({ type: 'quiz', content_json: { question: 'What is a dividend?' } })).toBe('What is a dividend?');
  });

  it('uses the scenario prompt', () => {
    expect(lessonLabel({ type: 'scenario', content_json: { prompt: 'A share you bought drops...' } })).toBe('A share you bought drops...');
  });

  it('uses the video caption instead of "Untitled"', () => {
    expect(lessonLabel({ type: 'video', content_json: { caption: 'What is a stock? (intro)', youtube_id: 'p7HKvqRI_Bo' } })).toBe('What is a stock? (intro)');
  });

  it('falls back to the youtube id for a captionless video', () => {
    expect(lessonLabel({ type: 'video', content_json: { youtube_id: 'p7HKvqRI_Bo' } })).toBe('Video (p7HKvqRI_Bo)');
  });

  it('falls back to "Untitled" only when nothing usable exists', () => {
    expect(lessonLabel({ type: 'card', content_json: {} })).toBe('Untitled');
  });
});
