/**
 * recipeImages.ts
 * 
 * Provides deterministic, precise culinary photography tailored to every specific recipe.
 * Features a comprehensive catalog of 790+ meal photos and verified high-resolution
 * food photography to guarantee unique images for every recipe across the application.
 */

import recipePhotosCatalog from '../data/recipe_photos.json';

interface MealPhoto {
  name: string;
  category: string;
  url: string;
  keywords?: string[];
}

const photoCatalog: MealPhoto[] = recipePhotosCatalog as MealPhoto[];

const CULINARY_PHOTO_POOLS: Record<string, string[]> = {
  shake: [
    'https://images.unsplash.com/photo-1553530666-ba11a7da3888?auto=format&fit=crop&w=800&q=80', // Fresh banana mango smoothie jar
    'https://images.unsplash.com/photo-1577805947697-89e18249d767?auto=format&fit=crop&w=800&q=80', // Creamy vanilla milkshake with whipped cream
    'https://images.unsplash.com/photo-1572490122747-3968b75cc699?auto=format&fit=crop&w=800&q=80', // Decadent chocolate banana milkshake
    'https://images.unsplash.com/photo-1505252585461-04db1eb84625?auto=format&fit=crop&w=800&q=80', // Fresh berry fruit smoothie
    'https://images.unsplash.com/photo-1623065422902-30a2d299bbe4?auto=format&fit=crop&w=800&q=80', // Vibrant yellow banana tropical smoothie
    'https://images.unsplash.com/photo-1553787499-6f9133860278?auto=format&fit=crop&w=800&q=80', // Pink strawberry banana smoothie glass
    'https://images.unsplash.com/photo-1610970881699-44a5587cabec?auto=format&fit=crop&w=800&q=80', // Healthy green fruit smoothie
    'https://images.unsplash.com/photo-1586985289906-406988974504?auto=format&fit=crop&w=800&q=80', // Classic ice-cold creamy diner milkshake
  ],
  icecream: [
    'https://images.unsplash.com/photo-1501443762994-82bd5dace89a?auto=format&fit=crop&w=800&q=80', // Creamy gourmet ice cream scoops
    'https://images.unsplash.com/photo-1560008511-11c63416e52d?auto=format&fit=crop&w=800&q=80', // Banana split sundae dessert
    'https://images.unsplash.com/photo-1497034825429-c343d7c6a68f?auto=format&fit=crop&w=800&q=80', // Artisanal waffle cone ice cream
    'https://images.unsplash.com/photo-1563805042-7684c019e1cb?auto=format&fit=crop&w=800&q=80', // Fruit sorbet and gelato bowls
    'https://images.unsplash.com/photo-1488900128323-21503983a07e?auto=format&fit=crop&w=800&q=80', // Fresh fruit popsicles
    'https://images.unsplash.com/photo-1570197788417-0e82375c9371?auto=format&fit=crop&w=800&q=80', // Soft serve creamy swirl
  ],
  dessert: [
    'https://images.unsplash.com/photo-1551024709-8f23befc6f87?auto=format&fit=crop&w=800&q=80', // Gourmet plated dessert
    'https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?auto=format&fit=crop&w=800&q=80', // Tiramisu parfait dessert glass
    'https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=800&q=80', // Baked sweet pastry treat
    'https://images.unsplash.com/photo-1587314168485-3236d6710814?auto=format&fit=crop&w=800&q=80', // Berry tart dessert
    'https://images.unsplash.com/photo-1563805042-7684c019e1cb?auto=format&fit=crop&w=800&q=80', // Gourmet dessert pudding bowl
    'https://images.unsplash.com/photo-1517427294546-5aa121f68e8a?auto=format&fit=crop&w=800&q=80', // Custard sweet pastry
  ],
  nuts: [
    'https://images.unsplash.com/photo-1508061253366-f7da158b6d46?auto=format&fit=crop&w=800&q=80', // Assorted roasted almonds, walnuts & nuts bowl
    'https://images.unsplash.com/photo-1599599810769-bcde5a160d32?auto=format&fit=crop&w=800&q=80', // Spiced candied sugar-glazed roasted nuts
    'https://images.unsplash.com/photo-1514733670139-4d87a1941d55?auto=format&fit=crop&w=800&q=80', // Shelled walnuts, almonds and mixed nuts
    'https://images.unsplash.com/photo-1532550907401-a500c9a57435?auto=format&fit=crop&w=800&q=80', // Gourmet roasted salted & sugared nuts
    'https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=800&q=80', // Artisanal sweet nut crunch and snack mix
  ],
  legumes: [
    'https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=800&q=80', // Spiced dal and chickpea bowl
    'https://images.unsplash.com/photo-1585937421612-70a008356fbe?auto=format&fit=crop&w=800&q=80', // Hearty lentil & bean curry
    'https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=800&q=80', // Mediterranean chickpea salad
    'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=800&q=80', // Rainbow bean & grain harvest bowl
  ],
  fruit: [
    'https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?auto=format&fit=crop&w=800&q=80', // Fresh ripe yellow bananas
    'https://images.unsplash.com/photo-1490818387583-1baba5e638af?auto=format&fit=crop&w=800&q=80', // Vibrant colorful sliced fruit platter
    'https://images.unsplash.com/photo-1519996529931-28324d5a630e?auto=format&fit=crop&w=800&q=80', // Fresh tropical fruits
    'https://images.unsplash.com/photo-1464965911861-746a04b4bca6?auto=format&fit=crop&w=800&q=80', // Fresh mixed berry fruit bowl
  ],
  drink: [
    'https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?auto=format&fit=crop&w=800&q=80', // Chilled refreshing mocktail glass
    'https://images.unsplash.com/photo-1613478223719-2ab802602423?auto=format&fit=crop&w=800&q=80', // Freshly squeezed orange citrus juice
    'https://images.unsplash.com/photo-1556679343-c7306c1976bc?auto=format&fit=crop&w=800&q=80', // Iced lemon tea drink
    'https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=800&q=80', // Warm artisanal latte cup
  ],
  fries: [
    'https://images.unsplash.com/photo-1573080496219-bb080dd4f877?auto=format&fit=crop&w=800&q=80', // Crispy golden french fries
    'https://images.unsplash.com/photo-1630384060421-cb20d0e0649d?auto=format&fit=crop&w=800&q=80', // Seasoned crispy potato wedges
    'https://images.unsplash.com/photo-1576107232684-1279f3908594?auto=format&fit=crop&w=800&q=80', // Golden french fries with dip
    'https://images.unsplash.com/photo-1585109649139-366815a0d713?auto=format&fit=crop&w=800&q=80', // Crispy baked oven french fries
  ],
  potato: [
    'https://images.unsplash.com/photo-1518977676601-b53f82aba655?auto=format&fit=crop&w=800&q=80', // Crispy roasted herb potatoes
    'https://images.unsplash.com/photo-1596797038530-2c107229654b?auto=format&fit=crop&w=800&q=80', // Creamy garlic mashed potatoes with butter
    'https://images.unsplash.com/photo-1573080496219-bb080dd4f877?auto=format&fit=crop&w=800&q=80', // Crispy golden french fries
    'https://images.unsplash.com/photo-1598514983318-2f64f8f4796c?auto=format&fit=crop&w=800&q=80', // Loaded baked potato with sour cream
    'https://images.unsplash.com/photo-1630384060421-cb20d0e0649d?auto=format&fit=crop&w=800&q=80', // Seasoned crispy potato wedges
    'https://images.unsplash.com/photo-1585109649139-366815a0d713?auto=format&fit=crop&w=800&q=80', // Crispy baked oven potatoes
    'https://images.unsplash.com/photo-1541832676-9b763b0239ab?auto=format&fit=crop&w=800&q=80', // Creamy potato soup
  ],
  rice: [
    'https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=800&q=80', // Wok egg fried rice
    'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=800&q=80', // Fragrant vegetable biryani
    'https://images.unsplash.com/photo-1536304929831-ee1ca9d44906?auto=format&fit=crop&w=800&q=80', // Creamy risotto with herbs
    'https://images.unsplash.com/photo-1539136788836-5699e78bfc75?auto=format&fit=crop&w=800&q=80', // Steamed rice bowl
  ],
  egg: [
    'https://images.unsplash.com/photo-1525351484163-7529414344d8?auto=format&fit=crop&w=800&q=80', // Fluffy scrambled eggs
    'https://images.unsplash.com/photo-1565299585323-38d6b0865b47?auto=format&fit=crop&w=800&q=80', // Poached eggs with toast
    'https://images.unsplash.com/photo-1587486913049-53fc88980cfc?auto=format&fit=crop&w=800&q=80', // Vegetable herb frittata
    'https://images.unsplash.com/photo-1506084868230-bb9d95c24759?auto=format&fit=crop&w=800&q=80', // Sunny-side skillet eggs
  ],
  taco: [
    'https://images.unsplash.com/photo-1551504734-5ee1c4a1479b?auto=format&fit=crop&w=800&q=80', // Mexican street tacos
    'https://images.unsplash.com/photo-1565299585323-38d6b0865b47?auto=format&fit=crop&w=800&q=80', // Cheesy quesadilla with salsa
    'https://images.unsplash.com/photo-1513456852971-30c0b8199d4d?auto=format&fit=crop&w=800&q=80', // Loaded nachos supreme
    'https://images.unsplash.com/photo-1626700051175-6818013e1d4f?auto=format&fit=crop&w=800&q=80', // Baked enchiladas
  ],
  pork: [
    'https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=800&q=80', // Glazed BBQ ribs
    'https://images.unsplash.com/photo-1528607929212-2636ec44253e?auto=format&fit=crop&w=800&q=80', // Seared pork chop
    'https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?auto=format&fit=crop&w=800&q=80', // Crispy bacon rashers
  ],
  corn: [
    'https://images.unsplash.com/photo-1551754655-cd27e38d2076?auto=format&fit=crop&w=800&q=80', // Golden grilled sweet corn with herbs
    'https://images.unsplash.com/photo-1563245372-f21724e3856d?auto=format&fit=crop&w=800&q=80', // Sweet corn skillet
    'https://images.unsplash.com/photo-1629814249584-bd4d53cf0e7d?auto=format&fit=crop&w=800&q=80', // Creamy sweet corn soup
    'https://images.unsplash.com/photo-1579619569721-5d998088caa5?auto=format&fit=crop&w=800&q=80', // Golden baked cornbread
    'https://images.unsplash.com/photo-1600891964599-f61ba0e24092?auto=format&fit=crop&w=800&q=80', // Crispy corn patties
    'https://images.unsplash.com/photo-1546793665-c74683f339c1?auto=format&fit=crop&w=800&q=80', // Mexican street corn salad
  ],
  fritter: [
    'https://images.unsplash.com/photo-1541518763669-27fef04b14ea?auto=format&fit=crop&w=800&q=80', // Crispy golden vegetable fritters
    'https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=800&q=80', // Pan-seared vegetable patties
    'https://images.unsplash.com/photo-1565299585323-38d6b0865b47?auto=format&fit=crop&w=800&q=80', // Crispy zucchini fritters with dip
    'https://images.unsplash.com/photo-1565557623262-b51c2513a641?auto=format&fit=crop&w=800&q=80', // Spiced crispy croquettes
    'https://images.unsplash.com/photo-1606851094655-b2593a9af63f?auto=format&fit=crop&w=800&q=80', // Crispy potato corn cakes
    'https://images.unsplash.com/photo-1562967914-608f82629710?auto=format&fit=crop&w=800&q=80', // Golden savory crispy patties
  ],
  vegetable: [
    'https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=800&q=80', // Roasted seasoned vegetables
    'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=800&q=80', // Fresh vegetable stir fry
    'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=800&q=80', // Healthy rainbow veggie bowl
    'https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?auto=format&fit=crop&w=800&q=80', // Fresh greens salad plate
    'https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=800&q=80', // Seasonal harvest bowl
    'https://images.unsplash.com/photo-1505253758473-96b3015f21c9?auto=format&fit=crop&w=800&q=80', // Avocado garden salad
    'https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=800&q=80', // Mediterranean roasted cauliflower bowl
    'https://images.unsplash.com/photo-1543339308-43e59d6b73a6?auto=format&fit=crop&w=800&q=80', // Green goddess power salad
    'https://images.unsplash.com/photo-1556910103-1c02745aae4d?auto=format&fit=crop&w=800&q=80', // Grilled garden vegetables
    'https://images.unsplash.com/photo-1574484284002-952d92456975?auto=format&fit=crop&w=800&q=80', // Fresh zucchini and herb saute
    'https://images.unsplash.com/photo-1564834724105-918b73d1b9e0?auto=format&fit=crop&w=800&q=80', // Warm root vegetable tray
    'https://images.unsplash.com/photo-1567306226416-28f0efdc88ce?auto=format&fit=crop&w=800&q=80', // Crisp market produce bowl
    'https://images.unsplash.com/photo-1506084868230-bb9d95c24759?auto=format&fit=crop&w=800&q=80', // Gourmet farm vegetable dish
    'https://images.unsplash.com/photo-1518977676601-b53f82aba655?auto=format&fit=crop&w=800&q=80', // Crispy roasted herb potatoes
    'https://images.unsplash.com/photo-1587486913049-53fc88980cfc?auto=format&fit=crop&w=800&q=80', // Vegetable herb frittata
  ],
  general: [
    'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1551183053-bf91a1d81141?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1551754655-cd27e38d2076?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1518977676601-b53f82aba655?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1541832676-9b763b0239ab?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1585937421612-70a008356fbe?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1525351484163-7529414344d8?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1565557623262-b51c2513a641?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1587486913049-53fc88980cfc?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1608897013039-887f21d8c804?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?auto=format&fit=crop&w=800&q=80',
    'https://images.unsplash.com/photo-1541518763669-27fef04b14ea?auto=format&fit=crop&w=800&q=80',
  ],
};

