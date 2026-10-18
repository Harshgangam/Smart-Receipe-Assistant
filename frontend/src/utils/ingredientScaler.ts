/**
 * ingredientScaler.ts
 *
 * Scales ingredient quantity strings by a multiplier (e.g., "1 c. milk" -> "2 c. milk" at 2x).
 * Handles whole numbers, decimals, fractions (1/2, 3/4), mixed fractions (1 1/2),
 * and preserves descriptive wording and units cleanly.
 */

function formatNumber(num: number): string {
  // Round to nearest quarter or clean decimal
  const rounded = Math.round(num * 100) / 100;
  // If close to a clean common fraction
  const intPart = Math.floor(rounded);
  const frac = rounded - intPart;

  if (Math.abs(frac - 0.5) < 0.05) {
    return intPart > 0 ? `${intPart} 1/2` : '1/2';
  }
  if (Math.abs(frac - 0.25) < 0.05) {
    return intPart > 0 ? `${intPart} 1/4` : '1/4';
  }
  if (Math.abs(frac - 0.75) < 0.05) {
    return intPart > 0 ? `${intPart} 3/4` : '3/4';
  }
  if (Math.abs(frac - 0.33) < 0.05) {
    return intPart > 0 ? `${intPart} 1/3` : '1/3';
  }
  if (Math.abs(frac - 0.67) < 0.05) {
    return intPart > 0 ? `${intPart} 2/3` : '2/3';
  }

  // If whole number
  if (Number.isInteger(rounded) || frac === 0) {
    return rounded.toString();
  }

  return rounded.toFixed(1).replace(/\.0$/, '');
}

export function scaleIngredient(raw: string, multiplier: number): string {
  if (multiplier === 1 || !raw) return raw;

  // Regex patterns:
  // 1. Mixed fraction: "1 1/2 c. milk"
  const mixedMatch = raw.match(/^(\d+)\s+(\d+)\/(\d+)\s*(.*)$/);
  if (mixedMatch) {
    const whole = parseFloat(mixedMatch[1]);
    const num = parseFloat(mixedMatch[2]);
    const den = parseFloat(mixedMatch[3]);
    const val = (whole + num / den) * multiplier;
    return `${formatNumber(val)} ${mixedMatch[4]}`.trim();
  }

  // 2. Simple fraction: "1/2 cup flour"
  const fracMatch = raw.match(/^(\d+)\/(\d+)\s*(.*)$/);
  if (fracMatch) {
    const num = parseFloat(fracMatch[1]);
    const den = parseFloat(fracMatch[2]);
    const val = (num / den) * multiplier;
    return `${formatNumber(val)} ${fracMatch[3]}`.trim();
  }

  // 3. Decimal or integer at the start: "3 bananas", "18 Tbsp. flour", "1.5 tsp salt"
  const numMatch = raw.match(/^(\d+(?:\.\d+)?)\s*(.*)$/);
  if (numMatch) {
    const val = parseFloat(numMatch[1]) * multiplier;
    return `${formatNumber(val)} ${numMatch[2]}`.trim();
  }

  // If no leading quantity found, return as-is
  return raw;
}
