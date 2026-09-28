from typing import Dict, Any, List

PLANT_DISEASE_CATALOG: Dict[str, Dict[str, Any]] = {
    "tomato_early_blight": {
        "plant_species": "Tomato",
        "condition_name": "Early Blight (Alternaria solani)",
        "condition_category": "Fungal",
        "symptoms": [
            "Concentric ring 'bullseye' dark brown spots on lower leaves",
            "Yellowing halos around leaf lesions",
            "Premature defoliation starting from the bottom of the plant upwards"
        ],
        "organic_remedy": {
            "organic_controls": [
                "Apply organic copper octanoate or liquid copper fungicide at first sign",
                "Spray Bacillus subtilis (Serenade) biofungicide weekly during humid weather",
                "Prune off all bottom leaves within 12 inches of the soil surface to prevent soil splash"
            ],
            "cultural_prevention": [
                "Water strictly at the soil base using drip irrigation or soaker hoses (keep foliage dry)",
                "Apply a 2-3 inch mulch layer (straw or shredded leaves) under plants",
                "Practice a 3-year crop rotation away from Solanaceae (tomatoes, peppers, potatoes, eggplants)"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Moderate"
        }
    },
    "tomato_late_blight": {
        "plant_species": "Tomato",
        "condition_name": "Late Blight (Phytophthora infestans)",
        "condition_category": "Fungal",
        "symptoms": [
            "Large water-soaked irregular dark green to purplish-black lesions",
            "White fungal fuzzy growth on leaf undersides during cool, moist mornings",
            "Rapid stem browning and firm brown rot on fruit"
        ],
        "organic_remedy": {
            "organic_controls": [
                "Immediately remove and bag heavily infected stems; do NOT compost them",
                "Apply preventive organic copper fungicide to unaffected foliage on neighboring plants",
                "Increase air circulation drastically by pruning suckers"
            ],
            "cultural_prevention": [
                "Plant certified disease-resistant cultivars (e.g. Defiant, Mountain Merit, Iron Lady)",
                "Space plants at least 24-36 inches apart for rapid foliage drying",
                "Destroy volunteer potato and tomato plants in spring"
            ],
            "safe_for_pollinators": True,
            "severity_level": "High / Urgent"
        }
    },
    "tomato_septoria_leaf_spot": {
        "plant_species": "Tomato",
        "condition_name": "Septoria Leaf Spot (Septoria lycopersici)",
        "condition_category": "Fungal",
        "symptoms": [
            "Numerous small circular spots with dark brown margins and tan/gray centers",
            "Tiny black specks (pycnidia fruiting bodies) inside the center of spots",
            "Lower foliage turns completely yellow and drops off"
        ],
        "organic_remedy": {
            "organic_controls": [
                "Spray with potassium bicarbonate or copper fungicide every 7-10 days",
                "Remove and dispose of spotted bottom leaves immediately"
            ],
            "cultural_prevention": [
                "Thick organic mulch barrier to block fungal spore splashback from soil",
                "Disinfect garden shears with 70% isopropyl alcohol between plants"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Moderate"
        }
    },
    "tomato_powdery_mildew": {
        "plant_species": "Tomato",
        "condition_name": "Powdery Mildew (Oidium neolycopersici)",
        "condition_category": "Fungal",
        "symptoms": [
            "White powdery talcum-like fungal patches on the upper surface of leaves",
            "Leaves turn yellow, curl upward, and dry out under warm dry weather"
        ],
        "organic_remedy": {
            "organic_controls": [
                "Spray with dilute potassium bicarbonate (1 tbsp/gal water + 1/2 tsp castile soap)",
                "Apply organic cold-pressed neem oil or horticultural oil in early morning",
                "Apply sulfur-based organic dust or biofungicide (Bacillus pumilus)"
            ],
            "cultural_prevention": [
                "Ensure maximum full sun exposure (at least 6-8 hours daily)",
                "Avoid excessive high-nitrogen fertilizer which creates vulnerable tender foliage"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Moderate"
        }
    },
    "tomato_bacterial_spot": {
        "plant_species": "Tomato",
        "condition_name": "Bacterial Spot (Xanthomonas spp.)",
        "condition_category": "Bacterial",
        "symptoms": [
            "Small greasy or water-soaked dark brown circular spots on leaves and fruit",
            "Leaves appear ragged as centers of lesions fall out",
            "Scabby rough lesions on green tomatoes"
        ],
        "organic_remedy": {
            "organic_controls": [
                "Preventive OMRI-listed copper hydroxide spray combined with Bacillus biofungicide",
                "Avoid handling or pruning plants when foliage is wet from dew or rain"
            ],
            "cultural_prevention": [
                "Use hot-water treated or certified disease-free seeds",
                "Drip irrigation to eliminate overhead water splashing",
                "Rotate garden beds for 2 years"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Moderate"
        }
    },
    "tomato_spider_mites": {
        "plant_species": "Tomato",
        "condition_name": "Two-Spotted Spider Mites (Tetranychus urticae)",
        "condition_category": "Pest / Insect",
        "symptoms": [
            "Fine yellow stippling or bronzing on leaf surfaces",
            "Delicate fine webbing visible on leaf undersides and stem joints",
            "Leaves become brittle, dry, and fall off in hot, dry conditions"
        ],
        "organic_remedy": {
            "organic_controls": [
                "Spray leaf undersides thoroughly with cold insecticidal soap or neem oil",
                "Introduce beneficial predatory mites (Phytoseiulus persimilis)",
                "Use a strong water jet in the morning to physically dislodge mite colonies"
            ],
            "cultural_prevention": [
                "Keep soil consistently moist and avoid drought stress",
                "Encourage predatory insects by planting dill, alyssum, and marigolds nearby"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Moderate"
        }
    },
    "tomato_healthy": {
        "plant_species": "Tomato",
        "condition_name": "Healthy Foliage",
        "condition_category": "Healthy",
        "symptoms": [
            "Vibrant deep green foliage with uniform texture",
            "No visible lesions, curling, webbing, or chlorosis",
            "Vigorous stem growth and sturdy branching"
        ],
        "organic_remedy": {
            "organic_controls": [
                "No treatments necessary! Plant is in optimal health."
            ],
            "cultural_prevention": [
                "Continue balanced watering (1-1.5 inches per week)",
                "Side-dress with compost or worm castings when first fruit clusters set",
                "Maintain mulch layer and support vines with stakes or cages"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Low"
        }
    },
    "pepper_bacterial_spot": {
        "plant_species": "Pepper",
        "condition_name": "Bacterial Leaf Spot (Xanthomonas campestris)",
        "condition_category": "Bacterial",
        "symptoms": [
            "Small yellowish-green spots that darken to brown with water-soaked margins",
            "Leaves turn yellow and drop prematurely, exposing fruit to sunscald",
            "Warty raised brown spots on pepper fruit"
        ],
        "organic_remedy": {
            "organic_controls": [
                "Spray OMRI-listed organic fixed copper fungicide at first sign",
                "Remove fallen infected leaves from around the plant base"
            ],
            "cultural_prevention": [
                "Plant resistant bell and hot pepper varieties (e.g. Aristotle, Vanguard)",
                "Water with drip irrigation only",
                "Rotate away from nightshades for 2 full years"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Moderate"
        }
    },
    "pepper_healthy": {
        "plant_species": "Pepper",
        "condition_name": "Healthy Foliage",
        "condition_category": "Healthy",
        "symptoms": [
            "Glossy dark green leaves with uniform surface",
            "No spotting, mosaic patterns, or chewing damage",
            "Strong central leader with flower buds developing"
        ],
        "organic_remedy": {
            "organic_controls": [
                "No treatment required. Plants are vigorous."
            ],
            "cultural_prevention": [
                "Maintain soil pH between 6.2 and 6.8 with good calcium availability",
                "Avoid over-fertilizing with high-nitrogen food to encourage fruit set"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Low"
        }
    },
    "squash_powdery_mildew": {
        "plant_species": "Squash & Zucchini",
        "condition_name": "Powdery Mildew (Podosphaera xanthii)",
        "condition_category": "Fungal",
        "symptoms": [
            "White flour-like powdery patches spreading across both leaf surfaces",
            "Leaves yellow, turn brittle, and die back prematurely",
            "Reduced fruit yield and sunburned squash"
        ],
        "organic_remedy": {
            "organic_controls": [
                "Spray with dilute potassium bicarbonate or milk spray (40% milk, 60% water in direct sun)",
                "Apply organic neem oil or horticultural oil weekly",
                "Prune the most severely infected older leaves"
            ],
            "cultural_prevention": [
                "Plant resistant squash varieties (e.g. Dunja zucchini, Honeyboat delicata)",
                "Provide 3-4 feet of spacing between squash mounds for air movement",
                "Water at the base early in the morning"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Moderate"
        }
    },
    "apple_scab": {
        "plant_species": "Apple",
        "condition_name": "Apple Scab (Venturia inaequalis)",
        "condition_category": "Fungal",
        "symptoms": [
            "Olive-green to velvety dark brown lesions on leaves and fruit",
            "Distorted, cracked, or corky lesions on developing apples",
            "Early summer leaf drop"
        ],
        "organic_remedy": {
            "organic_controls": [
                "Apply liquid lime sulfur or organic copper during early spring green tip bud stage",
                "Rake and destroy fallen leaves in autumn to eliminate overwintering spores"
            ],
            "cultural_prevention": [
                "Prune tree canopy annually in late winter for maximum sun penetration and air circulation",
                "Plant scab-resistant cultivars like Liberty, Enterprise, Freedom, or Pristine"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Moderate"
        }
    },
    "apple_cedar_rust": {
        "plant_species": "Apple",
        "condition_name": "Cedar-Apple Rust (Gymnosporangium juniperi-virginianae)",
        "condition_category": "Fungal",
        "symptoms": [
            "Bright yellow-orange spots on upper leaf surfaces in late spring",
            "Spots develop tiny black dots and tubular spore cups on leaf undersides",
            "Early defoliation and fruit blemish"
        ],
        "organic_remedy": {
            "organic_controls": [
                "Apply sulfur or organic biofungicide (Bacillus amyloliquefaciens) during bud break to petal fall",
                "Remove nearby Eastern Red Cedar galls if present within 500 feet"
            ],
            "cultural_prevention": [
                "Choose rust-immune apple varieties (e.g. Liberty, Enterprise, Redfree)",
                "Maintain open tree canopy"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Moderate"
        }
    },
    "apple_healthy": {
        "plant_species": "Apple",
        "condition_name": "Healthy Foliage",
        "condition_category": "Healthy",
        "symptoms": [
            "Lush green leaves without lesions or rust spots",
            "Clean fruit development with smooth skin"
        ],
        "organic_remedy": {
            "organic_controls": ["No treatment needed."],
            "cultural_prevention": ["Maintain dormant season pruning and organic compost mulch ring."],
            "safe_for_pollinators": True,
            "severity_level": "Low"
        }
    },
    "grape_black_rot": {
        "plant_species": "Grape",
        "condition_name": "Black Rot (Guignardia bidwellii)",
        "condition_category": "Fungal",
        "symptoms": [
            "Reddish-brown circular leaf spots with tiny black fruiting pimples",
            "Berries turn brown, shrivel rapidly into hard black mummies",
            "Entire grape clusters destroyed before ripening"
        ],
        "organic_remedy": {
            "organic_controls": [
                "Apply organic copper fungicide or wettable sulfur starting at 1-inch new shoot growth through 4 weeks post-bloom",
                "Remove and burn all shriveled berry mummies from vines and ground"
            ],
            "cultural_prevention": [
                "Trellis vines high for maximum wind and air passage",
                "Keep base of grape arbor free of tall grass and weeds"
            ],
            "safe_for_pollinators": True,
            "severity_level": "High / Urgent"
        }
    },
    "grape_healthy": {
        "plant_species": "Grape",
        "condition_name": "Healthy Foliage",
        "condition_category": "Healthy",
        "symptoms": [
            "Broad, rich green leaves with active tendril growth",
            "Clean cluster formation without shriveling or spotting"
        ],
        "organic_remedy": {
            "organic_controls": ["No treatment needed."],
            "cultural_prevention": ["Annual dormant pruning and canopy management."],
            "safe_for_pollinators": True,
            "severity_level": "Low"
        }
    },
    "strawberry_leaf_scorch": {
        "plant_species": "Strawberry",
        "condition_name": "Leaf Scorch (Diplocarpon earlianum)",
        "condition_category": "Fungal",
        "symptoms": [
            "Irregular purplish-red blotches without light centers",
            "Leaves turn brown and look scorched or burned around edges",
            "Vigor and runner production decline"
        ],
        "organic_remedy": {
            "organic_controls": [
                "Spray copper octanoate or sulfur after post-harvest renovation",
                "Mow or clip old foliage after June harvest"
            ],
            "cultural_prevention": [
                "Renew strawberry beds every 3-4 years",
                "Plant in well-draining soil with clean straw mulch between rows",
                "Drip irrigation to avoid wetting strawberry crowns"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Moderate"
        }
    },
    "strawberry_healthy": {
        "plant_species": "Strawberry",
        "condition_name": "Healthy Foliage",
        "condition_category": "Healthy",
        "symptoms": [
            "Trifoliate leaves with bright serrated green margins",
            "Strong crown development and white blossom clusters"
        ],
        "organic_remedy": {
            "organic_controls": ["No treatment needed."],
            "cultural_prevention": ["Keep straw mulch under fruit to prevent ground contact."],
            "safe_for_pollinators": True,
            "severity_level": "Low"
        }
    },
    "potato_early_blight": {
        "plant_species": "Potato",
        "condition_name": "Early Blight (Alternaria solani)",
        "condition_category": "Fungal",
        "symptoms": [
            "Brown angular spots with concentric target rings on older foliage",
            "Lower leaves yellow and wither",
            "Tuber yield reduced"
        ],
        "organic_remedy": {
            "organic_controls": [
                "Apply organic copper fungicide or Bacillus subtilis",
                "Hill soil or add straw mulch to protect tubers from spore washdown"
            ],
            "cultural_prevention": [
                "Maintain uniform soil moisture; avoid drought stress",
                "3-year rotation away from nightshades"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Moderate"
        }
    },
    "potato_healthy": {
        "plant_species": "Potato",
        "condition_name": "Healthy Foliage",
        "condition_category": "Healthy",
        "symptoms": [
            "Dense, lush dark green foliage with upright stems",
            "No foliar spotting or curling"
        ],
        "organic_remedy": {
            "organic_controls": ["No treatment needed."],
            "cultural_prevention": ["Continue hilling soil around stems to keep tubers buried."],
            "safe_for_pollinators": True,
            "severity_level": "Low"
        }
    },
    # --- PlantDoc-expanded classes (https://github.com/pratikkayal/PlantDoc-Dataset) ---
    "potato_late_blight": {
        "plant_species": "Potato",
        "condition_name": "Late Blight (Phytophthora infestans)",
        "condition_category": "Fungal",
        "symptoms": [
            "Large dark water-soaked lesions that spread rapidly on leaves",
            "White fungal growth on leaf undersides in cool, wet weather",
            "Stem lesions and firm brown tuber rot"
        ],
        "organic_remedy": {
            "organic_controls": [
                "Remove and bag heavily infected foliage immediately; do not compost",
                "Apply preventive organic copper fungicide to neighboring plants",
                "Hill soil deeply to protect developing tubers"
            ],
            "cultural_prevention": [
                "Plant certified disease-free seed potatoes",
                "Destroy volunteer potatoes and cull piles in spring",
                "Improve airflow and avoid overhead irrigation"
            ],
            "safe_for_pollinators": True,
            "severity_level": "High / Urgent"
        }
    },
    "tomato_leaf_mold": {
        "plant_species": "Tomato",
        "condition_name": "Leaf Mold (Passalora fulva)",
        "condition_category": "Fungal",
        "symptoms": [
            "Pale green to yellow patches on upper leaf surfaces",
            "Olive-green to grayish-purple fuzzy mold on leaf undersides",
            "Common in humid greenhouses and dense canopies"
        ],
        "organic_remedy": {
            "organic_controls": [
                "Increase ventilation and prune lower leaves for airflow",
                "Apply potassium bicarbonate or organic copper at first sign",
                "Remove heavily infected leaves and dispose off-site"
            ],
            "cultural_prevention": [
                "Keep relative humidity below 85% in enclosed growing spaces",
                "Avoid wetting foliage; water at the soil line",
                "Choose leaf-mold-resistant tomato varieties when available"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Moderate"
        }
    },
    "tomato_mosaic_virus": {
        "plant_species": "Tomato",
        "condition_name": "Tomato Mosaic Virus (ToMV)",
        "condition_category": "Viral",
        "symptoms": [
            "Mottled light and dark green mosaic patterns on leaves",
            "Leaf distortion, fern-leaf narrowing, or blistering",
            "Stunted growth and uneven fruit ripening"
        ],
        "organic_remedy": {
            "organic_controls": [
                "Remove and destroy infected plants — there is no cure once infected",
                "Disinfect tools and hands with 10% bleach or 70% alcohol between plants",
                "Control aphids and other sap-sucking insects that can spread viruses"
            ],
            "cultural_prevention": [
                "Start with certified virus-free seed and transplants",
                "Avoid tobacco products near plants (ToMV can transfer from hands)",
                "Rotate beds and control weedy nightshade hosts"
            ],
            "safe_for_pollinators": True,
            "severity_level": "High / Urgent"
        }
    },
    "tomato_yellow_leaf_curl": {
        "plant_species": "Tomato",
        "condition_name": "Tomato Yellow Leaf Curl Virus (TYLCV)",
        "condition_category": "Viral",
        "symptoms": [
            "Upward leaf curling with yellowing leaf margins",
            "Stunted plants with shortened internodes",
            "Reduced flowering and fruit set"
        ],
        "organic_remedy": {
            "organic_controls": [
                "Roguing: remove infected plants promptly to limit spread",
                "Use reflective mulches and fine insect netting to reduce whiteflies",
                "Apply insecticidal soap to undersides of leaves for whitefly nymphs"
            ],
            "cultural_prevention": [
                "Plant TYLCV-resistant cultivars where available",
                "Manage whitefly populations early in the season",
                "Avoid overlapping tomato plantings that carry whiteflies year-round"
            ],
            "safe_for_pollinators": True,
            "severity_level": "High / Urgent"
        }
    },
    "corn_gray_leaf_spot": {
        "plant_species": "Corn",
        "condition_name": "Gray Leaf Spot (Cercospora zeae-maydis)",
        "condition_category": "Fungal",
        "symptoms": [
            "Rectangular gray to tan lesions running parallel to leaf veins",
            "Lesions expand and coalesce, killing large leaf areas",
            "Yield loss when upper canopy is infected before grain fill"
        ],
        "organic_remedy": {
            "organic_controls": [
                "Remove and destroy severely infected residue after harvest",
                "Apply approved organic biofungicides at early lesion stage if feasible"
            ],
            "cultural_prevention": [
                "Rotate away from continuous corn for at least one year",
                "Choose hybrids with gray leaf spot resistance",
                "Reduce dense canopy humidity with wider spacing where possible"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Moderate"
        }
    },
    "corn_leaf_blight": {
        "plant_species": "Corn",
        "condition_name": "Northern / Southern Leaf Blight",
        "condition_category": "Fungal",
        "symptoms": [
            "Elongated cigar-shaped gray-green to tan lesions on leaves",
            "Lesions expand under warm, humid weather",
            "Premature leaf death reduces ear fill"
        ],
        "organic_remedy": {
            "organic_controls": [
                "Remove heavily blighted leaves on small garden plantings",
                "Apply copper or Bacillus-based biofungicide preventively in wet spells"
            ],
            "cultural_prevention": [
                "Plant blight-resistant sweet corn varieties",
                "Rotate crops and till under infected residue",
                "Avoid overhead watering in the evening"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Moderate"
        }
    },
    "corn_common_rust": {
        "plant_species": "Corn",
        "condition_name": "Common Rust (Puccinia sorghi)",
        "condition_category": "Fungal",
        "symptoms": [
            "Small cinnamon-brown pustules on both leaf surfaces",
            "Pustules rupture and release powdery rust spores",
            "Heavy infection causes leaf yellowing and drying"
        ],
        "organic_remedy": {
            "organic_controls": [
                "Remove earliest infected leaves on backyard plantings",
                "Apply sulfur or copper fungicide if pustules are spreading rapidly"
            ],
            "cultural_prevention": [
                "Choose rust-resistant sweet corn hybrids",
                "Provide good airflow between rows",
                "Avoid late plantings that mature during peak rust season"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Moderate"
        }
    },
    "blueberry_healthy": {
        "plant_species": "Blueberry",
        "condition_name": "Healthy Foliage",
        "condition_category": "Healthy",
        "symptoms": [
            "Glossy green leaves without spotting or tip burn",
            "Even canopy color and active new growth"
        ],
        "organic_remedy": {
            "organic_controls": ["No treatment needed."],
            "cultural_prevention": [
                "Maintain acidic soil (pH 4.5–5.5) with pine bark mulch",
                "Provide consistent moisture without waterlogging roots"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Low"
        }
    },
    "cherry_healthy": {
        "plant_species": "Cherry",
        "condition_name": "Healthy Foliage",
        "condition_category": "Healthy",
        "symptoms": [
            "Deep green leaves with clean margins",
            "No shot-hole lesions or powdery residue"
        ],
        "organic_remedy": {
            "organic_controls": ["No treatment needed."],
            "cultural_prevention": [
                "Prune for open canopy airflow in late winter",
                "Rake fallen leaves to reduce overwintering disease pressure"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Low"
        }
    },
    "peach_healthy": {
        "plant_species": "Peach",
        "condition_name": "Healthy Foliage",
        "condition_category": "Healthy",
        "symptoms": [
            "Lance-shaped green leaves without curling or yellow mottling",
            "Clean shoot tips and developing fruit"
        ],
        "organic_remedy": {
            "organic_controls": ["No treatment needed."],
            "cultural_prevention": [
                "Maintain dormant-season sanitation and open pruning",
                "Avoid wetting foliage overnight"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Low"
        }
    },
    "raspberry_healthy": {
        "plant_species": "Raspberry",
        "condition_name": "Healthy Foliage",
        "condition_category": "Healthy",
        "symptoms": [
            "Compound green leaflets without purple blotching",
            "Upright canes with active lateral growth"
        ],
        "organic_remedy": {
            "organic_controls": ["No treatment needed."],
            "cultural_prevention": [
                "Thin canes annually for airflow",
                "Mulch and drip-irrigate to keep foliage dry"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Low"
        }
    },
    "soybean_healthy": {
        "plant_species": "Soybean",
        "condition_name": "Healthy Foliage",
        "condition_category": "Healthy",
        "symptoms": [
            "Trifoliate leaves with uniform green color",
            "No chlorotic mottling or necrotic lesions"
        ],
        "organic_remedy": {
            "organic_controls": ["No treatment needed."],
            "cultural_prevention": [
                "Rotate legumes and avoid continuous soybean plantings",
                "Scout regularly after humid weather"
            ],
            "safe_for_pollinators": True,
            "severity_level": "Low"
        }
    }
}

CLASS_NAMES = list(PLANT_DISEASE_CATALOG.keys())
NUM_CLASSES = len(CLASS_NAMES)