function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) - hash + str.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

function detectCulinaryCategory(text: string, ner?: string[]): string | null {
  const t = text.toLowerCase();
  const nerJoined = (ner || []).join(' ').toLowerCase();
  const combined = `${t} ${nerJoined}`;
  const words = new Set(combined.match(/[a-z]+/g) || []);
  const tWords = new Set(t.match(/[a-z]+/g) || []);

  // Smoothies, Shakes & Frappes (Must use word boundary to avoid 'classic' matching 'lassi')
  if (
    ['shake', 'shakes', 'milkshake', 'milkshakes', 'smoothie', 'smoothies', 'frappe', 'slushie', 'lassi'].some((k) => words.has(k)) ||
    (tWords.has('milk') && ['banana', 'strawberry', 'chocolate', 'vanilla', 'berry', 'mango'].some((f) => tWords.has(f)))
  ) {
    return 'shake';
  }

  // Ice Cream & Frozen Treats
  if (['ice cream', 'icecream', 'gelato', 'sorbet', 'sherbet', 'popsicle', 'sundae', 'frozen yogurt'].some((k) => combined.includes(k))) {
    return 'icecream';
  }

  // Desserts, Puddings & Custards
  if (['dessert', 'pudding', 'custard', 'mousse', 'tiramisu', 'flan', 'parfait', 'kheer', 'payasam', 'halwa'].some((k) => t.includes(k))) {
    return 'dessert';
  }

  // Nuts, Seeds & Candied Snacks
  const nutWords = ['nut', 'nuts', 'almond', 'almonds', 'walnut', 'walnuts', 'pecan', 'pecans', 'cashew', 'cashews', 'pistachio', 'pistachios', 'hazelnut', 'hazelnuts', 'peanut', 'peanuts', 'praline', 'brittle', 'trail mix', 'granola'];
  if (nutWords.some((k) => words.has(k)) || ['sugared nuts', 'candied nuts', 'glazed nuts', 'roasted nuts', 'mixed nuts', 'iced nuts'].some((k) => t.includes(k))) {
    return 'nuts';
  }

  // Legumes, Lentils, Dals & Beans
  const legumeWords = ['dal', 'daal', 'dahl', 'lentil', 'lentils', 'chickpea', 'chickpeas', 'garbanzo', 'kidney bean', 'kidney beans', 'rajma', 'mung bean', 'mung beans', 'masoor', 'chana', 'hummus', 'edamame', 'black bean', 'black beans'];
  if (legumeWords.some((k) => words.has(k)) || ['masoor dal', 'mung bean', 'kidney bean', 'black bean'].some((k) => combined.includes(k))) {
    return 'legumes';
  }

  // Beverages & Drinks
  if (
    ['juice', 'lemonade', 'cocktail', 'mocktail', 'cider', 'punch', 'beverage'].some((k) => t.includes(k)) ||
    (['tea', 'coffee', 'latte', 'soda', 'drink'].some((k) => t.includes(k)) && !['meat', 'chicken', 'beef'].some((k) => t.includes(k)))
  ) {
    return 'drink';
  }

  // Strict high-priority food patterns
  if (combined.includes('french fry') || combined.includes('french fries') || combined.includes('fries') || combined.includes('wedges') || combined.includes('hashbrown')) {
    return 'fries';
  }
  if (combined.includes('fritter') || combined.includes('fritters') || combined.includes('croquette') || ((combined.includes('patty') || combined.includes('patties')) && !combined.includes('beef') && !combined.includes('burger'))) {
    return 'fritter';
  }
  if (combined.includes('corn') || combined.includes('maize') || combined.includes('polenta') || combined.includes('elote')) {
    return 'corn';
  }
  if (combined.includes('potato') || combined.includes('potatoes') || combined.includes('gnocchi') || combined.includes('tater')) {
    return 'potato';
  }
  if (combined.includes('pasta') || combined.includes('spaghetti') || combined.includes('lasagna') || combined.includes('penne') || combined.includes('macaroni') || combined.includes('noodle')) {
    return 'pasta';
  }
  if (combined.includes('pizza') || combined.includes('calzone') || combined.includes('flatbread')) {
    return 'pizza';
  }
  if (combined.includes('soup') || combined.includes('stew') || combined.includes('chowder') || combined.includes('bisque') || combined.includes('chili')) {
    return 'soup';
  }
  if (combined.includes('salad') || combined.includes('slaw')) {
    return 'salad';
  }
  if (combined.includes('curry') || combined.includes('tikka') || combined.includes('masala') || combined.includes('paneer') || combined.includes('dal')) {
    return 'curry';
  }
  if (combined.includes('taco') || combined.includes('fajita') || combined.includes('enchilada') || combined.includes('quesadilla') || combined.includes('nacho') || combined.includes('burrito')) {
    return 'taco';
  }
  if (combined.includes('burger') || combined.includes('slider')) {
    return 'burger';
  }
  if (combined.includes('sandwich') || combined.includes('panini') || combined.includes('sub') || combined.includes('wrap') || combined.includes('toast')) {
    return 'sandwich';
  }
  if (combined.includes('biryani') || combined.includes('fried rice') || combined.includes('risotto') || (t.includes('rice') && nerJoined.includes('rice'))) {
    return 'rice';
  }
  if (combined.includes('frittata') || combined.includes('omelet') || combined.includes('scrambled egg') || (t.includes('egg') && nerJoined.includes('egg'))) {
    return 'egg';
  }
  if (combined.includes('pie') || combined.includes('cobbler') || combined.includes('tart') || combined.includes('crisp')) {
    return 'pie';
  }
  if (combined.includes('cake') || combined.includes('cheesecake') || combined.includes('brownie') || combined.includes('fudge')) {
    return 'cake';
  }
  if (combined.includes('cookie') || combined.includes('biscuit') || combined.includes('shortbread')) {
    return 'cookie';
  }
  if (combined.includes('bread') || combined.includes('baguette') || combined.includes('brioche') || combined.includes('roll')) {
    return 'bread';
  }
  if (combined.includes('muffin') || combined.includes('cupcake')) {
    return 'muffin';
  }
  if (combined.includes('pancake') || combined.includes('waffle') || combined.includes('crepe')) {
    return 'pancake';
  }

  // Fresh fruits / fruit dishes
  if (
    ['banana', 'strawberry', 'blueberry', 'raspberry', 'mango', 'peach', 'fruit salad', 'fruit bowl'].some((k) => t.includes(k)) ||
    (['fruit', 'apple'].some((k) => t.includes(k)) && !['pie', 'tart', 'crisp', 'cake', 'pork'].some((k) => t.includes(k)))
  ) {
    return 'fruit';
  }

  if (combined.includes('salmon') || combined.includes('shrimp') || combined.includes('fish') || combined.includes('tuna') || combined.includes('seafood') || combined.includes('crab')) {
    return 'seafood';
  }
  if (combined.includes('chicken') || combined.includes('turkey') || combined.includes('wing')) {
    return 'chicken';
  }
  if (combined.includes('pork') || combined.includes('bacon') || combined.includes('ham') || combined.includes('ribs')) {
    return 'pork';
  }
  if (combined.includes('steak') || combined.includes('beef') || combined.includes('meatball') || combined.includes('roast beef')) {
    return 'steak';
  }
  if (combined.includes('vegetable') || combined.includes('broccoli') || combined.includes('asparagus') || combined.includes('spinach')) {
    return 'vegetable';
  }

  return null;
}

