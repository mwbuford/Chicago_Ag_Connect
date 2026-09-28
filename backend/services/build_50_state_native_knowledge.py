"""
Unified 50-State Agronomic, Climate, Cooperative Extension, and Native Plant Knowledgebase.
Covers all 50 US States + DC with Land-Grant Universities, Regional Soils, Cultivars, and Native Species.
"""
import json
from pathlib import Path

# Helper generator for native species lists by ecoregion
ECOREGION_NATIVE_PLANTS = {
    "MIDWEST": [
        {
            "common_name": "Purple Coneflower",
            "botanical_name": "Echinacea purpurea",
            "plant_category": "Native Wildflower & Pollinator",
            "ecoregion_benefits": "Deep taproot penetrates prairie clay; vital nectar hub for native bumblebees and goldfinches in late summer.",
            "sun_and_soil": "Full Sun to Light Shade; thrives in rich prairie loam and clay.",
            "water_needs": "Low / Drought-Tolerant (Once established)",
            "best_garden_use": "Perennial borders, vegetable garden pollinator strips, cut flower beds."
        },
        {
            "common_name": "Prairie Blazing Star",
            "botanical_name": "Liatris pycnostachya",
            "plant_category": "Native Wildflower & Pollinator",
            "ecoregion_benefits": "Spectacular purple flower spikes attract monarch butterflies and beneficial predatory wasps that protect vegetables.",
            "sun_and_soil": "Full Sun; thrives in moist to average loam.",
            "water_needs": "Moderate",
            "best_garden_use": "Vertical accent behind raised beds, butterfly gardens."
        },
        {
            "common_name": "Serviceberry / Juneberry",
            "botanical_name": "Amelanchier laevis",
            "plant_category": "Native Edible Berry / Fruit",
            "ecoregion_benefits": "One of the earliest spring nectar sources; produces delicious sweet dark purple blueberry-like fruit in June.",
            "sun_and_soil": "Full Sun to Part Shade; well-drained loam or clay loam.",
            "water_needs": "Moderate",
            "best_garden_use": "Backyard edible landscaping, bird habitat, small specimen tree."
        },
        {
            "common_name": "Wild Bergamot / Bee Balm",
            "botanical_name": "Monarda fistulosa",
            "plant_category": "Native Wildflower & Herb",
            "ecoregion_benefits": "Aromatic foliage naturally repels garden pests while lilac blooms attract hummingbirds and native bees.",
            "sun_and_soil": "Full Sun to Part Shade; tolerates diverse garden soils.",
            "water_needs": "Low to Moderate",
            "best_garden_use": "Companion planting around tomato beds, herbal tea garden."
        }
    ],
    "MID_ATLANTIC": [
        {
            "common_name": "Virginia Bluebells",
            "botanical_name": "Mertensia virginica",
            "plant_category": "Native Woodland Perennial",
            "ecoregion_benefits": "Earliest spring woodland bloomer providing critical early nectar for emerging queen bumblebees.",
            "sun_and_soil": "Part Shade to Full Shade; rich, moist organic soil.",
            "water_needs": "Moderate to Moist",
            "best_garden_use": "Shady garden borders, under deciduous fruit trees, spring bulbs companion."
        },
        {
            "common_name": "American Pawpaw",
            "botanical_name": "Asimina triloba",
            "plant_category": "Native Fruit Tree",
            "ecoregion_benefits": "Largest native edible fruit in North America (custard-banana flavor); sole larval host of the Zebra Swallowtail butterfly.",
            "sun_and_soil": "Full Sun (mature) or Part Shade; fertile riverbank loam.",
            "water_needs": "Moderate to Moist",
            "best_garden_use": "Edible orchard, naturalized backyard canopy, wildlife garden."
        },
        {
            "common_name": "American Elderberry",
            "botanical_name": "Sambucus canadensis",
            "plant_category": "Native Edible Berry / Shrub",
            "ecoregion_benefits": "Huge umbrella clusters of white flowers followed by antioxidant-rich elderberries; feeds over 40 species of native birds.",
            "sun_and_soil": "Full Sun to Part Sun; moist soils and garden borders.",
            "water_needs": "Moderate to High",
            "best_garden_use": "Edible windbreaks, rain gardens, natural privacy hedgerows."
        },
        {
            "common_name": "Cardinal Flower",
            "botanical_name": "Lobelia cardinalis",
            "plant_category": "Native Wildflower & Pollinator",
            "ecoregion_benefits": "Intense scarlet-red blooms specifically adapted for ruby-throated hummingbird pollination.",
            "sun_and_soil": "Full Sun to Part Shade; moist to wet soils.",
            "water_needs": "Moist / Riparian",
            "best_garden_use": "Rain gardens, low wet garden spots, hummingbird attraction."
        }
    ],
    "SOUTHEAST": [
        {
            "common_name": "Butterfly Weed",
            "botanical_name": "Asclepias tuberosa",
            "plant_category": "Native Wildflower & Pollinator",
            "ecoregion_benefits": "Vibrant fiery orange blooms; premier host plant for Monarch butterfly caterpillars and extreme drought tolerance.",
            "sun_and_soil": "Full Sun; well-drained sandy or red clay soil.",
            "water_needs": "Low / Drought-Tolerant",
            "best_garden_use": "Sunny borders, pollinator sanctuary, perennial garden corners."
        },
        {
            "common_name": "Rabbiteye Blueberry",
            "botanical_name": "Vaccinium virgatum",
            "plant_category": "Native Edible Berry / Shrub",
            "ecoregion_benefits": "Bred by nature for hot southeastern summers and acidic soils; heavy producer of sweet summer fruit.",
            "sun_and_soil": "Full Sun; acidic soil (pH 4.5 - 5.5) rich in pine mulch.",
            "water_needs": "Moderate",
            "best_garden_use": "Fruiting shrub borders, edible hedge, container gardens."
        },
        {
            "common_name": "Purple Passionflower (Maypop)",
            "botanical_name": "Passiflora incarnata",
            "plant_category": "Native Edible Vine & Pollinator",
            "ecoregion_benefits": "Exotic intricate purple blooms followed by edible aromatic passionfruit; larval host for Gulf Fritillary butterflies.",
            "sun_and_soil": "Full Sun; well-drained sandy or loam soil.",
            "water_needs": "Low to Moderate",
            "best_garden_use": "Fence climbing, garden trellises, wildlife trellis."
        },
        {
            "common_name": "Stokes Aster",
            "botanical_name": "Stokesia laevis",
            "plant_category": "Native Wildflower & Groundcover",
            "ecoregion_benefits": "Evergreen southern foliage with 3-inch sky-blue cornflower blooms; heat and humidity resilient.",
            "sun_and_soil": "Full Sun to Part Sun; well-drained soil.",
            "water_needs": "Low / Drought-Tolerant",
            "best_garden_use": "Front of garden borders, rock gardens, container accent."
        }
    ],
    "NORTHEAST": [
        {
            "common_name": "Eastern Red Columbine",
            "botanical_name": "Aquilegia canadensis",
            "plant_category": "Native Wildflower & Pollinator",
            "ecoregion_benefits": "Red and yellow nodding bells bloom in May; key early nectar source for returning hummingbirds.",
            "sun_and_soil": "Part Shade to Full Sun; rocky or sandy loam.",
            "water_needs": "Low to Moderate",
            "best_garden_use": "Rock gardens, shady garden edges, woodland borders."
        },
        {
            "common_name": "Highbush Blueberry",
            "botanical_name": "Vaccinium corymbosum",
            "plant_category": "Native Edible Berry / Shrub",
            "ecoregion_benefits": "Native northeastern superfood shrub; brilliant scarlet autumn foliage after delicious summer berry harvest.",
            "sun_and_soil": "Full Sun; acidic organic soil (pH 4.5 - 5.5).",
            "water_needs": "Moderate",
            "best_garden_use": "Edible landscaping, raised acid beds, boundary hedgerows."
        },
        {
            "common_name": "Spotted Joe-Pye Weed",
            "botanical_name": "Eutrochium maculatum",
            "plant_category": "Native Wildflower & Pollinator",
            "ecoregion_benefits": "Magnificent vanilla-scented mauve flower domes that act as a magnet for swallowtail butterflies.",
            "sun_and_soil": "Full Sun to Light Shade; moist fertile soil.",
            "water_needs": "Moderate to Moist",
            "best_garden_use": "Back of perennial border, rain gardens, moisture retention zones."
        },
        {
            "common_name": "Winterberry Holly",
            "botanical_name": "Ilex verticillata",
            "plant_category": "Native Shrub & Wildlife",
            "ecoregion_benefits": "Deciduous native holly that produces thousands of bright ruby-red winter berries feeding songbirds through snow.",
            "sun_and_soil": "Full Sun to Part Shade; damp to wet soils.",
            "water_needs": "Moderate to High",
            "best_garden_use": "Winter garden interest, rain gardens, wildlife refuge."
        }
    ],
    "GREAT_PLAINS": [
        {
            "common_name": "Texas Bluebonnet",
            "botanical_name": "Lupinus texensis",
            "plant_category": "Native Wildflower & Nitrogen Fixer",
            "ecoregion_benefits": "Fixes atmospheric nitrogen directly into the soil, naturally enriching native topsoil while feeding spring honeybees.",
            "sun_and_soil": "Full Sun; well-drained alkaline limestone or gravelly soil.",
            "water_needs": "Low / Drought-Tolerant",
            "best_garden_use": "Spring wildflower meadow, front borders, companion cover crop."
        },
        {
            "common_name": "Blanket Flower",
            "botanical_name": "Gaillardia pulchella",
            "plant_category": "Native Wildflower & Pollinator",
            "ecoregion_benefits": "Thrives through 100°F+ Great Plains heat with continuous fiery red-and-gold blooms from May to frost.",
            "sun_and_soil": "Full Sun; thrives in poor, sandy or rocky soils.",
            "water_needs": "Extremely Low / Drought-Tolerant",
            "best_garden_use": "Dry garden borders, drought-proof flower beds, cottage borders."
        },
        {
            "common_name": "Purple Prairie Clover",
            "botanical_name": "Dalea purpurea",
            "plant_category": "Native Wildflower & Soil Builder",
            "ecoregion_benefits": "Deep taproots aerate tight subsoils; fixes nitrogen and produces dense cone-like purple flowers.",
            "sun_and_soil": "Full Sun; well-drained prairie soil.",
            "water_needs": "Low / Drought-Tolerant",
            "best_garden_use": "Soil restoration beds, pollinator gardens, native prairie strips."
        },
        {
            "common_name": "Mexican Hat (Upright Prairie Coneflower)",
            "botanical_name": "Ratibida columnifera",
            "plant_category": "Native Wildflower & Pollinator",
            "ecoregion_benefits": "Remarkably drought-resilient with unique sombrero-like flowers that attract native solitary bees.",
            "sun_and_soil": "Full Sun; dry to medium prairie soils.",
            "water_needs": "Low / Drought-Tolerant",
            "best_garden_use": "Dry wildflower meadows, perennial borders, roadside borders."
        }
    ],
    "SOUTHWEST": [
        {
            "common_name": "Desert Marigold",
            "botanical_name": "Baileya multiradiata",
            "plant_category": "Native Wildflower & Groundcover",
            "ecoregion_benefits": "Bright sunny yellow blooms nearly year-round in arid heat; silvery foliage reflects desert UV radiation.",
            "sun_and_soil": "Full Sun; gravelly, caliche, or sandy desert soils.",
            "water_needs": "Extremely Low / Desert Adapted",
            "best_garden_use": "Xeriscape garden, rock beds, perimeter pollinator edging."
        },
        {
            "common_name": "Desert Willow",
            "botanical_name": "Chilopsis linearis",
            "plant_category": "Native Flowering Tree / Shrub",
            "ecoregion_benefits": "Produces fragrant trumpet-shaped orchid-like flowers through triple-digit summer heat, feeding native desert hummingbirds.",
            "sun_and_soil": "Full Sun; well-draining desert soil.",
            "water_needs": "Low / Drought-Tolerant",
            "best_garden_use": "Patio shade specimen, small garden tree, wildlife boundary."
        },
        {
            "common_name": "Chiltepin (Wild Bird Pepper)",
            "botanical_name": "Capsicum annuum var. glabriusculum",
            "plant_category": "Native Edible Heritage Pepper",
            "ecoregion_benefits": "The wild ancestor of all domesticated peppers; perennial desert bush producing intense, fruity mini fiery peppers.",
            "sun_and_soil": "Part Shade (filtered sun under desert trees); well-drained soil.",
            "water_needs": "Low to Moderate",
            "best_garden_use": "Edible herb garden, container plant, native food preserve."
        },
        {
            "common_name": "Parry's Agave",
            "botanical_name": "Agave parryi",
            "plant_category": "Native Desert Succulent",
            "ecoregion_benefits": "Architectural compact blue-gray rosettes; extreme cold-hardiness (-20°F) and virtually zero water requirement.",
            "sun_and_soil": "Full Sun; well-drained gravelly or sandy soil.",
            "water_needs": "Extremely Low",
            "best_garden_use": "Architectural focal point, xeriscape landscape, rock garden."
        }
    ],
    "WEST_COAST": [
        {
            "common_name": "California Poppy",
            "botanical_name": "Eschscholzia californica",
            "plant_category": "Native Wildflower & Pollinator",
            "ecoregion_benefits": "The iconic golden state native; self-seeds readily, thrives in lean soil, and provides abundant spring pollen.",
            "sun_and_soil": "Full Sun; well-drained poor to average soils.",
            "water_needs": "Low / Drought-Tolerant",
            "best_garden_use": "Spring borders, slopes, companion strips between vegetable beds."
        },
        {
            "common_name": "California Lilac",
            "botanical_name": "Ceanothus spp.",
            "plant_category": "Native Shrub & Nitrogen Fixer",
            "ecoregion_benefits": "Intense cobalt-blue blossoms with honey scent; fixes nitrogen in poor coastal soils and feeds native bees.",
            "sun_and_soil": "Full Sun; dry well-draining soil.",
            "water_needs": "Very Low (Avoid summer overwatering)",
            "best_garden_use": "Evergreen hedge, hillside stabilization, pollinator anchor."
        },
        {
            "common_name": "Western Serviceberry (Saskatoon)",
            "botanical_name": "Amelanchier alnifolia",
            "plant_category": "Native Edible Berry / Shrub",
            "ecoregion_benefits": "Cold-hardy Pacific native producing sweet, almond-blueberry flavored berries excellent for fresh eating and pies.",
            "sun_and_soil": "Full Sun to Part Shade; adaptable garden loam.",
            "water_needs": "Moderate",
            "best_garden_use": "Edible landscaping, wildlife hedgerow, fruit border."
        },
        {
            "common_name": "Douglas Aster",
            "botanical_name": "Symphyotrichum subspicatum",
            "plant_category": "Native Wildflower & Late Pollinator",
            "ecoregion_benefits": "Lavender-blue star flowers provide essential nectar for migrating monarch and painted lady butterflies in September/October.",
            "sun_and_soil": "Full Sun to Part Shade; moist to average soils.",
            "water_needs": "Moderate",
            "best_garden_use": "Late-season color border, pollinator corridor, rain garden."
        }
    ],
    "ROCKIES": [
        {
            "common_name": "Rocky Mountain Columbine",
            "botanical_name": "Aquilegia caerulea",
            "plant_category": "Native Mountain Wildflower",
            "ecoregion_benefits": "Stunning blue and white spurred blossoms adapted to high-altitude mountain sun and cool nights.",
            "sun_and_soil": "Full Sun at high elevations; Part Shade in valleys; rich well-drained soil.",
            "water_needs": "Moderate",
            "best_garden_use": "Alpine rock garden, perennial border, shady mountain beds."
        },
        {
            "common_name": "Chokecherry",
            "botanical_name": "Prunus virginiana",
            "plant_category": "Native Edible Shrub / Small Tree",
            "ecoregion_benefits": "Fragrant white flower sprays followed by dark cherries perfect for homemade syrups, preserves, and wine.",
            "sun_and_soil": "Full Sun to Part Shade; well-drained mountain soil.",
            "water_needs": "Low to Moderate",
            "best_garden_use": "Edible shelterbelt, wildlife boundary, natural screen."
        },
        {
            "common_name": "Golden Currant",
            "botanical_name": "Ribes aureum",
            "plant_category": "Native Edible Berry / Shrub",
            "ecoregion_benefits": "Clove-scented yellow spring blooms followed by translucent golden-red sweet berries; extremely cold-hardy.",
            "sun_and_soil": "Full Sun to Light Shade; gravelly or sandy loam.",
            "water_needs": "Low / Drought-Tolerant",
            "best_garden_use": "Edible berry border, low water landscape, pollinator shrub."
        },
        {
            "common_name": "Blanketflower",
            "botanical_name": "Gaillardia aristata",
            "plant_category": "Native Wildflower & Pollinator",
            "ecoregion_benefits": "Tough Rocky Mountain perennial with bright red centers tipped in yellow; blooms continuously through dry summers.",
            "sun_and_soil": "Full Sun; well-drained gravelly soil.",
            "water_needs": "Low / Drought-Tolerant",
            "best_garden_use": "Xeriscape borders, cut flowers, sunny slopes."
        }
    ]
}

