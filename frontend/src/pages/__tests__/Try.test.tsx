import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { UserEvent } from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import demoContent from '@/demo/demoContent.json';
import Try from '../Try';

const demo = demoContent as {
  module_title: string;
  icon: string;
  learning_objectives: string[];
  lessons: { type: string; xp_reward: number; content_json: Record<string, unknown> }[];
  tease: { extra_level_count: number; other_module_count: number };
};
const totalXp = demo.lessons.reduce((sum, l) => sum + l.xp_reward, 0);

let fetchSpy: ReturnType<typeof vi.fn>;
beforeEach(() => {
  fetchSpy = vi.fn(() => Promise.reject(new Error('no network in /try')));
  vi.stubGlobal('fetch', fetchSpy);
});
afterEach(() => {
  vi.unstubAllGlobals();
});

function renderTry() {
  return render(
    <MemoryRouter initialEntries={['/try']}>
      <Routes>
        <Route path="/try" element={<Try />} />
        <Route path="/signup" element={<div>SIGNUP PAGE</div>} />
        <Route path="/login" element={<div>LOGIN PAGE</div>} />
        <Route path="/privacy" element={<div>PRIVACY PAGE</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

/** Drive the whole lesson arc from the intro screen to the completion screen. */
async function completeArc(user: UserEvent) {
  await user.click(screen.getByRole('button', { name: /start/i }));
  for (const lesson of demo.lessons) {
    if (lesson.type === 'card') {
      await user.click(screen.getByRole('button', { name: /got it/i }));
    } else if (lesson.type === 'video') {
      await user.click(screen.getByLabelText('I watched this'));
      await user.click(screen.getByRole('button', { name: /mark complete/i }));
    } else if (lesson.type === 'quiz') {
      const c = lesson.content_json as { choices: string[]; answer_index: number };
      await user.click(screen.getByRole('radio', { name: c.choices[c.answer_index] }));
      await user.click(screen.getByRole('button', { name: /check answer/i }));
      await user.click(screen.getByRole('button', { name: /continue/i }));
    } else if (lesson.type === 'scenario') {
      const c = lesson.content_json as { choices: { label: string }[]; correct_index: number };
      await user.click(screen.getByRole('radio', { name: c.choices[c.correct_index].label }));
      await user.click(screen.getByRole('button', { name: /check answer/i }));
      await user.click(screen.getByRole('button', { name: /continue/i }));
    } else {
      throw new Error(`unknown demo lesson type: ${lesson.type}`);
    }
  }
}

describe('Try page (public demo)', () => {
  it('renders the intro unauthenticated with module info and objectives, without any fetch', () => {
    renderTry();

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(/try your first investikid lesson/i);
    expect(screen.getByText(/no account needed/i)).toBeInTheDocument();
    expect(screen.getByText(demo.module_title)).toBeInTheDocument();
    for (const obj of demo.learning_objectives) {
      expect(screen.getByText(obj)).toBeInTheDocument();
    }
    expect(screen.getByRole('button', { name: /start/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /back to log in/i })).toHaveAttribute('href', '/login');
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('shows a progress indicator and a persistent Sign up escape link during the flow', async () => {
    const user = userEvent.setup();
    renderTry();

    await user.click(screen.getByRole('button', { name: /start/i }));
    expect(screen.getByText(`Lesson 1 of ${demo.lessons.length}`)).toBeInTheDocument();
    expect(screen.getByRole('progressbar', { name: /lesson progress/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Sign up' })).toHaveAttribute('href', '/signup');

    await user.click(screen.getByRole('button', { name: /got it/i }));
    expect(screen.getByText(`Lesson 2 of ${demo.lessons.length}`)).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('completes the full arc with zero fetch calls, totals the XP, teases locked content, and converts to /signup', async () => {
    const user = userEvent.setup();
    renderTry();

    await completeArc(user);

    expect(screen.getByText(/you finished your first lesson/i)).toBeInTheDocument();
    expect(screen.getByText(`+${totalXp} XP`)).toBeInTheDocument();

    // Tease panel is driven by the JSON counts (extra_level_count=2 → "Levels 2 and 3").
    expect(screen.getByText(/levels 2 and 3 are waiting/i)).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`${demo.tease.other_module_count} more modules`))).toBeInTheDocument();
    expect(screen.getByText(/from budgeting to your brain on money/i)).toBeInTheDocument();

    expect(screen.getByRole('link', { name: /parents: learn more/i })).toHaveAttribute('href', '/privacy');
    expect(fetchSpy).not.toHaveBeenCalled();

    await user.click(screen.getByRole('link', { name: /create an account to save your progress/i }));
    expect(screen.getByText('SIGNUP PAGE')).toBeInTheDocument();
  });

  it('intro has no axe violations', async () => {
    const { container } = renderTry();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('a lesson step has no axe violations', async () => {
    const user = userEvent.setup();
    const { container } = renderTry();
    await user.click(screen.getByRole('button', { name: /start/i }));
    expect(await axe(container)).toHaveNoViolations();
  });

  it('completion screen has no axe violations', async () => {
    const user = userEvent.setup();
    const { container } = renderTry();
    await completeArc(user);
    expect(await axe(container)).toHaveNoViolations();
  });
});
