import json
import re
import time
import math
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from backend.models.ai_models import (
    AgronomySLMRequest,
    AgronomySLMResponse,
    AgronomyChatMessage
)
from backend.services.advisory_engine import (
    generate_home_garden_advisory,
    calculate_climate_normals,
    STATE_EXTENSIONS
)
from backend.services.state_lookup import resolve_state_code

logger = logging.getLogger("agronomy_slm")


# ── Expanded keyword → scenario dispatch table ───────────────
# Each entry: (keyword_list, handler_name)
# Evaluated in order — first match wins within a mode group.

GARDENER_SCENARIOS = [
    (["lead", "contamination", "soil test", "safe soil", "heavy metal", "brownfield", "polluted"],
     "_urban_soil_safety"),
    (["urban farm", "urban agriculture", "city lot", "vacant lot", "community garden", "plot", "allotment"],
     "_urban_farm_start"),
    (["snap", "link match", "ebt", "food access", "food desert", "affordable food", "mobile market", "fresh moves"],
     "_urban_food_access"),
    (["raised bed", "city garden", "balcony", "rooftop", "lot garden"],
     "_urban_raised_beds"),
    (["frost", "when to plant", "calendar", "season", "date", "schedule", "spring", "fall", "timing", "transplant"],
     "_gardener_timing"),
    (["soil", "clay", "sand", "ph", "compost", "fertilizer", "amend", "loam", "texture", "organic matter",
      "topsoil", "perlite", "drainage", "acidic", "alkaline", "lime", "sulfur"],
     "_gardener_soil"),
    (["container", "pot", "patio", "grow bag", "window box"],
     "_gardener_containers"),
    (["water", "irrigation", "drip", "soaker", "drought", "mulch", "moisture", "overwater"],
     "_gardener_water"),
    (["seed", "germination", "seedling", "indoor", "transplant", "start seeds", "stratification"],
     "_gardener_seeds"),
    (["companion plant", "intercrop", "three sisters", "guild", "polyculture"],
     "_gardener_companions"),
    (["harvest", "when to pick", "ripe", "mature", "ready", "yield", "storage"],
     "_gardener_harvest"),
    (["cover crop", "rotation", "no-till", "fallow", "nitrogen fix", "rye", "clover", "buckwheat"],
     "_gardener_rotation"),
    (["pest", "bug", "insect", "worm", "blight", "mildew", "rot", "aphid", "mite", "hornworm",
      "beetle", "caterpillar", "slug", "scale", "whitefly", "cucumber beetle"],
     "_gardener_pests"),
    (["native", "pollinator", "bee", "butterfly", "wildflower", "habitat", "flower", "monarch"],
     "_gardener_natives"),
    (["tomato", "tomatoes"], "_crop_tomato"),
    (["pepper", "peppers", "hot pepper", "jalapeño", "habanero"], "_crop_pepper"),
    (["squash", "zucchini", "pumpkin", "winter squash", "summer squash", "cucurbit"], "_crop_squash"),
    (["lettuce", "greens", "spinach", "kale", "arugula", "salad", "mesclun", "chard", "collard"], "_crop_greens"),
    (["bean", "beans", "pea", "peas", "legume", "lentil"], "_crop_beans"),
    (["carrot", "carrots", "beet", "beets", "radish", "turnip", "parsnip", "root vegetable"], "_crop_roots"),
    (["herb", "herbs", "basil", "oregano", "thyme", "rosemary", "dill", "cilantro", "parsley", "mint"],
     "_crop_herbs"),
]

HOMESTEADER_SCENARIOS = [
    (["chicken", "hen", "egg", "coop", "flock", "poultry", "rooster", "chick", "layer", "broiler"],
     "_homesteader_chickens"),
    (["compost", "manure", "fertility", "cover crop", "humus", "worm", "vermicompost"],
     "_homesteader_compost"),
    (["fruit", "tree", "orchard", "berry", "apple", "peach", "pear", "plum", "cherry",
      "blueberry", "raspberry", "blackberry", "strawberry", "grape"],
     "_homesteader_fruit"),
    (["preserve", "can", "canning", "freeze", "dry", "ferment", "storage", "pickle",
      "jam", "jelly", "dehydrate", "root cellar", "lacto"],
     "_homesteader_preserve"),
    (["goat", "pig", "sheep", "cattle", "cow", "livestock", "pasture", "grazing", "fence"],
     "_homesteader_livestock"),
    (["rainwater", "well", "water system", "cistern", "gray water", "irrigation", "water harvest"],
     "_homesteader_water"),
    (["beekeeping", "bee", "hive", "honey", "beeswax", "pollination"],
     "_homesteader_bees"),
    (["energy", "solar", "wind", "propane", "off grid", "generator", "battery"],
     "_homesteader_energy"),
]

SMALL_FARM_SCENARIOS = [
    (["food access", "affordable", "neighbors who need", "sliding scale", "pantry", "donate produce"],
     "_urban_grower_food_access"),
    (["mobile market", "fresh moves", "link match", "snap sales", "ebt"],
     "_urban_grower_mobile"),
    (["apprentice", "apprenticeship", "grower training", "internship", "workforce", "job training"],
     "_urban_grower_training"),
    (["business", "plan", "loan", "fsa", "nrcs", "budget", "revenue", "profit", "startup", "funding"],
     "_farm_business"),
    (["equipment", "tractor", "tiller", "tunnel", "irrigation", "tool", "bcs", "broadfork", "seeder"],
     "_farm_equipment"),
    (["rotation", "cover crop", "soil health", "no-till", "regenerative", "organic certification"],
     "_farm_rotation"),
    (["market", "csa", "sell", "wholesale", "restaurant", "farm stand", "direct", "price", "booth"],
     "_farm_sales"),
    (["labor", "employee", "intern", "wwoof", "crew", "hire"],
     "_farm_labor"),
    (["pest management", "ipm", "integrated pest", "spray schedule", "organic certification",
      "row cover", "beneficial insect"],
     "_farm_ipm"),
    (["high tunnel", "greenhouse", "season extension", "low tunnel", "frost protection", "row cover"],
     "_farm_season_extension"),
]


