# Forgotten Valley - Art Bible

## Render target
Unity URP. Goal = 'grounded realistic', NOT photoreal HDRP. A weak GPU
must hold 60fps at 1080p. Stylized-realistic: real proportions + PBR
materials, but readable silhouettes and a controlled palette.

## Mood
Overcast Nordic-temperate valley. Damp. Low sun. Volumetric-ish fog
but BOUNDED (you can always see ~40-60m; the moody-fog mistake earlier
was unbounded fog -> flat void). Fog is atmosphere, never a wall.

## Palette
Desaturated greens/greys, wet bark browns, cold blue shadow, one warm
accent = the hearth fire + relic shards (amber/orange) so the player's
eye always finds 'home' and 'goal'.

## Lighting
Single soft directional 'sun' low on the horizon (golden-hour-ish),
gentle ambient from sky, baked where static. Night = moonlight (cool,
low) + hearth as the only warm pool. Contrast between safe-warm and
wild-cold is the whole visual thesis.

## Performance rails (URP)
- Tris budget on screen: <= ~900k. LODs on every tree/rock.
- Realtime lights: sun + hearth + max 4 small point lights at night.
- Fog: linear, start ~15m end ~70m. NEVER exponential-squared at high
  density (that was the void bug).
- One post-process volume: subtle tonemap (ACES), gentle vignette,
  mild bloom on the hearth/relics only.

## Readability rules
Interactables get a faint rim/emissive. Enemies silhouette dark
against fog. The hearth glow is visible from anywhere in the valley.