STATE_REGION_MAP = {
    "IL": "MIDWEST", "IN": "MIDWEST", "OH": "MIDWEST", "MI": "MIDWEST", "WI": "MIDWEST", "MN": "MIDWEST", "IA": "MIDWEST", "MO": "MIDWEST",
    "VA": "MID_ATLANTIC", "MD": "MID_ATLANTIC", "DE": "MID_ATLANTIC", "PA": "MID_ATLANTIC", "WV": "MID_ATLANTIC", "DC": "MID_ATLANTIC", "NJ": "MID_ATLANTIC",
    "NC": "SOUTHEAST", "SC": "SOUTHEAST", "GA": "SOUTHEAST", "FL": "SOUTHEAST", "AL": "SOUTHEAST", "MS": "SOUTHEAST", "TN": "SOUTHEAST", "KY": "SOUTHEAST", "LA": "SOUTHEAST", "AR": "SOUTHEAST",
    "ME": "NORTHEAST", "NH": "NORTHEAST", "VT": "NORTHEAST", "MA": "NORTHEAST", "CT": "NORTHEAST", "RI": "NORTHEAST", "NY": "NORTHEAST",
    "TX": "GREAT_PLAINS", "OK": "GREAT_PLAINS", "KS": "GREAT_PLAINS", "NE": "GREAT_PLAINS", "SD": "GREAT_PLAINS", "ND": "GREAT_PLAINS",
    "AZ": "SOUTHWEST", "NM": "SOUTHWEST", "NV": "SOUTHWEST", "UT": "SOUTHWEST",
    "CO": "ROCKIES", "WY": "ROCKIES", "MT": "ROCKIES", "ID": "ROCKIES",
    "CA": "WEST_COAST", "OR": "WEST_COAST", "WA": "WEST_COAST", "AK": "WEST_COAST", "HI": "WEST_COAST"
}

def build_full_extension_knowledgebase():
    from backend.services.build_50_state_extensions import STATE_EXTENSIONS_DATA

    for st_code, st_data in STATE_EXTENSIONS_DATA.items():
        region = STATE_REGION_MAP.get(st_code, "MIDWEST")
        st_data["ecoregion"] = region
        st_data["native_species"] = ECOREGION_NATIVE_PLANTS.get(region, ECOREGION_NATIVE_PLANTS["MIDWEST"])

    out_path = Path(__file__).resolve().parent.parent / "data" / "state_extensions.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(STATE_EXTENSIONS_DATA, f, indent=2)

    print(f"✓ Enriched 50-State Extension knowledgebase with authentic native species ({len(STATE_EXTENSIONS_DATA)} states).")

if __name__ == "__main__":
    build_full_extension_knowledgebase()