class AgronomySLMEngine:
    """
    Domain-Specific Agronomic Small Language Model (SLM) Inference Engine.
    Combines dense botanical knowledge retrieval with rule-based parametric agronomy
    and generative synthesis to provide hyper-localized, Master Gardener-grade advice.
    """

    def __init__(self, dataset_path: Optional[str] = None):
        self.dataset_path = dataset_path or str(
            Path(__file__).resolve().parent.parent / "ml" / "data" / "agronomy_qa_dataset.jsonl"
        )
        self.knowledge_base: List[Dict[str, Any]] = []
        self._load_knowledge_base()

    def _load_knowledge_base(self):
        try:
            if Path(self.dataset_path).exists():
                with open(self.dataset_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            self.knowledge_base.append(json.loads(line.strip()))
                logger.info(f"Loaded {len(self.knowledge_base)} agronomic knowledge vectors.")
            else:
                logger.warning(f"Knowledge base not found at {self.dataset_path}. Generating…")
                from backend.ml.dataset_generator_slm import generate_agronomy_slm_dataset
                generate_agronomy_slm_dataset(self.dataset_path)
                self._load_knowledge_base()
        except Exception as e:
            logger.error(f"Failed to load SLM knowledge base: {e}")

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r'\b[a-zA-Z0-9_-]{3,}\b', text)]

    def _score_relevance(self, query_tokens: List[str], target_text: str, state: str) -> float:
        target_tokens = set(self._tokenize(target_text))
        if not target_tokens:
            return 0.0
        match_count = sum(1 for t in query_tokens if t in target_tokens)
        score = match_count / math.sqrt(len(target_tokens) + 1)
        if state.lower() in target_text.lower():
            score += 1.5
        return score

    def _match_scenario(self, query: str, scenarios: list) -> Optional[str]:
        """Return the first handler name whose keywords appear in the query."""
        for keywords, handler in scenarios:
            if any(kw in query for kw in keywords):
                return handler
        return None

    # ── Context helpers ──────────────────────────────────────

    def _location(self, req, st_upper):
        return f"{req.county}, {st_upper}" if req.county else st_upper

    def _zone_intro(self, climate, st_upper, req):
        return (
            f"**{self._location(req, st_upper)}** — "
            f"USDA Zone **{climate.hardiness_zone}**, "
            f"**{climate.frost_free_days}** frost-free days "
            f"({climate.last_spring_frost_date} → {climate.first_fall_frost_date})"
        )

    # ── Gardener scenarios ────────────────────────────────────

    def _urban_soil_safety(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🧪 **Chicago Urban Soil Safety — {z}**\n\n"
            f"**Why it matters:** Many Chicago lots have legacy lead from paint, industry, or fill. "
            f"Your mapped soil series is **{soil.soil_series}** ({soil.native_texture}), but city soil "
            f"can differ from native maps — always test before growing food in ground beds.\n\n"
            f"**Do this first:**\n"
            f"1. Get a lead/heavy-metal soil test (UI Extension or a lab that reports lead in ppm)\n"
            f"2. Keep kids and pets off bare soil until results are back\n"
            f"3. Prefer **raised beds with imported clean topsoil + compost** for food crops\n\n"
            f"**If lead is elevated:** Grow in lined raised beds or containers; mulch paths; "
            f"wash produce well; avoid root crops in contaminated ground. Leafy greens and fruiting "
            f"crops in clean media are safer choices.\n\n"
            f"**Resources:** Cook County / University of Illinois Extension Master Gardeners, "
            f"and urban farms like Urban Growers Collective model safe growing practices citywide."
        )

    def _urban_farm_start(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🏙️ **Starting Urban Ag in Chicago — {z}**\n\n"
            f"**Paths that work here:** community garden plot, backyard raised beds, vacant-lot "
            f"stewardship with clear permission, or partnering with an existing urban farm.\n\n"
            f"**Practical starter plan:**\n"
            f"- Confirm land access (owner, park district, or garden waitlist)\n"
            f"- Soil test or use **raised beds** (see soil-safety guidance)\n"
            f"- Start with high-value greens, herbs, tomatoes, and peppers after "
            f"**{climate.last_spring_frost_date}**\n"
            f"- Plan water (hose, rain barrel, or shared garden spigot) and tool storage\n"
            f"- Share surplus through neighbors, markets, or food-access partners\n\n"
            f"**Learn alongside growers:** Organizations such as Urban Growers Collective run farms, "
            f"training, and food-access programs across Chicago — visit urbangrowerscollective.org "
            f"and use this map to find nearby markets and urban farms."
        )

    def _urban_food_access(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🧺 **Food Access & SNAP/Link in Chicago — {z}**\n\n"
            f"**For neighbors who need food:** Look on the map for farmers markets and farm stands "
            f"marked **SNAP/Link Match** — Illinois Link (EBT) often stretches further with match "
            f"programs at participating Chicago markets.\n\n"
            f"**For growers:** Selling at Link Match markets, CSA shares with sliding scale, "
            f"and partnerships with food pantries or mobile markets help get produce into "
            f"neighborhoods that need it.\n\n"
            f"**Tips:**\n"
            f"- Filter the map for SNAP/Link sites near your zip\n"
            f"- Ask market managers about Link Match hours and eligible products\n"
            f"- Urban farms and orgs (e.g. Urban Growers Collective, Link Up Illinois partners) "
            f"often combine growing, jobs training, and affordable produce\n\n"
            f"Use **Find Local Markets & Food** on this app to locate sites, hours, and directions."
        )

    def _urban_raised_beds(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🪴 **Chicago Raised Beds & City Lots — {z}**\n\n"
            f"**Bed build (food-safe):** Untreated wood, stone, or food-grade plastic frames; "
            f"landscape fabric optional as a barrier over questionable ground soil. "
            f"Fill with ~50% topsoil / 30% compost / 20% aeration (perlite or bark).\n\n"
            f"**Size that works on small lots:** 4×8 ft beds you can reach from both sides; "
            f"18–24 in depth for tomatoes and roots.\n\n"
            f"**Season for Zone {climate.hardiness_zone}:** Cool greens before and after "
            f"**{climate.last_spring_frost_date}**; warm crops after frost risk passes. "
            f"You have about **{climate.frost_free_days}** frost-free days — succession-sow greens.\n\n"
            f"**Native soil note:** Mapped as {soil.soil_series} ({soil.native_texture}). "
            f"In the city, still prefer imported mix for eating gardens unless a soil test is clean."
        )

    def _gardener_timing(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🗓️ **Planting Calendar for {z}**\n\n"
            f"**Cool-Season Crops** (lettuce, spinach, peas, kale, radishes, carrots):\n"
            f"- Direct sow outdoors **3–4 weeks before {climate.last_spring_frost_date}**\n"
            f"- Or start fall crops **8–10 weeks before {climate.first_fall_frost_date}**\n\n"
            f"**Warm-Season Crops** (tomatoes, peppers, squash, beans, cucumbers, basil):\n"
            f"- Start tomatoes and peppers **indoors 6–8 weeks before {climate.last_spring_frost_date}**\n"
            f"- Transplant outdoors **1–2 weeks after {climate.last_spring_frost_date}** once soil reaches 60°F\n"
            f"- Direct sow beans, squash, and cucumber after last frost\n\n"
            f"**Zone Note:** Zone {climate.hardiness_zone} means your winters reliably reach "
            f"certain minimum temperatures. A longer frost-free window (your {climate.frost_free_days} days) "
            f"means you can succession-plant greens 3–4 times per year."
        )

    def _gardener_soil(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🪴 **Soil Guide for {z}**\n\n"
            f"**Your native soil:** {soil.soil_series} — {soil.native_texture}, pH {soil.native_ph_range}\n\n"
            f"**{soil.garden_suitability_summary}**\n\n"
            f"**Organic Raised Bed Mix (recommended):**\n"
            f"- 50% screened topsoil\n"
            f"- 30% finished compost\n"
            f"- 20% coarse perlite or pine bark fines\n\n"
            f"**Amending in-ground beds:**\n"
            f"- Add 3–4 inches of compost and work in 8–10 inches deep before first planting\n"
            f"- If pH is below 6.0: add agricultural lime (1–2 lbs per 10 sq ft)\n"
            f"- If pH is above 7.5: add sulfur or acidifying fertilizer\n"
            f"- Mulch all beds with 2–3 inches of straw after planting to retain moisture\n\n"
            f"**{soil.raised_bed_recommendation}**"
        )

    def _gardener_containers(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🪣 **Container Gardening Guide for {z}**\n\n"
            f"**Container sizing:**\n"
            f"- Herbs & lettuce: 6–8 inch deep pots\n"
            f"- Peppers, bush beans: 10–12 inch deep pots\n"
            f"- Tomatoes, eggplant: 5-gallon bucket minimum; 10-gallon is better\n"
            f"- Root crops (carrots, beets): 12+ inches deep\n\n"
            f"**Soil:** Use a light potting mix — never garden soil in pots (it compacts and kills drainage).\n\n"
            f"**Watering:** Containers dry out 2–3× faster than in-ground beds. "
            f"Water when the top inch is dry. In summer heat, large containers may need daily water.\n\n"
            f"**Feeding:** Apply a balanced liquid fertilizer every 2 weeks — containers leach nutrients fast.\n\n"
            f"**Best container crops for Zone {climate.hardiness_zone}:**\n"
            f"- Cherry tomatoes (Tumbling Tom, Sweet 100, Patio)\n"
            f"- Peppers (any variety)\n"
            f"- Lettuce and spinach (perfect for partial shade containers)\n"
            f"- Herbs: basil, thyme, oregano, chives, mint (mint needs its own pot — it spreads aggressively)\n"
            f"- Bush beans and peas on a small trellis"
        )

    def _gardener_water(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"💧 **Watering & Moisture Guide for {z}**\n\n"
            f"**General target:** 1 inch per week (from rain + irrigation combined)\n"
            f"- In hot summers: may need 1.5–2 inches/week\n"
            f"- Check with a rain gauge or a simple 1-inch container set out in the garden\n\n"
            f"**Best method:** Drip irrigation or soaker hose on a timer\n"
            f"- Waters roots directly, keeps leaves dry (prevents fungal disease)\n"
            f"- Set timer to run early morning (5–7am) so leaves dry before afternoon heat\n"
            f"- Overhead sprinklers increase blight risk on tomatoes and squash\n\n"
            f"**Mulch is your best tool:**\n"
            f"- 2–3 inches of straw, shredded leaves, or wood chips cuts water needs by 40–60%\n"
            f"- Keeps soil temperature stable and suppresses weeds simultaneously\n\n"
            f"**Reading your plants:**\n"
            f"- Wilting at midday in heat = normal; wilting in morning = underwater\n"
            f"- Yellow lower leaves + soggy soil = overwatered (stop and let it dry)\n"
            f"- Blossom end rot on tomatoes = inconsistent moisture (even watering fixes it)"
        )

    def _gardener_seeds(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🌱 **Seed Starting Guide for {z}**\n\n"
            f"**Start indoors (weeks before last frost {climate.last_spring_frost_date}):**\n"
            f"- 8–10 weeks before: celery, onion, leek, peppers\n"
            f"- 6–8 weeks before: tomatoes, eggplant\n"
            f"- 4–6 weeks before: broccoli, cabbage, cauliflower, Brussels sprouts\n"
            f"- 2–4 weeks before: lettuce, chard, kale (can also direct sow)\n\n"
            f"**Direct sow (outdoors):**\n"
            f"- 3–4 weeks before last frost: peas, spinach, lettuce, radishes, carrots\n"
            f"- After last frost: beans, squash, cucumbers, corn, sunflowers, basil\n\n"
            f"**Germination tips:**\n"
            f"- Soil temperature matters more than air temp: most seeds need 65–75°F to germinate\n"
            f"- A seedling heat mat speeds germination by 30–50%\n"
            f"- Keep seed-starting mix moist but never soggy — use a spray bottle\n"
            f"- Harden off transplants over 7–10 days (increase outdoor exposure gradually)\n\n"
            f"**Don't start these indoors:** beans, peas, carrots, beets, radishes, parsley — they resent root disturbance"
        )

    def _gardener_companions(self, query, soil, climate, ext, st_upper, req, natives):
        return (
            f"🌿 **Companion Planting Guide**\n\n"
            f"**Classic combinations:**\n"
            f"- **Tomatoes + Basil:** Basil may repel aphids and improve tomato flavor; basil also attracts pollinators\n"
            f"- **Three Sisters (Corn + Beans + Squash):** Corn provides trellis for beans, beans fix nitrogen, squash covers ground to suppress weeds\n"
            f"- **Carrots + Onions:** Onion smell deters carrot fly; carrot smell deters onion fly\n"
            f"- **Brassicas + Dill:** Dill attracts parasitic wasps that control cabbage caterpillars\n"
            f"- **Roses + Garlic:** Garlic deters aphids from rose bushes\n\n"
            f"**Beneficial insect attractors (plant among vegetables):**\n"
            f"- Dill, fennel, and parsley (umbel flowers) → feed lacewings and parasitic wasps\n"
            f"- Alyssum (sweet alyssum) → hoverflies whose larvae eat aphids\n"
            f"- Phacelia, borage, and native wildflowers → bumblebees and native pollinators\n\n"
            f"**Avoid planting together:**\n"
            f"- Onions/garlic + beans/peas (alliums suppress legume growth)\n"
            f"- Fennel + most vegetables (fennel releases allelopathic compounds — grow it alone)\n"
            f"- Tomatoes + brassicas (compete heavily for nutrients)"
        )

    def _gardener_harvest(self, query, soil, climate, ext, st_upper, req, natives):
        return (
            f"🧺 **Harvest Timing & Storage Guide**\n\n"
            f"**Harvest at the right moment — plants produce MORE when harvested regularly:**\n\n"
            f"- **Tomatoes:** Fully colored, slightly soft. Windowsill-ripen if frost approaches.\n"
            f"- **Zucchini/Summer Squash:** 6–8 inches long. Don't let them become baseball bats — plant stops producing.\n"
            f"- **Beans:** Pods snap cleanly, seeds barely visible inside. Check every 2 days in peak season.\n"
            f"- **Cucumbers:** Before any yellowing begins — usually 6–8 inches for slicers, 3–4 for pickling types.\n"
            f"- **Peppers:** Green = fully formed but immature. Colored = sweeter and higher in vitamins. Both are edible.\n"
            f"- **Lettuce/Greens:** Harvest outer leaves continuously ('cut-and-come-again') or cut whole heads just above the crown.\n"
            f"- **Carrots:** 70–80 days typically; shoulders visible at soil surface is a good sign.\n"
            f"- **Basil:** Pinch flower buds as soon as they appear — once it bolts, flavor drops immediately.\n\n"
            f"**Short-term storage:**\n"
            f"- Most vegetables: refrigerator immediately after harvest\n"
            f"- Tomatoes: counter at room temp (fridge kills flavor)\n"
            f"- Basil: like cut flowers in a glass of water on the counter, not refrigerator"
        )

    def _gardener_rotation(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"♻️ **Crop Rotation & Cover Crops for {z}**\n\n"
            f"**Why rotate?** Same plant family in the same spot builds up specific soil pathogens and depletes specific nutrients.\n\n"
            f"**4-Year Rotation (1 bed = 1 zone, rotate each spring):**\n"
            f"1. **Nightshades** (tomatoes, peppers, eggplant, potatoes) — heavy feeders\n"
            f"2. **Brassicas** (broccoli, cabbage, kale, radishes) — medium feeders\n"
            f"3. **Legumes** (beans, peas) — nitrogen fixers, light feeders\n"
            f"4. **Roots + Cucurbits** (carrots, beets, squash, cucumbers) — loosen soil\n\n"
            f"**Cover crops by season in Zone {climate.hardiness_zone}:**\n"
            f"- **Fall/Winter:** Winter rye or winter wheat (hardy, suppresses weeds, builds organic matter)\n"
            f"- **Spring fallow:** Crimson clover or hairy vetch (fixes nitrogen for the following crop)\n"
            f"- **Summer fallow:** Buckwheat (fast-growing, smothers weeds, feeds pollinators)\n\n"
            f"Mow or till cover crops 2–3 weeks before planting the next crop. "
            f"Your native soil ({soil.native_texture}, pH {soil.native_ph_range}) benefits especially from the organic matter."
        )

    def _gardener_pests(self, query, soil, climate, ext, st_upper, req, natives):
        pest_list = ext.get("pest_watch", [])
        regional_pests = ", ".join(pest_list[:5]) if pest_list else "aphids, hornworms, cucumber beetles, and powdery mildew"
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🛡️ **Organic Pest & Disease Guide for {z}**\n\n"
            f"**Regional pests to watch:** {regional_pests}\n\n"
            f"**Prevention first (Integrated Pest Management):**\n"
            f"- Scout your garden every 2–3 days; check leaf undersides and soil at plant bases\n"
            f"- Floating row covers on transplants for first 2–3 weeks block most flying pests\n"
            f"- Companion plants: dill, fennel, alyssum attract predatory insects\n"
            f"- Healthy soil = healthy plants; stressed plants attract more pests\n\n"
            f"**Targeted organic controls:**\n"
            f"- **Aphids:** Blast with water; spray insecticidal soap (1 tsp dish soap per quart water)\n"
            f"- **Caterpillars/hornworms:** Hand-pick; spray Bt (Bacillus thuringiensis) in evening\n"
            f"- **Cucumber beetles:** Yellow sticky traps + kaolin clay on foliage\n"
            f"- **Powdery mildew:** Baking soda spray (1 tbsp + 1 tsp oil per gallon); improve air circulation\n"
            f"- **Early/Late blight (tomatoes):** Copper fungicide preventively every 7–10 days in wet weather\n"
            f"- **Slugs:** Beer traps; diatomaceous earth around plant bases\n"
            f"- **General:** Neem oil (1 tbsp per gallon + few drops soap) — broad-spectrum, safe for bees after drying"
        )

    def _gardener_natives(self, query, soil, climate, ext, st_upper, req, natives):
        native_list = ext.get("native_species", [])
        native_names = [f"**{n['common_name']}** (*{n.get('botanical_name', '')}*)" for n in native_list[:5]]
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🌸 **Native Plants & Pollinators for {z}**\n\n"
            f"**Top native species for your ecoregion ({ext.get('ecoregion', 'temperate').replace('_', ' ').title()}):**\n"
            + "\n".join(f"- {n}" for n in native_names) + "\n\n"
            f"**Why natives?**\n"
            f"- Zero synthetic fertilizer or pesticide needed once established\n"
            f"- Support native bees, butterflies, and beneficial insects that pollinate your vegetable garden\n"
            f"- Drought-tolerant once roots are established (usually after first full growing season)\n\n"
            f"**Placement:**\n"
            f"- Plant a 3–5 foot wide 'pollinator border' along one edge of your vegetable beds\n"
            f"- Include early, mid, and late bloomers for season-long nectar availability\n"
            f"- Even a small patch of native wildflowers significantly increases pollinator populations within 50 feet"
        )

    # ── Crop-specific scenarios ───────────────────────────────

    def _crop_tomato(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🍅 **Tomato Growing Guide for {z}**\n\n"
            f"**Starting:** Begin seeds indoors 6–8 weeks before {climate.last_spring_frost_date}.\n"
            f"Transplant outdoors 1–2 weeks after last frost when soil is above 60°F.\n\n"
            f"**Spacing:** Indeterminate (vining) varieties: 24–36 inches apart, staked or caged. "
            f"Determinate (bush) varieties: 18–24 inches apart.\n\n"
            f"**Feeding:** Heavy feeders — apply compost at planting, then a balanced fertilizer every 2 weeks "
            f"once flowering begins. Reduce nitrogen after first flowers appear.\n\n"
            f"**Watering:** Deep and consistent — 1–2 inches/week. Inconsistent watering causes blossom end rot "
            f"and cracking. Mulch heavily around the base.\n\n"
            f"**Disease prevention in Zone {climate.hardiness_zone}:**\n"
            f"- Remove lower leaves touching soil (first 12 inches)\n"
            f"- Never overhead water — drip or soaker only\n"
            f"- Stake or cage immediately at planting for airflow\n"
            f"- Copper fungicide preventively every 10–14 days in wet weather\n\n"
            f"**Best varieties for your zone:** Look for disease-resistant labels (VFN = verticillium, fusarium, nematode resistant). "
            f"In hot climates: Heat Master, Celebrity. In cool climates: Siletz, Stupice."
        )

    def _crop_pepper(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🌶️ **Pepper Growing Guide for {z}**\n\n"
            f"**Starting:** Peppers need the longest indoor head start — start seeds **8–10 weeks before {climate.last_spring_frost_date}**.\n"
            f"They need soil temps of 70–80°F to germinate (use a heat mat).\n\n"
            f"**Transplanting:** Wait until nights are consistently above 55°F and soil is above 65°F.\n"
            f"Peppers are extremely cold-sensitive — even a cool night stunts them for weeks.\n\n"
            f"**In short-season zones (Zone {climate.hardiness_zone}):**\n"
            f"- Focus on fast-maturing varieties: Ace, Gypsy, California Wonder, Shishito\n"
            f"- A wall of water or black plastic mulch speeds soil warming by 2–4 weeks\n\n"
            f"**Feeding:** Moderate feeders. Too much nitrogen = beautiful plants, no fruit. "
            f"Switch to a low-N bloom fertilizer once flowers appear.\n\n"
            f"**Harvest:** Green peppers = immature but edible. Colored (red/yellow/orange) = sweeter, more vitamins. "
            f"The longer you wait, the sweeter and more nutritious — but the plant can only ripen so many at once."
        )

    def _crop_squash(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🎃 **Squash & Zucchini Guide for {z}**\n\n"
            f"**Direct sow after last frost** — squash dislikes root disturbance, so direct seeding is preferred.\n"
            f"Plant after {climate.last_spring_frost_date} when soil is 65°F+.\n\n"
            f"**Spacing:** Bush zucchini: 24–36 inches. Vining winter squash: 4–6 feet. Give them ROOM.\n\n"
            f"**Harvesting zucchini:** Pick at 6–8 inches. Check EVERY day in peak season — "
            f"a missed zucchini becomes a watery baseball bat overnight and the plant slows production.\n\n"
            f"**Winter squash:** Let it mature on the vine until the skin hardens and the stem dries out. "
            f"Harvest before first hard frost. Cure at 80°F for 10 days before storage.\n\n"
            f"**Squash vine borer:** The #1 killer of squash in the eastern US. "
            f"Wrap base of stems with aluminum foil to prevent egg-laying; or plant a second batch 3 weeks later as backup.\n\n"
            f"**Powdery mildew:** Almost inevitable by late season. Tolerate it if plants are still producing; "
            f"spray baking soda solution early to slow it."
        )

    def _crop_greens(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🥬 **Greens & Salad Crops Guide for {z}**\n\n"
            f"**Cool-season crops** — best planted in spring and fall, NOT in summer heat.\n\n"
            f"**Spring planting:** Direct sow 3–4 weeks before {climate.last_spring_frost_date}.\n"
            f"**Fall planting:** Sow 6–8 weeks before {climate.first_fall_frost_date} for a fall harvest.\n\n"
            f"**Succession planting:** Sow a new row every 2–3 weeks for continuous harvest all season.\n\n"
            f"**Bolt prevention:** Most greens bolt (go to flower) when days get long and hot.\n"
            f"- Grow heat-tolerant varieties for summer: Jericho lettuce, New Red Fire, Batavian types\n"
            f"- Shade cloth (30–50%) extends the season in summer by 4–6 weeks\n\n"
            f"**Harvest style:** Cut-and-come-again for lettuce, chard, arugula — harvest outer leaves, "
            f"leave the crown and it regrows 2–3 more times. "
            f"Kale and chard can produce all season this way.\n\n"
            f"**Soil needs:** Moderate nitrogen. Top-dress with compost between cuttings."
        )

    def _crop_beans(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🫘 **Beans & Peas Guide for {z}**\n\n"
            f"**Beans (warm-season):** Direct sow after last frost ({climate.last_spring_frost_date}), "
            f"soil 60°F+. Do NOT start indoors — they resent transplanting.\n"
            f"- Bush beans: 18 inches apart, harvest in 50–60 days\n"
            f"- Pole beans: 4–6 inch spacing, need a 6-foot trellis, harvest over longer season\n\n"
            f"**Peas (cool-season):** Direct sow 4–6 weeks BEFORE last frost — peas need cool soil to germinate.\n"
            f"They stop producing when temps reach 80°F. A fall planting works well too.\n\n"
            f"**Nitrogen fixing:** Both beans and peas fix atmospheric nitrogen into the soil through root nodules. "
            f"When you pull spent plants, cut them at the soil line and leave the roots in — "
            f"those nodules release nitrogen for the next crop.\n\n"
            f"**Harvest:** Pick beans when pods snap cleanly (seeds barely formed). "
            f"Check every 2 days — overmature beans are tough and the plant slows down.\n\n"
            f"**Inoculant:** If beans haven't grown in that soil before, dust seeds with rhizobium inoculant powder. It boosts nitrogen fixation significantly."
        )

    def _crop_roots(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🥕 **Root Vegetables Guide for {z}**\n\n"
            f"**Cool-season crops** — direct sow in early spring or late summer/fall.\n"
            f"Sow 3–5 weeks before last frost ({climate.last_spring_frost_date}) for spring crop.\n"
            f"Sow 8–10 weeks before first fall frost ({climate.first_fall_frost_date}) for fall/winter crop.\n\n"
            f"**Soil preparation is everything for roots:**\n"
            f"Your soil is {soil.native_texture} (pH {soil.native_ph_range}).\n"
            f"- Heavy clay → grow in raised beds filled with light sandy loam or use short 'Chantenay' types\n"
            f"- Rocky soil → same as above; rocks cause forking in carrots\n"
            f"- Sandy loam → ideal; roots grow deep and straight naturally\n\n"
            f"**Thinning:** The single most neglected step. Thin carrots to 2–3 inches apart and beets to 3–4 inches. "
            f"Crowded roots produce only tops.\n\n"
            f"**Harvest:** Wait for roots to reach maturity (size noted on seed packet). "
            f"Carrots actually sweeten after a light frost. Leave in ground and harvest as needed in fall "
            f"(with mulch protection) in Zone {climate.hardiness_zone}."
        )

    def _crop_herbs(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🌿 **Herb Growing Guide for {z}**\n\n"
            f"**Annual herbs** (replant each year): basil, cilantro, dill, parsley, chervil\n"
            f"**Perennial herbs** (plant once): oregano, thyme, rosemary, sage, chives, mint, lovage\n\n"
            f"**Basil:** Plant after last frost ({climate.last_spring_frost_date}), full sun, warm soil. "
            f"Pinch flower buds immediately when they appear — once it bolts, flavor declines fast.\n\n"
            f"**Cilantro:** Bolts quickly in heat. Sow every 3 weeks for continuous harvest. "
            f"Let some bolt to collect coriander seed and it will self-sow next year.\n\n"
            f"**Rosemary/thyme/sage:** Full sun, excellent drainage, minimal water once established. "
            f"In Zone {climate.hardiness_zone}, rosemary may be marginally hardy — mulch heavily or bring inside if temps drop below 10°F.\n\n"
            f"**Mint:** Grow in a container or it will take over your entire garden. Seriously.\n\n"
            f"**Harvest:** Snip stems from the top regularly. Frequent harvesting makes plants bushier and more productive."
        )

    # ── Homesteader scenarios ─────────────────────────────────

    def _homesteader_chickens(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🐔 **Backyard Chickens Guide for {z}**\n\n"
            f"**Before you start:** Check local zoning and HOA rules on flock size, coop setbacks, and rooster restrictions.\n\n"
            f"**Flock size:** Start with 4–6 hens. Expect 3–5 eggs per hen per week in peak season.\n\n"
            f"**Coop requirements:**\n"
            f"- 4 sq ft per bird inside the coop (more is better)\n"
            f"- 10 sq ft per bird in the outdoor run\n"
            f"- Use hardware cloth (NOT chicken wire) — 1/2\" mesh hardware cloth stops raccoons and weasels\n"
            f"- 1 nesting box per 3–4 hens\n"
            f"- Roost bar at least 1–2 feet above the floor (chickens sleep on bars, not on the ground)\n\n"
            f"**Breeds for Zone {climate.hardiness_zone}:**\n"
            f"- Cold-hardy: Rhode Island Red, Australorp, Orpington, Plymouth Rock, Wyandotte\n"
            f"- Heat-tolerant: Leghorn, Andalusian, Egyptian Fayoumi\n\n"
            f"**Feed:** Layer pellets + free-choice oyster shell (for strong eggshells) + grit. "
            f"Supplement with garden scraps, mealworms, and grass. Avoid: raw potatoes, onions, avocado, chocolate.\n\n"
            f"**Winter care:** Deep litter method (pile bedding up all winter, clean in spring). "
            f"Ensure ventilation WITHOUT drafts. Add a heated water base to prevent freeze.\n\n"
            f"**Garden integration:** Chicken tractor (movable coop) on fallow beds clears weeds and fertilizes before planting season."
        )

    def _homesteader_compost(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"♻️ **Compost & Soil Fertility Guide for {z}**\n\n"
            f"**Your native soil:** {soil.native_texture}, pH {soil.native_ph_range}\n\n"
            f"**3-Bin Compost System:**\n"
            f"- **Bin 1 (Adding):** Layer browns (straw, dry leaves, cardboard) and greens (kitchen scraps, chicken manure, grass) at 30:1 C:N ratio\n"
            f"- **Bin 2 (Active):** Turn with a fork weekly; the pile should feel like a wrung-out sponge and feel warm inside\n"
            f"- **Bin 3 (Finished):** Sift and apply 1–2 inches to beds each spring\n"
            f"Finished compost in 2–4 months with weekly turning; 6–12 months if passive.\n\n"
            f"**Vermicomposting (worm bin):** For kitchen scraps indoors. "
            f"Red wigglers process food waste into concentrated castings — the best fertilizer you can make.\n\n"
            f"**Cover crops** (plant after fall harvest):\n"
            f"- Winter rye: suppresses weeds, protects soil, adds organic matter\n"
            f"- Crimson clover: fixes 60–150 lbs of nitrogen per acre\n"
            f"- Buckwheat (summer fallow): smothers weeds, feeds pollinators, mows under in 30–45 days\n\n"
            f"**Chicken manure:** High nitrogen — hot compost for 3–6 months before applying to food crops."
        )

    def _homesteader_fruit(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🍎 **Fruit Trees & Perennial Crops for {z}**\n\n"
            f"**Best time to plant:** Early spring while trees are still dormant (bare-root stock is cheapest). "
            f"Plant before {climate.last_spring_frost_date}.\n\n"
            f"**Tree selection for Zone {climate.hardiness_zone}:**\n"
            f"- **Apples:** Most cold-hardy tree fruit. Choose disease-resistant varieties: Liberty, Enterprise, Honeycrisp, Goldrush\n"
            f"- **Pears:** Very hardy; Asian pears are often easier than European types\n"
            f"- **Peaches/Nectarines:** Need 700–1,000 chill hours; check zone compatibility\n"
            f"- **Plums:** Japanese plums for warmer zones; American/European for colder\n"
            f"- **Blueberries:** Need acidic soil (pH 4.5–5.5); pair 2+ varieties for cross-pollination\n"
            f"- **Raspberries & Blackberries:** Very cold-hardy; spread aggressively if not contained\n\n"
            f"**Spacing:**\n"
            f"- Standard apple/pear: 15–20 ft apart\n"
            f"- Semi-dwarf: 10–12 ft\n"
            f"- Dwarf: 6–8 ft (needs staking permanently)\n\n"
            f"**First year rule:** Remove ALL fruit the first year to force root establishment. "
            f"One year of patience = decades of better production.\n\n"
            f"**Pruning:** Prune while dormant (late winter, before buds break). "
            f"Open vase shape for stone fruits; modified central leader for apples."
        )

    def _homesteader_preserve(self, query, soil, climate, ext, st_upper, req, natives):
        return (
            f"🫙 **Food Preservation Guide**\n\n"
            f"**Water-bath canning** (high-acid foods only):\n"
            f"- Safe for: tomatoes (add lemon juice), pickles, jams, jellies, fruit\n"
            f"- Process time: 10–45 minutes depending on jar size and product\n"
            f"- Required equipment: large pot, canning rack, jar lifter, lids\n\n"
            f"**Pressure canning** (low-acid foods):\n"
            f"- Required for: green beans, corn, meats, soups, mixed vegetables\n"
            f"- Never water-bath can low-acid foods — risk of botulism\n"
            f"- A weighted-gauge pressure canner costs $80–150 and lasts decades\n\n"
            f"**Freezing:**\n"
            f"- Blanch vegetables first (1–3 min in boiling water, then ice bath) to preserve color and texture\n"
            f"- Vacuum-seal for best quality; freezer bags work fine for 3–6 months\n"
            f"- Best candidates: greens, beans, corn, berries, pesto, cooked soups\n\n"
            f"**Drying/Dehydrating:**\n"
            f"- Dehydrate herbs at 95–105°F (higher kills volatile oils)\n"
            f"- Tomatoes at 135°F for 8–12 hours; peppers at 125°F\n"
            f"- Store in airtight jars away from light and heat\n\n"
            f"**Root Cellaring:**\n"
            f"- Ideal conditions: 32–40°F, 85–95% humidity\n"
            f"- Potatoes, carrots, beets: store in damp sand or sawdust\n"
            f"- Winter squash and onions: 50–60°F, low humidity (cured first)\n\n"
            f"**Lacto-fermentation (easiest of all):**\n"
            f"- Sauerkraut, kimchi, pickles: just vegetables + salt + time, no special equipment\n"
            f"- 2% salt by weight, packed in a jar, submerged under brine — ready in 3–7 days"
        )

    def _homesteader_livestock(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🐐 **Small Livestock Guide for {z}**\n\n"
            f"**Easiest to start with (ranked by ease):** Chickens → Ducks → Rabbits → Goats → Pigs → Cattle\n\n"
            f"**Dairy Goats:**\n"
            f"- 2 does minimum (goats are social, never keep just one)\n"
            f"- Nigerian Dwarf: smaller, friendly, 1–2 qts milk/day, manageable for beginners\n"
            f"- LaMancha or Nubian: 1–2 gallons/day but need more space\n"
            f"- Fencing: goats escape almost anything — use 4-foot welded wire with t-posts every 8 feet\n\n"
            f"**Pigs:**\n"
            f"- Easiest large livestock — one or two feeder pigs (April–October) is a great start\n"
            f"- Electric fence (2 strands, 6 and 12 inches off ground) is sufficient\n"
            f"- Feed: commercial grain + garden scraps + whey (if you have dairy)\n"
            f"- Expected yield: one pig = 150–200 lbs of pork in 6 months\n\n"
            f"**General livestock notes:**\n"
            f"- Water: all livestock need clean water year-round; heated buckets in winter\n"
            f"- Zoning: check county rules for each species before investing\n"
            f"- Processing: locate your local USDA-inspected processor before you need it"
        )

    def _homesteader_water(self, query, soil, climate, ext, st_upper, req, natives):
        return (
            f"💧 **Homestead Water Systems**\n\n"
            f"**Rainwater harvesting:**\n"
            f"- A 1,000 sq ft roof collects ~600 gallons per 1 inch of rain\n"
            f"- First-flush diverter removes initial dirty runoff (leaves, bird waste)\n"
            f"- Check state law: some western states restrict rainwater collection\n"
            f"- 1,500-gallon poly tank + simple gravity drip works for a kitchen garden\n\n"
            f"**Irrigation efficiency:**\n"
            f"- Drip irrigation uses 30–50% less water than sprinklers\n"
            f"- Mulch 2–3 inches deep reduces irrigation needs by another 40–50%\n"
            f"- Water early morning (5–7am) to minimize evaporation\n\n"
            f"**Well water:**\n"
            f"- Annual water test for coliform bacteria and nitrates is the minimum\n"
            f"- High iron or sulfur is common in rural wells — a whole-house filter may be needed for garden irrigation\n\n"
            f"**Gray water reuse:**\n"
            f"- Laundry-to-landscape: route washing machine gray water to fruit trees or ornamentals\n"
            f"- Check your state's gray water regulations first"
        )

    def _homesteader_bees(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🐝 **Beekeeping Guide for {z}**\n\n"
            f"**Getting started:**\n"
            f"- Take a beginner beekeeping course before buying anything (local bee club or state beekeepers association)\n"
            f"- Start with 2 hives — if one fails you have a comparison and can re-queen from the other\n"
            f"- Order package bees or nucleus (nuc) colonies in January–February for April–May delivery\n\n"
            f"**Equipment basics:**\n"
            f"- Langstroth hive with 2 deep brood boxes + 1 honey super to start\n"
            f"- Veil and gloves (always), smoker, hive tool, brush\n"
            f"- Startup cost: ~$300–500 per hive for good-quality equipment\n\n"
            f"**Zone {climate.hardiness_zone} timing:**\n"
            f"- Install package bees when temps are consistently above 50°F nights\n"
            f"- Inspect every 7–10 days through spring and summer\n"
            f"- Prepare for winter by ensuring 60–80 lbs of honey stores (or feed 2:1 sugar syrup in fall)\n\n"
            f"**Integrated Pest Management:**\n"
            f"- Varroa mite is the primary threat — test monthly with an alcohol wash or sticky board\n"
            f"- Treat when mite levels exceed 2 per 100 bees\n"
            f"- Oxalic acid (Apivar strips) is the most effective and least disruptive treatment"
        )

    def _homesteader_energy(self, query, soil, climate, ext, st_upper, req, natives):
        return (
            f"⚡ **Off-Grid & Homestead Energy**\n\n"
            f"**Solar:**\n"
            f"- A 3–5 kW system can power a basic homestead (lights, well pump, refrigerator, small appliances)\n"
            f"- Battery storage (LiFePO4 batteries are safest and most durable) is essential for nighttime use\n"
            f"- Grid-tie with net metering is the most cost-effective if utility connection exists\n\n"
            f"**Propane:**\n"
            f"- Most cost-effective fuel for cooking, water heating, and backup generator\n"
            f"- 500-gallon tank serves most homesteads; fill in spring (off-season pricing is lower)\n\n"
            f"**Wood heating:**\n"
            f"- A well-seasoned cord of hardwood produces as much heat as 150–200 gallons of propane\n"
            f"- Season firewood 1–2 years before burning; split and stack with airflow\n"
            f"- EPA-certified wood stove or insert significantly reduces creosote buildup vs open fireplace\n\n"
            f"**Passive design first:**\n"
            f"- Insulation, thermal mass, and proper south-facing windows do more than any equipment\n"
            f"- A well-insulated root cellar maintains 35–50°F year-round with no energy input"
        )

    # ── Small farm scenarios ──────────────────────────────────

    # ── Small-farm / urban grower scenarios ───────────────────

    def _urban_grower_food_access(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🤝 **Connecting Chicago Growers & Neighbors — {z}**\n\n"
            f"Urban farms succeed when produce reaches people who need it — not only full-price market shoppers.\n\n"
            f"**Sales & sharing models:**\n"
            f"- Farmers market booths with **Illinois Link / SNAP Match**\n"
            f"- Sliding-scale CSA boxes and pay-what-you-can farm stands\n"
            f"- Wholesale to corner stores, clinics, or school partners\n"
            f"- Surplus donations coordinated with pantries and mutual-aid groups\n\n"
            f"**Practice tip:** Track which neighborhoods you serve and price a portion of harvest "
            f"for access buyers. Groups like Urban Growers Collective blend production, jobs, and "
            f"food justice — use this map to find peer farms and market sites nearby."
        )

    def _urban_grower_mobile(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🚌 **Mobile Markets & Link Match Sales — {z}**\n\n"
            f"Chicago has used bus- and van-based markets (e.g. Fresh Moves–style models) to bring "
            f"produce into areas with fewer grocery options.\n\n"
            f"**If you sell or partner:**\n"
            f"- Confirm Link/EBT terminal setup and Link Match rules with the market host\n"
            f"- Stock staples neighbors request (greens, onions, tomatoes, herbs) plus cultural favorites\n"
            f"- Post clear hours, stop locations, and payment signs\n"
            f"- Coordinate with clinics, libraries, or churches for reliable stop hosts\n\n"
            f"Filter this app’s map for SNAP/Link sites and urban farms near your route."
        )

    def _urban_grower_training(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"📋 **Urban Grower Training Pathways — {z}**\n\n"
            f"**Typical Chicago pathway:**\n"
            f"1. Volunteer or plot at a community garden / urban farm\n"
            f"2. Seasonal apprenticeship or crew role (production + markets)\n"
            f"3. Extension or nonprofit workshops (soil safety, IPM, business basics)\n"
            f"4. Lead a bed block, farm stand, or youth crew\n\n"
            f"**Skills to build:** raised-bed production, wash/pack food safety, Link Match market "
            f"sales, community outreach, and basic bookkeeping.\n\n"
            f"Look up Urban Growers Collective and peer farms on the map for live examples of "
            f"training + food-access work on the South and West Sides."
        )

    def _farm_business(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"📋 **Small Farm Business Guide for {z}**\n\n"
            f"**Federal programs (free money + free help):**\n"
            f"- **USDA FSA Microloan:** Up to $50,000, no farm experience required, streamlined application\n"
            f"- **NRCS EQIP:** Cost-share up to 75% for high tunnels, irrigation, cover crops, fencing\n"
            f"- **Beginning Farmer programs:** Often provide additional priority in EQIP and other programs\n"
            f"- Find your local FSA/NRCS service center: farmers.gov\n\n"
            f"**Revenue projections (ballpark):**\n"
            f"- CSA (20 members × $25/week × 20 weeks): $10,000/season\n"
            f"- Farmers market (1 market × $500 avg/Saturday × 20 weeks): $10,000/season\n"
            f"- Farm stand (self-serve, honor system): $5,000–15,000 depending on location\n"
            f"- Restaurant wholesale: $500–2,000/week per account, but more work and waste\n\n"
            f"**First-year focus:** Pick ONE sales channel and do it well before diversifying.\n\n"
            f"**Simple accounting:** Track every expense and sale in a spreadsheet from day one. "
            f"Your accountant (get one) needs this to maximize farm deductions. "
            f"Schedule F (IRS) allows significant expense deductions for legitimate farm operations.\n\n"
            f"*Disclaimer: General guidance only — consult an accountant and your local FSA office for your specific situation.*"
        )

    def _farm_equipment(self, query, soil, climate, ext, st_upper, req, natives):
        return (
            f"🚜 **Small Farm Equipment Guide**\n\n"
            f"**Minimum viable toolkit for 1–5 acres of vegetables:**\n\n"
            f"**Tillage:**\n"
            f"- BCS walk-behind tractor + tiller attachment: $2,500–4,500 (handles 1–3 acres efficiently)\n"
            f"- Broadfork (6-tine): $150–250 — for no-till bed prep and aeration without inversion\n"
            f"- Wheel hoe with stirrup blade: $100–150 — fastest weed cultivation between rows\n\n"
            f"**Water:**\n"
            f"- Drip tape on a timer: $500–1,500/acre. Biggest labor saver on the farm.\n"
            f"- Header tank + simple soaker timer: lower cost option for <1 acre\n\n"
            f"**Season Extension:**\n"
            f"- Low tunnel (caterpillar) with 9-gauge wire hoops + Agribon row cover: $0.15–0.25/linear ft\n"
            f"- High tunnel (20×96 ft): $3,000–8,000 depending on structure. Best ROI in farming.\n\n"
            f"**Harvest & Pack:**\n"
            f"- Wash/pack station: stainless or food-grade surfaces with drain, cold running water\n"
            f"- Walk-in cooler (converted chest freezer with Inkbird controller): $200–400 DIY\n\n"
            f"**Priority order:** Irrigation → row covers/low tunnels → walk-in cooler → high tunnel → tractor"
        )

    def _farm_rotation(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🌾 **Crop Rotation & Soil Health for {z}**\n\n"
            f"**Native soil:** {soil.native_texture}, pH {soil.native_ph_range}\n\n"
            f"**4-Year Market Garden Rotation:**\n"
            f"1. **Legumes** (peas, beans, cover crop clover) — fix nitrogen, light feeders\n"
            f"2. **Brassicas** (broccoli, cabbage, kale, turnips) — break disease cycles, medium feeders\n"
            f"3. **Nightshades** (tomatoes, peppers, eggplant) — heavy feeders, benefit from legume N\n"
            f"4. **Cucurbits + Roots** (squash, cucumbers, carrots, beets) — moderate feeders, loosen soil\n\n"
            f"**Cover crop calendar for Zone {climate.hardiness_zone}:**\n"
            f"- After last harvest: winter rye or winter wheat (sow by mid-fall)\n"
            f"- Spring fallow: crimson clover or hairy vetch (mow in 60 days, fixes 100+ lbs N/acre)\n"
            f"- Summer fallow: buckwheat (fast cover, ready to mow in 4–6 weeks, excellent pollinator plant)\n\n"
            f"**Tarp method:** After mowing cover crops, apply a silage tarp for 3–6 weeks. "
            f"Kills everything below, leaving beds ready to plant with zero tillage. Huge labor saver.\n\n"
            f"**Organic certification path:** 3-year transition period (no prohibited substances for 3 years before first certified crop). "
            f"Contact your state organic certifier early — paperwork starts before the 3 years end."
        )

    def _farm_sales(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🧺 **Direct Sales & Market Strategy for {z}**\n\n"
            f"**Farmers markets:**\n"
            f"- Apply 2–6 months ahead of season (most markets open applications in fall/winter)\n"
            f"- Budget: $25–100/week booth fee; bring $300–600 in product for a good Saturday\n"
            f"- Display matters — tiered wooden shelves and clear labeling outperform table dumps\n"
            f"- Accept cards (Square, Clover) — you'll lose 30–40% of sales without card processing\n\n"
            f"**CSA (Community Supported Agriculture):**\n"
            f"- Collect payment in full in March for June–October shares — preseason cash flow is the point\n"
            f"- 20–50 members is a manageable starting size\n"
            f"- Weekly box value: $20–35 gives customers perceived value; $25 is the sweet spot\n\n"
            f"**Farm stand:**\n"
            f"- Honor system works surprisingly well in rural areas (80–95% payment rate)\n"
            f"- Solar-powered camera improves honesty and provides security\n"
            f"- Best products: eggs, honey, jam, flowers, pre-washed salad mix (highest margin items)\n\n"
            f"**Restaurant wholesale:**\n"
            f"- Send a weekly availability sheet to 3–5 chefs on Monday mornings\n"
            f"- Deliver on Thursday/Friday for weekend service\n"
            f"- Minimum order ($50–100) saves you from $8 deliveries that waste your time\n\n"
            f"**Chicago Ag Connect listing:** Create a vendor profile and log your market presence weekly — "
            f"local shoppers use this to find exactly what you grow."
        )

    def _farm_labor(self, query, soil, climate, ext, st_upper, req, natives):
        return (
            f"👥 **Farm Labor & Help**\n\n"
            f"**WWOOF & WorkAway:**\n"
            f"- Worldwide Opportunities on Organic Farms — volunteers work 25–30 hrs/week in exchange for room/board\n"
            f"- Great for seasonal peaks; requires housing, clear task structure, and a welcoming culture\n\n"
            f"**Farm apprentices:**\n"
            f"- 1-year paid apprenticeships attract serious young farmers\n"
            f"- Post on FarmMatch, Sustainable Agriculture Job Board, or your state farming organization\n"
            f"- Budget $12–15/hr plus housing or $1,500–2,000/month stipend\n\n"
            f"**Seasonal day labor:**\n"
            f"- Great for harvest peaks (planting transplants, garlic, harvesting crops)\n"
            f"- Contact your local H-2A program coordinator if you need guaranteed labor\n\n"
            f"**Reduce labor needs first:**\n"
            f"- A broadfork + tarping system takes 1 person instead of 3 for bed prep\n"
            f"- Drip irrigation + timer eliminates daily hand watering\n"
            f"- Batch harvesting + cold storage means fewer market trips\n"
            f"- Most profitable small farms run on 1–2 full-time equivalent workers per acre"
        )

    def _farm_ipm(self, query, soil, climate, ext, st_upper, req, natives):
        pest_list = ext.get("pest_watch", [])
        regional_pests = ", ".join(pest_list[:5]) if pest_list else "aphids, flea beetles, and fungal diseases"
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🛡️ **Farm-Scale IPM (Integrated Pest Management) for {z}**\n\n"
            f"**Regional key pests:** {regional_pests}\n\n"
            f"**IPM hierarchy:**\n"
            f"1. **Prevention:** Healthy soil, crop rotation, proper plant spacing for airflow\n"
            f"2. **Cultural controls:** Row covers, resistant varieties, timed planting to avoid pest peaks\n"
            f"3. **Biological controls:** Release or attract predatory insects; maintain habitat strips\n"
            f"4. **Mechanical controls:** Traps, hand removal, sticky barriers\n"
            f"5. **Organic sprays:** Last resort; apply in evening to protect pollinators\n\n"
            f"**Weekly scouting protocol:**\n"
            f"- Walk each field block every 5–7 days\n"
            f"- Record pest pressure by crop and date\n"
            f"- Action threshold: spray only when pest level threatens economic damage\n\n"
            f"**Beneficial insect habitat:**\n"
            f"- Permanent insectary strips (5–10% of field area) in dill, fennel, yarrow, native wildflowers\n"
            f"- Leave field margins unmowed until after bloom\n\n"
            f"**Organic certification note:** All pest control materials must be OMRI-listed or approved by your certifier before application."
        )

    def _farm_season_extension(self, query, soil, climate, ext, st_upper, req, natives):
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"🏗️ **Season Extension Guide for {z}**\n\n"
            f"**Row covers (Agribon or Reemay):**\n"
            f"- AG-19: +4–6°F frost protection, 85% light transmission. Use over transplants.\n"
            f"- AG-30: +8°F frost protection, 70% light. Use in fall/early spring.\n"
            f"- AG-50: Heavy frost protection, 50% light. Winter tunnel use only.\n\n"
            f"**Low tunnels (caterpillar tunnels):**\n"
            f"- 9-gauge wire hoops + row cover: push last frost 3–4 weeks earlier\n"
            f"- Set up in 30 min per 50-foot bed\n"
            f"- Great for spring greens, early tomato transplants, fall spinach\n\n"
            f"**High tunnels:**\n"
            f"- 20×96 ft Gothic high tunnel: typical price $3,000–8,000 erected\n"
            f"- Extends your growing season by 6–8 weeks on each end\n"
            f"- For Zone {climate.hardiness_zone}: can grow tomatoes until December and start in February\n"
            f"- NRCS EQIP often covers 50–75% of cost — apply in fall for next-year construction\n\n"
            f"**Heated greenhouse:**\n"
            f"- Significant operating cost — use only for high-value crops (microgreens, herbs, starts)\n"
            f"- Double-poly inflated with small blower reduces heat loss 30–40%\n\n"
            f"**Frost dates for {z}:** Last spring frost {climate.last_spring_frost_date}, "
            f"first fall frost {climate.first_fall_frost_date}. "
            f"With a high tunnel, shift both by 6–8 weeks."
        )

    # ── Generic fallbacks ─────────────────────────────────────

    def _fallback_kb_match(self, top_docs, soil, climate, st_upper, req):
        if not top_docs:
            return None
        matched_output = top_docs[0]["output"]
        z = self._zone_intro(climate, st_upper, req)
        return (
            f"**Agronomic Guidance for {z}:**\n\n"
            f"{matched_output}\n\n"
            f"📌 *Local note:* Native soil is {soil.native_texture} (pH {soil.native_ph_range}). "
            f"Your frost-free window is {climate.frost_free_days} days."
        )

    def _fallback_general(self, soil, climate, ext, st_upper, req):
        z = self._zone_intro(climate, st_upper, req)
        crops = ext.get("top_crops", ["tomatoes", "peppers", "squash"])
        crop_list = ", ".join(str(c) for c in crops[:5]) if crops else "tomatoes, peppers, squash, beans"
        return (
            f"🌱 **Local Agronomic Summary for {z}**\n\n"
            f"**Growing season:** {climate.last_spring_frost_date} → {climate.first_fall_frost_date} "
            f"({climate.frost_free_days} frost-free days)\n\n"
            f"**Native soil:** {soil.native_texture}, pH {soil.native_ph_range} ({soil.soil_series})\n"
            f"**Soil notes:** {soil.garden_suitability_summary}\n\n"
            f"**Top crops for your zone:** {crop_list}\n\n"
            f"**Getting started:**\n"
            f"- Select a spot with 6+ hours of direct sun\n"
            f"- Amend soil with 3–4 inches of compost before planting\n"
            f"- Plant warm-season crops 1–2 weeks after {climate.last_spring_frost_date}\n"
            f"- Ask me about any specific crop, pest, or technique and I'll give you detailed guidance."
        )

    # ── Main inference entry point ────────────────────────────

    def generate_response(self, req: AgronomySLMRequest) -> AgronomySLMResponse:
        start_time = time.time()
        lat = req.latitude if req.latitude is not None else 41.8781
        lon = req.longitude if req.longitude is not None else -87.6298
        st_upper = resolve_state_code(req.state, lat, lon)

        advisory = generate_home_garden_advisory(
            latitude=lat,
            longitude=lon,
            county_name=req.county,
            state_code=st_upper
        )

        ext = STATE_EXTENSIONS.get(st_upper, {})
        natives = ext.get("native_species", [])
        soil = advisory.soil
        climate = advisory.climate

        context_injected = {
            "state": st_upper,
            "county": req.county or "Regional",
            "mode": req.mode,
            "hardiness_zone": climate.hardiness_zone,
            "last_spring_frost": climate.last_spring_frost_date,
            "first_fall_frost": climate.first_fall_frost_date,
            "frost_free_days": climate.frost_free_days,
            "soil_texture": soil.native_texture,
            "native_ph": soil.native_ph_range,
            "ecoregion": ext.get("ecoregion", "Temperate").title()
        }

        query = req.prompt.strip().lower()
        query_tokens = self._tokenize(query)
        mode = req.mode if req.mode in ("gardener", "homesteader", "small_farm") else "gardener"

        # Knowledge base semantic search
        best_matches: List[Tuple[float, Dict[str, Any]]] = []
        for doc in self.knowledge_base:
            combined = f"{doc.get('instruction', '')} {doc.get('input', '')} {doc.get('output', '')}"
            s = self._score_relevance(query_tokens, combined, st_upper)
            if s > 0.3:
                best_matches.append((s, doc))
        best_matches.sort(key=lambda x: x[0], reverse=True)
        top_docs = [m[1] for m in best_matches[:3]]

        sources = [
            f"USDA Soil Survey & SSURGO ({st_upper})",
            f"State University Extension ({ext.get('ecoregion', 'Regional')})",
            "NOAA 30-Year Climate Normals",
        ]
        if mode == "homesteader":
            sources.append("ATTRA/NCAT Sustainable Agriculture")
        if mode == "small_farm":
            sources.append("USDA FSA & NRCS Programs")

        # Dispatch to scenario handler
        handler_name = None
        if mode == "homesteader":
            handler_name = self._match_scenario(query, HOMESTEADER_SCENARIOS)
            if not handler_name:
                handler_name = self._match_scenario(query, GARDENER_SCENARIOS)
        elif mode == "small_farm":
            handler_name = self._match_scenario(query, SMALL_FARM_SCENARIOS)
            if not handler_name:
                handler_name = self._match_scenario(query, GARDENER_SCENARIOS)
        else:
            handler_name = self._match_scenario(query, GARDENER_SCENARIOS)

        args = (query, soil, climate, ext, st_upper, req, natives)

        if handler_name and hasattr(self, handler_name):
            response_text = getattr(self, handler_name)(*args)
        else:
            kb_response = self._fallback_kb_match(top_docs, soil, climate, st_upper, req)
            response_text = kb_response if kb_response else self._fallback_general(soil, climate, ext, st_upper, req)

        inference_time_ms = round((time.time() - start_time) * 1000, 2)

        return AgronomySLMResponse(
            response=response_text,
            model_name=f"BackyardAg-Agronomy-SLM-v2-{mode}",
            context_injected=context_injected,
            inference_time_ms=inference_time_ms,
            sources_referenced=sources
        )


# Global singleton
agronomy_slm_service = AgronomySLMEngine()
