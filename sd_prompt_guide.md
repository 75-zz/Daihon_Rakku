# Stable Diffusion Prompt Engineering Guide

This guide provides comprehensive instructions for creating effective Stable Diffusion prompts for CG generation.

---

## Prompt Structure

### Basic Structure
```
[Subject] + [Style/Medium] + [Composition] + [Lighting] + [Environment] + [Details] + [Quality Tags]
```

### Three Core Elements
1. **Subject** - What you want to generate (start here, most important)
2. **Style** - The medium or aesthetic (how it should look)
3. **Context** - Details about actions, setting, and mood

### Priority Order
AI models focus on keywords at the **start** of a prompt. Place the most important elements first.

---

## Weight Syntax

### Basic Notation
| Format | Effect | Multiplier |
|--------|--------|------------|
| `(word)` | Slight increase | 1.1x |
| `((word))` | Moderate increase | 1.21x |
| `(((word)))` | Strong increase | 1.33x |
| `(word:1.5)` | Custom increase | 1.5x |
| `(word:0.7)` | Decrease | 0.7x |
| `word+` | Increase | 1.1x |
| `word++` | More increase | 1.21x |
| `word-` | Decrease | 0.9x |

### Best Practices
- **Useful range**: 0.5 to 1.5
- **Max recommended**: 1.4 (higher risks quality degradation)
- **No spaces**: `horse++` not `horse ++`
- **Multi-word phrases**: Use parentheses `(blue eyes:1.3)`
- **Nesting**: `(holding (a beer:1.3):1.1)` - inner weights multiply by outer

### Examples
```
# Emphasize specific features
(large_breasts:1.3), (ahegao:1.4), (cum_on_face:1.2)

# De-emphasize elements
(background:0.7), (clothing:0.5)

# Complex weighting
((masterpiece)), (best_quality:1.2), (detailed:1.1)
```

---

## Quality Tags

### Essential Quality Boosters
```
masterpiece, best_quality, highres, absurdres, incredibly_absurdres
ultra_detailed, intricate_details, 8k, high_resolution
official_art, professional, perfect_lighting
```

### Anime/Illustration Style
```
anime, anime_style, illustration, digital_art
cel_shading, flat_color, vibrant_colors
detailed_face, detailed_eyes, beautiful_detailed_eyes
```

### Realistic/Photo Style
```
photorealistic, realistic, photo, photograph
RAW photo, DSLR, cinematic, film_grain
depth_of_field, bokeh, sharp_focus
```

### NSFW Quality
```
explicit, nsfw, uncensored
detailed_genitalia, anatomically_correct
```

---

## SD 1.5 vs SDXL Differences

### SD 1.5
- Prefers **keyword-driven** prompts (tags, bullet points)
- Better with Danbooru-style tags
- Max 75 tokens (~350 characters)
- Example: `1girl, long_hair, blue_eyes, nude, large_breasts, masterpiece`

### SDXL
- Prefers **natural language** prompts (full sentences)
- More sensitive to keyword weights
- Better prompt adherence
- Don't go higher than 1.4 for weights
- Example: `A beautiful woman with long flowing hair and blue eyes, nude, with large breasts, masterpiece quality`

### Recommendation for This Project
Use **Danbooru tag format** (SD 1.5 style) for consistency with anime models:
```
1girl, mature_female, office_lady, large_breasts, nude, ahegao, sex, vaginal, from_behind, masterpiece, best_quality
```

---

## Negative Prompts

### Universal Quality Negatives
```
worst_quality, low_quality, normal_quality, lowres, low_res
blurry, jpeg_artifacts, compression_artifacts
pixelated, grainy, noisy, distortion
text, watermark, signature, username
```

### Anatomical Negatives
```
bad_anatomy, bad_proportions, gross_proportions
malformed_limbs, missing_limbs, extra_limbs
mutated_hands, poorly_drawn_hands, bad_hands
extra_fingers, missing_fingers, fused_fingers
extra_arms, extra_legs, fewer_digits
poorly_drawn_face, bad_face, ugly_face
asymmetrical_face, deformed
```

### Style-Specific Negatives

**For Anime:**
```
realistic, photo, photograph, 3d, 3d_render
cgi, unreal_engine, western_cartoon
```

**For Realistic:**
```
cartoon, anime, illustration, drawing
cgi, 3d_render, artwork
```

### NSFW-Specific Negatives
```
censored, mosaic_censoring, bar_censor
loli, shota, child, underage, minor
```

### Complete Recommended Negative Prompt
```
worst_quality, low_quality, lowres, bad_anatomy, bad_hands,
missing_fingers, extra_fingers, mutated_hands, poorly_drawn_face,
ugly, deformed, blurry, text, watermark, signature,
censored, mosaic_censoring, loli, shota, child
```

---

## Composition & Camera

### Camera Angles
```
from_above, from_below, from_behind, from_side
dutch_angle, tilted_frame
straight-on, eye_level
bird's_eye_view, worm's_eye_view
```

### Shot Types
```
close-up, extreme_close-up, face_focus
portrait, upper_body, cowboy_shot
full_body, wide_shot, very_wide_shot
```

