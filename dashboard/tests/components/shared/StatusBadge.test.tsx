import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { AdlStatus } from '@/api/types';

describe('StatusBadge', () => {
  it('renders provisional status with yellow emoji and color', () => {
    render(<StatusBadge status="provisional" />);
    
    // Check for emoji 🟡
    expect(screen.getByText(/🟡/)).toBeInTheDocument();
    expect(screen.getByText(/provisional/i)).toBeInTheDocument();
    // Chip should have warning color
    const chip = document.querySelector('.MuiChip-colorWarning');
    expect(chip).toBeInTheDocument();
  });

  it('renders validated status with green emoji and color', () => {
    render(<StatusBadge status="validated" />);
    
    // Check for emoji 🟢
    expect(screen.getByText(/🟢/)).toBeInTheDocument();
    expect(screen.getByText(/validated/i)).toBeInTheDocument();
    // Chip should have success color
    const chip = document.querySelector('.MuiChip-colorSuccess');
    expect(chip).toBeInTheDocument();
  });

  it('renders deprecated status with red emoji and color', () => {
    render(<StatusBadge status="deprecated" />);
    
    // Check for emoji 🔴
    expect(screen.getByText(/🔴/)).toBeInTheDocument();
    expect(screen.getByText(/deprecated/i)).toBeInTheDocument();
    // Chip should have error color
    const chip = document.querySelector('.MuiChip-colorError');
    expect(chip).toBeInTheDocument();
  });

  it('renders forked status with blue emoji and color', () => {
    render(<StatusBadge status="forked" />);
    
    // Check for emoji 🔵
    expect(screen.getByText(/🔵/)).toBeInTheDocument();
    expect(screen.getByText(/forked/i)).toBeInTheDocument();
    // Chip should have info color
    const chip = document.querySelector('.MuiChip-colorInfo');
    expect(chip).toBeInTheDocument();
  });

  it('renders archived status with white emoji and default color', () => {
    render(<StatusBadge status="archived" />);
    
    // Check for emoji ⚪
    expect(screen.getByText(/⚪/)).toBeInTheDocument();
    expect(screen.getByText(/archived/i)).toBeInTheDocument();
  });

  it('applies status-badge classname', () => {
    const { container } = render(<StatusBadge status="validated" />);
    
    const chip = container.querySelector('.status-badge');
    expect(chip).toBeInTheDocument();
  });
});
