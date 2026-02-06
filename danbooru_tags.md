# Danbooru Tags Reference for NSFW CG Generation

This document provides a comprehensive reference for Stable Diffusion prompts using Danbooru tag format.

## Tag Format Rules
- **lowercase** with **underscores** for spaces: `long_hair`, `office_lady`
- **comma-separated**: `1girl, long_hair, blue_eyes`
- **weight syntax**: `tag:1.2` for emphasis, `tag:0.8` for de-emphasis
- **parentheses**: `(tag)` = 1.1x, `((tag))` = 1.21x, `(tag:1.5)` = 1.5x

---

## Quality Tags (推奨)
```
masterpiece, best_quality, highres, absurdres, incredibly_absurdres
detailed, ultra_detailed, intricate_details
official_art, high_resolution
```

## Negative Prompt (推奨)
```
lowres, bad_anatomy, bad_hands, text, error, missing_fingers
extra_digit, fewer_digits, cropped, worst_quality, low_quality
normal_quality, jpeg_artifacts, signature, watermark, username
blurry, censored, mosaic_censoring
```

---

## Character Tags

### Gender/Type
```
1girl, 2girls, multiple_girls
1boy, 2boys, multiple_boys
solo, solo_focus
futanari, full-package_futanari, newhalf
```

### Age Descriptors (成人のみ使用)
```
mature_female, milf, adult
office_lady, housewife
older_woman, middle-aged
```
**禁止**: `loli`, `shota`, `child`, `young`, `toddler`

### Body Type
```
slim, slender, curvy, voluptuous
tall, short, average_height
muscular, toned, athletic
plump, chubby, thick_thighs
```

---

## Body Parts

### Breasts
```
breasts, large_breasts, huge_breasts, gigantic_breasts
medium_breasts, small_breasts, flat_chest
cleavage, sideboob, underboob
areolae, large_areolae, puffy_areolae
nipples, erect_nipples, inverted_nipples, puffy_nipples
breast_squeeze, breast_grab, breasts_out
bouncing_breasts, sagging_breasts
```

### Buttocks
```
ass, huge_ass, large_ass, small_ass
ass_focus, ass_visible_through_thighs
butt_crack, dimples_of_venus
spread_ass, ass_grab
```

### Female Genitalia
```
pussy, spread_pussy, pussy_juice
clitoris, labia, mons_pubis
cleft_of_venus
wet_pussy, gaping
```

### Male Genitalia
```
penis, erection, large_penis, huge_penis
veiny_penis, circumcised, uncircumcised
testicles, large_testicles
foreskin, glans
```

### Pubic Area
```
pubic_hair, thick_pubic_hair, trimmed_pubic_hair
shaved_pussy, hairless_pussy
groin, crotch
```

---

## Facial Expressions

### Sexual Expressions
```
ahegao, fucked_silly, torogao
aroused, in_heat, naughty_face
orgasm, panting, heavy_breathing
rolling_eyes, cross-eyed
drooling, saliva, tongue_out
```

### Emotional Expressions
```
blush, embarrassed, full-face_blush
crying, tears, crying_with_eyes_open
happy, smile, grin, smirk
seductive_smile, evil_smile
scared, nervous, trembling
angry, glaring, clenched_teeth
surprised, shocked, wide-eyed
pleasure, ecstasy
```

### Eye Expressions
```
closed_eyes, half-closed_eyes
looking_at_viewer, looking_away
eye_contact, empty_eyes
heart-shaped_pupils, heart_eyes
```

### Mouth Expressions
```
open_mouth, closed_mouth
parted_lips, lip_biting
tongue, tongue_out, long_tongue
moaning, screaming
```

---

## Poses & Positions

### Basic Positions
```
standing, sitting, kneeling, lying
on_back, on_stomach, on_side
all_fours, doggy_style
squatting, crouching
leaning_forward, bent_over
arched_back
```

### Leg Positions
```
spread_legs, legs_apart, m_legs
legs_up, legs_over_head
crossed_legs, kneeling
missionary, mating_press
standing_split, leg_lift
```

### Arm Positions
```
arms_up, arms_behind_back, arms_behind_head
hand_on_hip, hands_on_hips
reaching, grabbing
bound_arms, tied_hands
```

### Sexual Positions
```
cowgirl_position, reverse_cowgirl
missionary, mating_press
doggy_style, from_behind
standing_sex, against_wall
suspended, standing_split
lap_pillow, sitting_on_lap
straddling, riding
```

---

## Sex Acts

### Penetration
```
sex, vaginal, anal
double_penetration, triple_penetration
deep_penetration, cervical_penetration
imminent_penetration, imminent_vaginal, imminent_anal
guided_penetration
```

### Oral
```
fellatio, deepthroat, irrumatio
cunnilingus, anilingus
licking, licking_penis, licking_pussy
breast_sucking, nipple_sucking
testicle_sucking
```

### Manual
```
handjob, fingering, fisting
anal_fingering, vaginal_fingering
masturbation, female_masturbation, male_masturbation
mutual_masturbation
groping, breast_grab, ass_grab
```

### Other Acts
```
paizuri, naizuri, thigh_sex
buttjob, footjob, armpit_sex
grinding, frottage
tentacle_sex, tentacles
```