### Perspective
```
pov, first_person_view
looking_at_viewer, eye_contact
depth_of_field, bokeh
fisheye, panorama
```

---

## Lighting

### Basic Lighting
```
soft_lighting, natural_lighting, ambient_lighting
dramatic_lighting, cinematic_lighting
studio_lighting, professional_lighting
```

### Directional Lighting
```
backlighting, rim_lighting, side_lighting
underlighting, top_lighting
spotlight, focused_lighting
```

### Atmosphere
```
sunlight, golden_hour, warm_lighting
moonlight, night, cold_lighting
candlelight, firelight, neon_lighting
```

### Effects
```
glow, lens_flare, light_rays
volumetric_lighting, god_rays
shadows, hard_shadows, soft_shadows
```

---

## Environment & Settings

### Indoor
```
bedroom, bathroom, shower_room
office, classroom, locker_room
hotel_room, love_hotel
kitchen, living_room
```

### Furniture
```
bed, on_bed, lying_on_bed
couch, sofa, armchair
desk, table, against_wall
floor, carpet, tatami
```

### Outdoor
```
outdoors, outside, public
alley, rooftop, balcony
park, forest, beach
poolside, hot_spring
```

### Background
```
simple_background, white_background, gradient_background
blurred_background, bokeh_background
detailed_background, scenic_background
```

---

## Prompt Templates

### Template 1: Basic CG Page
```
[character count], [character type], [body features],
[clothing state], [pose/action], [expression],
[location], [camera angle],
[quality tags]

Negative: [standard negatives]
```

### Template 2: Sex Scene
```
[character count], [sex act], [position],
[character description], [body state],
[expression], [cum/fluid state],
[location], [angle],
masterpiece, best_quality, detailed, explicit

Negative: worst_quality, low_quality, bad_anatomy, censored
```

### Template 3: Aftermath Scene
```
[character count], after_sex, [position],
[character description], [body state],
[cum location], [expression],
[exhaustion state], [location],
masterpiece, best_quality, detailed

Negative: worst_quality, low_quality, bad_anatomy
```

---

## Complete Examples

### Example 1: Introduction Scene
**Positive:**
```
1girl, solo, mature_female, office_lady,
large_breasts, long_hair, brown_hair, brown_eyes,
business_suit, pencil_skirt, pantyhose,
standing, looking_at_viewer, nervous, light_blush,
office, desk, window, indoor,
from_front, upper_body,
masterpiece, best_quality, detailed, highres
```

**Negative:**
```
worst_quality, low_quality, lowres, bad_anatomy,
bad_hands, missing_fingers, poorly_drawn_face,
blurry, text, watermark, loli, child
```

### Example 2: Climax Scene
**Positive:**
```
1girl, 1boy, sex, vaginal, from_behind, doggy_style,
mature_female, large_breasts, nude, sweaty, wet,
(ahegao:1.3), tongue_out, drooling, tears,
(rolling_eyes:1.2), heavy_breathing,
(deep_penetration:1.2), pussy_juice,
bedroom, on_bed, messy_sheets,
from_side, dynamic_angle,
(masterpiece:1.2), best_quality, detailed, explicit
```

**Negative:**
```
worst_quality, low_quality, bad_anatomy,
censored, mosaic_censoring, bar_censor,
missing_fingers, extra_fingers, loli, child
```

### Example 3: Aftermath Scene
**Positive:**
```
1girl, solo, after_sex, lying, on_back,
mature_female, nude, large_breasts, sweaty,
(cum_on_body:1.2), cum_on_stomach, cum_on_breasts,
cum_dripping, cum_pool,
(exhausted:1.1), satisfied, half-closed_eyes, blush,
messy_hair, disheveled,
bed, pillow, sheets, indoor,
from_above,
masterpiece, best_quality, detailed, highres
```

**Negative:**
```
worst_quality, low_quality, bad_anatomy,
censored, text, watermark, loli, child
```

---

## Tips & Best Practices

### Do's
- Start with the main subject
- Use specific, descriptive terms
- Include quality tags
- Test and iterate
- Keep weights between 0.5-1.5
- Use negative prompts consistently

### Don'ts
- Don't use excessive weights (>1.5)
- Don't overload with too many tags
- Don't mix conflicting styles
- Don't forget negative prompts
- Don't use prohibited content tags

### Optimization
- Shorter prompts are faster to process
- More specific = better results
- Balance quality tags vs. content tags
- Use seed for reproducibility

---

## Sources

- [Hugging Face Diffusers - Prompt Weighting](https://huggingface.co/docs/diffusers/using-diffusers/weighted_prompts)
- [getimg.ai - Guide to Prompt Weights](https://getimg.ai/guides/guide-to-stable-diffusion-prompt-weights)
- [AIarty - Negative Prompts](https://www.aiarty.com/stable-diffusion-prompts/stable-diffusion-negative-prompt.htm)
- [Segmind - SDXL Prompt Guide](https://blog.segmind.com/prompt-guide-for-stable-diffusion-xl-crafting-textual-descriptions-for-image-generation/)
