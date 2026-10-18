import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PantryInput } from '../src/components/pantry/PantryInput';
import { PantryTagList } from '../src/components/pantry/PantryTagList';
import { QuickAddPantry } from '../src/components/pantry/QuickAddPantry';

describe('Pantry Management Components', () => {
  it('adds ingredient via input and form submission', () => {
    const handleAdd = vi.fn().mockReturnValue(true);
    render(<PantryInput onAdd={handleAdd} />);

    const input = screen.getByPlaceholderText(/Add ingredient/i);
    const submitBtn = screen.getByRole('button', { name: /Add/i });

    fireEvent.change(input, { target: { value: 'garlic' } });
    fireEvent.click(submitBtn);

    expect(handleAdd).toHaveBeenCalledWith('garlic', 7);
    expect(input).toHaveValue('');
  });

  it('renders pantry tags and allows removal', () => {
    const handleRemove = vi.fn();
    const handleClear = vi.fn();
    render(
      <PantryTagList
        ingredients={['tomato', 'onion', 'pasta']}
        onRemove={handleRemove}
        onClear={handleClear}
      />
    );

    expect(screen.getByText('tomato')).toBeInTheDocument();
    expect(screen.getByText('onion')).toBeInTheDocument();
    expect(screen.getByText('pasta')).toBeInTheDocument();

    const removeBtns = screen.getAllByRole('button', { name: /Remove/i });
    expect(removeBtns.length).toBe(3);

    fireEvent.click(removeBtns[0]);
    expect(handleRemove).toHaveBeenCalledWith('tomato');

    const clearBtn = screen.getByRole('button', { name: /Clear All/i });
    fireEvent.click(clearBtn);
    expect(handleClear).toHaveBeenCalled();
  });

  it('disables quick-add pill if staple is already in pantry', () => {
    const handleAdd = vi.fn();
    render(
      <QuickAddPantry
        onAdd={handleAdd}
        currentIngredients={['tomato', 'garlic']}
      />
    );

    const tomatoBtn = screen.getByRole('button', { name: /\+ tomato/i });
    expect(tomatoBtn).toBeDisabled();

    const pastaBtn = screen.getByRole('button', { name: /\+ pasta/i });
    expect(pastaBtn).not.toBeDisabled();

    fireEvent.click(pastaBtn);
    expect(handleAdd).toHaveBeenCalledWith('pasta');
  });
});