### Group Sex
```
group_sex, threesome, gangbang
mmf_threesome, ffm_threesome
spitroast, double_penetration
orgy, multiple_boys, multiple_girls
```

---

## Cum & Ejaculation

### Cum Location
```
cum, cum_in_pussy, cum_in_ass, cum_in_mouth
cum_on_body, cum_on_face, cum_on_breasts
cum_on_stomach, cum_on_ass, cum_on_back
cum_on_hair, cum_on_clothes
facial, bukkake
cumdrip, cum_dripping, cum_overflow
cum_pool, cum_string
```

### Ejaculation
```
ejaculation, ejaculating
internal_cumshot, creampie
pull_out, cumshot
multiple_cumshots
```

### Related
```
cum_inflation, stomach_bulge
cum_in_throat, swallowing
gokkun, cum_swap
used_condom, condom
```

---

## Clothing States

### Undress States
```
nude, completely_nude, naked
topless, bottomless
partially_nude, partially_undressed
clothes_removed, undressing
lifting_clothes, shirt_lift, skirt_lift
clothes_pull, panty_pull, bra_pull
```

### Clothing Exposure
```
no_bra, no_panties, no_underwear
open_clothes, open_shirt, open_fly
torn_clothes, ripped_clothes
wet_clothes, see-through
underwear_only, lingerie
```

### Specific Clothing
```
school_uniform, office_lady, maid
nurse, teacher, secretary
bunny_girl, cheerleader
bikini, swimsuit, one-piece_swimsuit
lingerie, babydoll, negligee
garter_belt, garter_straps, stockings
thighhighs, pantyhose, fishnets
miniskirt, pencil_skirt, pleated_skirt
```

---

## BDSM & Fetish

### Bondage
```
bondage, bound, tied_up
rope, shibari, suspension
handcuffs, chains, collar
blindfold, ball_gag, gag
spreader_bar, stocks
bound_wrists, bound_ankles
arms_behind_back, hands_tied
```

### Domination
```
femdom, maledom, dominatrix
slave, pet_play, human_dog
leash, collar, choker
humiliation, body_writing
spanking, whip, crop
```

### Other Fetish
```
lactation, breast_milk, milking
inflation, stomach_bulge
mind_control, hypnosis
corruption, transformation
netorare, ntr, cheating
voyeurism, exhibitionism
public_nudity, public_sex
```

---

## View & Composition

### Camera Angle
```
from_above, from_below, from_behind, from_side
dutch_angle, pov, first-person_view
close-up, extreme_close-up
wide_shot, full_body, upper_body, lower_body
cowboy_shot, portrait
```

### Focus
```
ass_focus, breast_focus, pussy_focus
face_focus, crotch_focus
foot_focus, thigh_focus
```

### Special Views
```
x-ray, cross-section, internal_view
multiple_views, sequence
split_screen
```

---

## Lighting & Atmosphere

### Lighting
```
backlighting, rim_lighting, dramatic_lighting
soft_lighting, studio_lighting
sunlight, moonlight, candlelight
dark, dimly_lit, shadow
spotlight, glowing
```

### Atmosphere
```
steamy, misty, foggy
wet, sweaty, glistening
```

---

## Settings/Locations

### Indoor
```
bedroom, bathroom, shower
office, classroom, locker_room
hotel_room, love_hotel
kitchen, living_room
```

### Specific Furniture
```
bed, on_bed, in_bed
couch, sofa, chair
desk, table, against_wall
floor, carpet, tatami
```

### Outdoor
```
outdoors, public, alley
rooftop, balcony, poolside
forest, beach, park
```

---

## Story Arc Tags (CG集用)

### Introduction (導入)
```
eye_contact, looking_at_viewer
standing, sitting, kneeling
clothed, underwear, lingerie
nervous, embarrassed, blush
```

### Development (展開)
```
undressing, clothes_removed
groping, touching, caressing
aroused, wet, panting
spread_legs, exposed
```

### Climax (クライマックス)
```
sex, penetration, deep_penetration
ahegao, fucked_silly, orgasm
cum, creampie, facial
screaming, moaning, drooling
```

### Resolution (余韻)
```
after_sex, afterglow
lying, exhausted, satisfied
cum_dripping, messy
cuddling, embracing
```

---

## Prompt Examples

### Example 1: Office Lady Introduction
```
1girl, solo, office_lady, mature_female, large_breasts,
business_suit, pencil_skirt, pantyhose,
standing, looking_at_viewer, nervous, blush,
office, desk, window,
masterpiece, best_quality, detailed
```

### Example 2: Climax Scene
```
1girl, 1boy, sex, vaginal, from_behind, doggy_style,
mature_female, large_breasts, nude, sweaty,
ahegao, tongue_out, drooling, tears,
deep_penetration, cum_in_pussy,
bedroom, on_bed,
masterpiece, best_quality, explicit
```

### Example 3: Aftermath
```
1girl, solo, after_sex, lying, on_back,
mature_female, nude, messy_hair,
cum_on_body, cum_on_stomach, cum_dripping,
exhausted, satisfied, blush, half-closed_eyes,
bed, pillow, sheets,
masterpiece, best_quality, detailed
```
