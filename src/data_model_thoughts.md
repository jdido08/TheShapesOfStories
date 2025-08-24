# Data Model Considerations


# Products
- Products have default fields title, description, etc.. 
- you can add new attributes/fields called product metafields 
- need to distinquish between shopify product AND printify product
- for me: it makes sense to have products at this level: [story-title]-[protagonist]-[medium] e.g. the-great-gatbsy-jay-gatsby-print, romeo-&-juliet-romeo-mug
- variants for me right now should be like size (e.g. 8x10, 11x14, etc..)
- each variant get's it's own SKU from printify -- those things need to match 

# Product Metafields
story.slug (single line text): the-great-gatsby
story.title (text)
story.author (text)
story.character (text): “Jay Gatsby”
story.series (text, optional)
story.universe (text, optional)
story.genre (list of single line text)
story.subgenre (list of single line text)
story.publication_year (integer)
story.publication_country (single line text)
story.setting_era (text)
story.setting_time (text, e.g., “summer 1922”)
story.setting_city (list)
story.setting_region (list)
story.setting_country (list)
story.language (text)
story.awards (list)

design.medium (single select): print | canvas | t-shirt | mug | …
design.line_type (single select): line | text ← (fixes your shape_tupe typo)
design.bg_hex (color)
design.bg_name (text, e.g., “Navy”)
design.font_family (text)
design.font_color_hex (color)
design.font_color_name (text)

shapes.archetype (single select enum; e.g., Man in Hole, Icarus, Cinderella, Boy Meets Girl, etc.)
shapes.symbols (text; e.g., ↑↓→)

printify.product_id


Variant metafields (per Shopify variant)
printify.blueprint_id (number)
printify.provider_id (number)
printify.variant_id (number)
printify.sku (text)
(You’ll also keep normal Shopify variant sku, price, etc.)

# Metaobjects --> objects that you can create yourself
- beneifical if you want dedicated landing pages e.g. good for sharing, links, SEO, etc.. but becaue I'm only starting to sell 8x10 prints it's not worth while for me to do this yet 
- I should consider for:
    - stories -- when there's multiple products per story (e.g. print, canvas, t-shirt, etc..) and/or characters (e.g. romeo, juliet)
    - authors | directors | teams -- easy grouping and you can have dedicated pages for them 
    - groups 
        - American Authors
        - NFL 
        - etc.. 


_______________

* **story\_slug** (metaobject or metafield): `the-great-gatsby`
* **character\_slug** (metafield): `jay-gatsby` (use `main` if there’s only one)
* **product handle**: `{story_slug}-{character_slug}-{medium}`
  e.g., `the-great-gatsby-jay-gatsby-print`, `romeo-and-juliet-romeo-t-shirt`

### Shopify Product (one per medium *and* character)

* **title**: “The Great Gatsby — Print (Jay Gatsby)”
* **description**: rich HTML
* **tags**: only campaign/fuzzy stuff (e.g., `bestseller`, `banned-books`, `giftable`)

### Product metafields (typed)

Use namespaces to keep things tidy:

**`story.*`**

* `story.slug` (single line text): `the-great-gatsby`
* `story.title` (text)
* `story.author` (text)
* `story.character` (text): “Jay Gatsby”
* `story.series` (text, optional)
* `story.universe` (text, optional)
* `story.genre` (list of single line text)
* `story.subgenre` (list of single line text)
* `story.publication_year` (integer)
* `story.publication_country` (single line text)
* `story.setting_era` (text)
* `story.setting_time` (text, e.g., “summer 1922”)
* `story.setting_city` (list)
* `story.setting_region` (list)
* `story.setting_country` (list)
* `story.language` (text)
* `story.awards` (list)

**`design.*`**

* `design.medium` (single select): `print | canvas | t-shirt | mug | …`
* `design.line_type` (single select): `line | text`  ← (fixes your `shape_tupe` typo)
* `design.bg_hex` (color)
* `design.bg_name` (text, e.g., “Navy”)
* `design.font_family` (text)
* `design.font_color_hex` (color)
* `design.font_color_name` (text)

**`shapes.*`** *(per character design, not global story)*

* `shapes.archetype` (single select enum; e.g., Man in Hole, Icarus, Cinderella, Boy Meets Girl, etc.)
* `shapes.symbols` (text; e.g., `↑↓→`)

**`printify.*`** *(variant mapping lives on the variant; see below, but you can also mirror at product if helpful)*

* `printify.product_id` (text, optional)

**Optional**

* `compliance.rights_status` (single select: `public_domain | fair_use_risk | licensed`)

### Variants

* **Prints/Canvas:** Option = `Size` (e.g., 8×10, 11×14, 18×24, 24×36).
* **T-Shirts:** Options = `Size`, `Color` (keep colors tight to avoid variant bloat).
* **Don’t use “Character” as an option**—that’s a separate product.

**Variant metafields (per Shopify variant)**
**`printify.*`**

* `printify.blueprint_id` (number)
* `printify.provider_id` (number)
* `printify.variant_id` (number)
* `printify.sku` (text)
  (You’ll also keep normal Shopify variant `sku`, `price`, etc.)

---

## Notes on fields you proposed



## Example (Great Gatsby — Print, Jay Gatsby)

**Product**

* handle: `the-great-gatsby-jay-gatsby-print`
* options: `Size` = 8×10, 18×24, 24×36
* tags: `bestseller`, `classroom`, `giftable`

**Metafields**

* `story.slug`: `the-great-gatsby`
* `story.title`: “The Great Gatsby”
* `story.author`: “F. Scott Fitzgerald”
* `story.character`: “Jay Gatsby”
* `story.genre`: `[ "Classics" ]`
* `story.publication_year`: `1925`
* `story.setting_city`: `[ "Long Island", "New York City" ]`
* `design.medium`: `print`
* `design.line_type`: `text`
* `design.bg_hex`: `#0A1F3B`
* `design.font_family`: `Baskerville`
* `design.font_color_hex`: `#F5E6D3`
* `shapes.archetype`: `Icarus`
* `shapes.symbols`: `↑↓`

**Variant (8×10)**

* Shopify `sku`: `GAT-PRT-8x10-JG-NVY-TXT`
* `printify.blueprint_id`: `XXXXX`
* `printify.provider_id`: `YYYYY`
* `printify.variant_id`: `ZZZZZ`
* `printify.sku`: `PRINTIFY-SKU-12345`

---

