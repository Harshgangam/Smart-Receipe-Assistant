/**
 * Frontend semantic food normalization utilities.
 * Ensures terms like "4 potatoes", "potatoes", and "potato" are recognized
 * as the same core food concept, preventing duplicate entries and enabling
 * semantic matching in UI components.
 */

const QUANTITY_AND_UNITS_REGEX = /^(?:(?:\d+(?:\.\d+)?|\d+\/\d+|\d+-\d+)\s*)?(?:(?:cup|cups|tbsp|tablespoon|tablespoons|tsp|teaspoon|teaspoons|oz|ounce|ounces|lb|lbs|pound|pounds|gram|grams|g|kg|ml|l|clove|cloves|can|cans|slice|slices|piece|pieces|head|heads|bunch|bunches|pinch|pinches|stalk|stalks|dash|package|packages|pkg|bag|bags)\s+(?:of\s+)?)?/i;

const MODIFIERS_REGEX = /\b(?:fresh|freshly|ground|diced|chopped|minced|sliced|peeled|cooked|raw|crushed|grated|shredded|whole|frozen|dry|dried|roasted|baked|boiled|organic|large|medium|small|warm|cold|hot|boneless|skinless|lean)\b/gi;

const COMMON_SYNONYMS: Record<string, string> = {
  'scallion': 'scallion',
  'scallions': 'scallion',
  'green onion': 'scallion',
  'green onions': 'scallion',
  'spring onion': 'scallion',
  'spring onions': 'scallion',
  'cilantro': 'coriander',
  'coriander leaves': 'coriander',
  'coriander': 'coriander',
  'bell pepper': 'bell pepper',
  'capsicum': 'bell pepper',
  'sweet pepper': 'bell pepper',
  'sweet potato': 'sweet potato',
  'sweet potatoes': 'sweet potato',
  'russet potato': 'potato',
  'russet potatoes': 'potato',
  'red potato': 'potato',
  'red potatoes': 'potato',
  'baby potato': 'potato',
  'baby potatoes': 'potato',
  'idaho potato': 'potato',
  'idaho potatoes': 'potato',
  'potatoes': 'potato',
  'potato': 'potato',
  'eggplant': 'eggplant',
  'aubergine': 'eggplant',
  'zucchini': 'zucchini',
  'courgette': 'zucchini',
};

/**
 * Strips quantities, units, and prep modifiers to extract the core ingredient name.
 * e.g., "4 potatoes" -> "potato"
 *       "2 large russet potatoes" -> "potato"
 *       "1 cup diced tomatoes" -> "tomato"
 */
export function extractCoreFood(raw: string): string {
  if (!raw) return '';
  let clean = raw.toLowerCase().trim();

  // Strip parenthetical notes like "(peeled)" or "(optional)"
  clean = clean.replace(/\([^)]*\)/g, ' ').trim();

  // Strip clauses after commas or semicolons (e.g. '4 medium potatoes, peeled and cut into 1/2-inch strips')
  if (clean.includes(',')) {
    clean = clean.split(',')[0].trim();
  }
  if (clean.includes(';')) {
    clean = clean.split(';')[0].trim();
  }

  // Strip leading quantities and units
  clean = clean.replace(QUANTITY_AND_UNITS_REGEX, '').trim();

  // Strip prep modifiers
  clean = clean.replace(MODIFIERS_REGEX, ' ').trim();
  clean = clean.replace(/\s+/g, ' ');

  // Direct synonym mapping
  if (COMMON_SYNONYMS[clean]) {
    return COMMON_SYNONYMS[clean];
  }

  // Singularize standard endings
  if (clean.endsWith('potatoes')) return clean.replace(/potatoes$/, 'potato');
  if (clean.endsWith('tomatoes')) return clean.replace(/tomatoes$/, 'tomato');
  if (clean.endsWith('ies') && clean.length > 4) return clean.slice(0, -3) + 'y';
  if (clean.endsWith('es') && (clean.endsWith('shes') || clean.endsWith('ches') || clean.endsWith('xes') || clean.endsWith('sses'))) {
    return clean.slice(0, -2);
  }
  if (clean.endsWith('s') && !clean.endsWith('ss') && clean.length > 3) {
    return clean.slice(0, -1);
  }

  return clean;
}

/**
 * Checks if two ingredient names represent the same semantic food concept.
 * e.g. isSameFood("4 potatoes", "potatoes") === true
 *      isSameFood("green onions", "scallion") === true
 */
export function isSameFood(a: string, b: string): boolean {
  if (!a || !b) return false;
  const coreA = extractCoreFood(a);
  const coreB = extractCoreFood(b);
  if (!coreA || !coreB) return false;
  if (coreA === coreB) return true;

  // Check synonym map
  const synA = COMMON_SYNONYMS[coreA] || coreA;
  const synB = COMMON_SYNONYMS[coreB] || coreB;
  return synA === synB;
}
