import { render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';
import HomePage from '@/app/page';

test('renders the application heading', () => {
  render(<HomePage />);

  expect(
    screen.getByRole('heading', { level: 1, name: 'AI Customer Support Assistant' }),
  ).toBeInTheDocument();
});
