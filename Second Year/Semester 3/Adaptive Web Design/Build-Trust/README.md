# TRUST – Interactive Case Study

A single-page experience exploring the mechanics of digital trust through narrative, visuals, and an interactive micro-experiment. The project mixes research notes, curated imagery, and a pace-sensitive interaction that highlights how trust grows slowly but can collapse instantly when rushed.

You can explore the full interactive experience here:
**https://cristina-trust.iakab.ro**

## Features
- **Story-first layout** – Sections cover the core definition, personal reflections, external voices, visual metaphors, and counterfactual scenarios.
- **Warm, molten palette** – The beige and gold color system supports the “molten signal” metaphor, framing trust as something tempered over time.
- **Accessible semantics** – Skip links, proper landmarks, keyboard focus styles, descriptive alt text, and hover/focus parity for flip cards ensure an inclusive read.
- **Responsive cards & imagery** – Quotes, scenario flips, and visual tiles reflow from single column to grid without losing hierarchy.
- **Interactive trust meter** – A patience-based mini game reinforces the lesson that trust demands steady, intentional effort.

## Project Structure

```
Adaptive Web Design/Seminars/Project/
├── images/          # Project imagery (molten banner, research visuals, etc.)
├── index.html       # Markup for the entire case study
├── style.css        # All visual styling (root palette, layout, components)
├── script.js        # Scroll-reset helper + trust meter interaction logic
└── README.md        # This document
```

## Getting Started
1. **Clone or download** the folder.
2. **Open `index.html`** in any modern browser. No build tools or external dependencies are required.
3. Optionally serve the page with a local server (e.g. `python3 -m http.server`) for consistent asset loading across browsers.

## Customising the Experience
- **Colors & typography** – Adjust CSS variables in `style.css` under the `:root` declaration. Light-mode overrides live inside the `@media (prefers-color-scheme: light)` block.
- **Imagery** – Swap the assets inside `images/`. Each tile uses `object-fit: cover`, so replacement photos are best cropped to landscape proportions.
- **Section content** – Edit the relevant HTML `<section>` blocks to change copy, voices, or visual captions.
- **Trust experiment behaviour** – Tweak constants in `script.js`:
  - `increment` controls how much the bar fills per deliberate tap.
  - `penaltyWindow` (milliseconds) defines how fast is “too fast” before the bar resets.
  - `threshold` sets the completion percentage required to trigger the celebration.

## Accessibility Notes
- Focus styles are high contrast and consistent on links, buttons, and interactive cards.
- Flip cards expose their content on both hover and keyboard focus (using `tabindex="0"`), and each card includes an `aria-label` describing the concept.
- The experiment’s progress bar carries `role="progressbar"` with live updates announced via `aria-live` regions.
- Keyboard users can bypass navigation using the “Skip to content” link at the top of the document.

## Credits & License
- **Author:** Ana-Maria Cristina Hognogi
- **Concept & build:** Adaptive Web Design – Trust research study
- **License:** MIT (feel free to remix with credit)

Enjoy exploring—and remember to build trust one calm step at a time.