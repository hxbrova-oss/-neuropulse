# Creatomate Template Spec — Weekly Top 5 AI Tools

## Dimensions
- Format: 1080 × 1920 (vertical, TikTok/Reels)
- Frame rate: 30fps
- Duration: ~12 seconds per tool × 5 = 60 seconds

## Text fields (created once in Creatomate editor)
| Field ID              | Sample value                  |
|-----------------------|-------------------------------|
| `tool_1_name`         | Notion AI                     |
| `tool_1_description`  | AI-powered docs, wikis, and project management |
| `tool_1_category`     | PRODUCTIVITY                  |
| `tool_1_pricing`      | 💰 Free tier available         |
| `tool_2_name`         | Cursor                        |
| `tool_2_description`  | AI-first code editor           |
| `tool_2_category`     | DEVELOPMENT                   |
| `tool_2_pricing`      | 💰 $20/month                   |
| ... (tool_3 through tool_5) | ...                     |

## Brand colors
- Background: `#0A0F1A` (dark navy)
- Primary text: `#FFFFFF`
- Accent: `#00D4FF` (NeuroPulse cyan)
- Category badge: `#00D4FF` with 20% opacity background
- Pricing: `#22C55E` (green)

## Intro/Outro
- **Intro slide** (2s): "Top 5 AI Tools This Week" | NeuroPulse logo top-right
- **Tool slides** (10s each): Tool name (big), category badge, description, pricing
- **Outro slide** (2s): "Follow for weekly AI tool drops" + NeuroPulse logo

## Animation style
- Fade/slide transitions (0.5s)
- Text reveals character by character (staggered, 0.02s per character)
- Subtle scale pulse on category badge (1.0 → 1.05 → 1.0, 2s loop)

## After creating the template
1. Create template in Creatomate editor
2. Copy Template ID → set as `CREATOMATE_TEMPLATE` in .env
3. Copy API Key → set as `CREATOMATE_KEY` in .env