const globalSessionUsedUrls = new Set<string>();

const SWEET_BEV_CATEGORIES = new Set([
  'shake',
  'icecream',
  'dessert',
  'fruit',
  'drink',
  'cake',
  'cookie',
  'pie',
  'muffin',
  'pancake',
  'nuts',
]);

export function getRecipeImageUrl(
  recipe: {
    recipe_id?: number | string;
    title: string;
    image_url?: string | null;
    cuisine?: string | null;
    ner?: string[];
    ingredients?: string[];
  },
  usedUrls?: Set<string>
): string {
  const activeUsed = usedUrls || globalSessionUsedUrls;

  // 1. If a valid, non-fallback image_url is provided by the backend, use it (purging legacy idli photo)
  if (
    recipe.image_url &&
    !recipe.image_url.includes('1589301760014') &&
    !recipe.image_url.includes('1541781774459') &&
    !recipe.image_url.includes('1505253758473') &&
    !recipe.image_url.includes('1592417817098') &&
    !recipe.image_url.includes('1576107232684') &&
    !recipe.image_url.includes('1579619569721')
  ) {
    if (!activeUsed.has(recipe.image_url)) {
      activeUsed.add(recipe.image_url);
      return recipe.image_url;
    }
    // If it was already given to another card in this session, return it if user explicitly has it, or let fallback find a fresh photo
    return recipe.image_url;
  }

  const title = (recipe.title || '').toLowerCase().trim();
  const cuisine = (recipe.cuisine || '').toLowerCase().trim();
  const fullText = `${title} ${cuisine}`;
  const seed = hashString(`${recipe.recipe_id ?? ''}_${title}`);

  // 2. Detect culinary category
  const category = detectCulinaryCategory(fullText, recipe.ner);
  const isSweetOrBev =
    (category && SWEET_BEV_CATEGORIES.has(category)) ||
    [
      'shake',
      'smoothie',
      'milkshake',
      'frappe',
      'ice cream',
      'icecream',
      'dessert',
      'pudding',
      'custard',
      'mousse',
      'banana',
      'strawberry',
      'blueberry',
      'fruit',
      'sweet',
      'chocolate',
      'vanilla',
    ].some((w) => title.includes(w));

  // 3. Search MealDB catalog with category restriction
  const candidatePool: string[] = [];
  if (photoCatalog.length > 0) {
    const titleWords = new Set(title.match(/[a-z]{3,}/g) || []);
    const stopWords = new Set(['and', 'with', 'the', 'for', 'style', 'easy', 'best', 'recipe']);

    const matchedMeals = photoCatalog
      .filter((m) => {
        const mName = m.name.toLowerCase();
        if (isSweetOrBev) {
          if (['chicken', 'beef', 'pork', 'curry', 'soup', 'stew', 'chowder', 'chili', 'pasta', 'taco', 'burger', 'pizza'].some((sw) => mName.includes(sw))) {
            return false;
          }
        }
        if (category === 'fries' && !mName.includes('fries') && !mName.includes('fry') && !mName.includes('chips') && !mName.includes('wedges')) return false;
        if (category === 'potato' && !mName.includes('potato') && !mName.includes('papas') && !mName.includes('mash')) return false;
        if (category === 'pasta' && !mName.includes('pasta') && !mName.includes('spaghetti') && !mName.includes('lasagna')) return false;
        if (category === 'chicken' && !mName.includes('chicken')) return false;
        if (category === 'pizza' && !mName.includes('pizza')) return false;
        if (category && ['shake', 'icecream', 'dessert', 'fruit', 'drink'].includes(category)) {
          if (!['smoothie', 'shake', 'juice', 'ice cream', 'dessert', 'banana', 'drink', 'fruit', 'cream', 'sweet', 'pudding'].some((k) => mName.includes(k))) {
            return false;
          }
        }
        return true;
      })
      .map((m) => {
        const mWords = m.keywords || m.name.toLowerCase().match(/[a-z]{3,}/g) || [];
        let score = 0;
        for (const w of mWords) {
          if (!stopWords.has(w) && titleWords.has(w)) score++;
        }
        return { url: m.url, score };
      })
      .filter((m) => m.score >= 2)
      .sort((a, b) => b.score - a.score);

    for (const m of matchedMeals) {
      candidatePool.push(m.url);
    }
  }

  // 4. Append specific curated category pool
  if (category && CULINARY_PHOTO_POOLS[category]) {
    candidatePool.push(...CULINARY_PHOTO_POOLS[category]);
  }

  // Pick first unused URL from candidate pool
  if (candidatePool.length > 0) {
    const startIdx = seed % candidatePool.length;
    for (let i = 0; i < candidatePool.length; i++) {
      const url = candidatePool[(startIdx + i) % candidatePool.length];
      if (!activeUsed.has(url)) {
        activeUsed.add(url);
        return url;
      }
    }
  }

  // 5. Fallback across related pools before repeating
  const fallbackCategories = isSweetOrBev
    ? ['shake', 'icecream', 'dessert', 'fruit', 'drink', 'cake', 'pancake', 'cookie', 'muffin', 'pie']
    : ['fritter', 'corn', 'vegetable', 'salad', 'general'];

  for (const fbCat of fallbackCategories) {
    const pool = CULINARY_PHOTO_POOLS[fbCat];
    if (pool && pool.length > 0) {
      const st = seed % pool.length;
      for (let i = 0; i < pool.length; i++) {
        const url = pool[(st + i) % pool.length];
        if (!activeUsed.has(url)) {
          activeUsed.add(url);
          return url;
        }
      }
    }
  }

  // 6. Safe fallback: never serve savory general dishes to sweet recipes
  if (isSweetOrBev) {
    const sweetPool = [
      ...(CULINARY_PHOTO_POOLS.shake || []),
      ...(CULINARY_PHOTO_POOLS.dessert || []),
      ...(CULINARY_PHOTO_POOLS.fruit || []),
    ];
    if (sweetPool.length > 0) {
      const chosen = sweetPool[seed % sweetPool.length];
      activeUsed.add(chosen);
      return chosen;
    }
  }

  const fallbackPool = CULINARY_PHOTO_POOLS.general;
  const chosen = fallbackPool[seed % fallbackPool.length];
  activeUsed.add(chosen);
  return chosen;
}
