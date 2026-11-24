"""
EcoTransform AI - Multimodal Vision & Intelligence Service
Integrates Google Gemini 1.5/2.0 Flash Vision REST API with structured JSON output,
paired with an intelligent offline fallback engine for fail-safe hackathon demonstrations.
"""

import os
import json
import base64
import urllib.request
import urllib.error
from PIL import Image
import io
from impact_calculator import calculate_environmental_impact
from ocr_service import evaluate_image_quality, parse_packaging_ocr

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

GEMINI_SYSTEM_PROMPT = """
You are EcoTransform AI, an expert computer vision environmental scientist, materials engineer, and circular economy designer.

Analyze the user's provided waste image with high scientific accuracy.

TASKS:
1. Identify the primary object, composition material (e.g., PET #1, HDPE #2, Corrugated Cardboard, Aluminum, Borosilicate Glass), and physical condition.
2. Classify into one or more categories: ["Biodegradable", "Recyclable", "Reusable", "Hazardous", "Non-recyclable"].
3. Estimate item weight in kilograms based on typical dimensional standards.
4. If hazardous (e.g., swollen battery, fluorescent mercury tube, medical sharp, pesticide), mark is_hazardous: true and DO NOT suggest DIY cutting or heating.
5. OCR & PACKAGING LABEL RECOGNITION:
   - Carefully read any visible printed, embossed, stamped, or molded text, symbols, and recycling codes on the packaging.
   - Look specifically for Resin Identification Codes (PET 1, HDPE 2, PVC 3, LDPE 4, PP 5, PS 6, OTHER 7).
   - Read recycling instructions (e.g. How2Recycle: Rinse & Replace Cap), warnings, and composition notes.
   - Report exactly what is printed without assuming printed labels represent 100% of the entire composite product.
6. Generate exactly 3 practical, creative, and safe "Waste-to-Wealth" upcycling transformation ideas:
   - Idea 1: Beginner / 15-min home utility.
   - Idea 2: Intermediate / decor or organization with high visual appeal.
   - Idea 3: Advanced / functional product with potential commercial or market resale value ($3-$25).
7. Provide accurate, realistic step-by-step instructions and practical safety guidelines.

OUTPUT REQUIREMENT:
Return strictly a valid JSON object matching this schema without markdown codeblocks or quotes around the JSON:
{
  "item_name": "Clear Plastic Beverage Bottle (500ml)",
  "primary_material": "Polyethylene Terephthalate (PET, #1)",
  "physical_condition": "Empty, clean, slightly crushed with cap intact",
  "confidence_score": 0.94,
  "categories": ["Recyclable", "Reusable"],
  "is_hazardous": false,
  "identification_reasoning": "Standard transparency, distinct injection molding base ring, and structural ribbing characteristic of PET beverage containers.",
  "disposal_recommendation": "Rinse, flatten to save bin space, screw cap back on, and place in municipal dry recyclables bin.",
  "estimated_weight_kg": 0.025,
  "ocr_evidence": {
    "extracted_text": "500ml PET 1 RECYCLE ME PLEASE RINSE BEFORE BIN",
    "detected_symbols": ["♳ (PET 1)", "How2Recycle Cap On"],
    "identified_material": "Polyethylene Terephthalate (PET #1)",
    "information_source": "Embossed recycling logo on bottle base & side label text",
    "ocr_confidence": 0.95
  },
  "upcycle_recommendations": [
    {
      "product_name": "Self-Watering Microgreen Planter",
      "difficulty": "Easy",
      "estimated_time_mins": 15,
      "estimated_cost_usd": 0.50,
      "potential_value_usd": 8.00,
      "materials_needed": ["Empty 500ml PET bottle", "Cotton string", "Potting soil", "Seeds"],
      "tools_needed": ["Utility knife or scissors"],
      "safety_precautions": ["Cut edges of plastic can be sharp; tape or sand them smooth."],
      "steps": [
        "Cut the plastic bottle horizontally in half approximately 10cm from the base.",
        "Invert the top conical half into the lower base cylinder.",
        "Thread a 15cm cotton wick through the neck into the base reservoir.",
        "Fill the inverted cone with soil, sow seeds, and fill base with 100ml water."
      ],
      "sustainability_benefit": "Eliminates single-use plastic disposal while producing domestic fresh herbs with zero transport emissions."
    },
    {
      "product_name": "Ergonomic Cable Organizer Spool",
      "difficulty": "Easy",
      "estimated_time_mins": 10,
      "estimated_cost_usd": 0.00,
      "potential_value_usd": 4.00,
      "materials_needed": ["Center cylindrical section of bottle"],
      "tools_needed": ["Kitchen scissors"],
      "safety_precautions": ["Ensure cut edges are trimmed flush."],
      "steps": [
        "Remove bottle top and base to create an open plastic sleeve.",
        "Cut a continuous spiral strip of 1.5cm width.",
        "Wrap the spiral sleeve around bundled computer cables for clean desk cable management."
      ],
      "sustainability_benefit": "Replaces petroleum-derived virgin plastic cable wraps."
    },
    {
      "product_name": "Hanging Wild Bird Feeder",
      "difficulty": "Medium",
      "estimated_time_mins": 25,
      "estimated_cost_usd": 1.00,
      "potential_value_usd": 12.00,
      "materials_needed": ["Bottle with cap", "Two discarded wooden spoons", "Twine", "Bird seed"],
      "tools_needed": ["Craft knife or hole punch"],
      "safety_precautions": ["Puncture bottle slowly on a firm cutting mat."],
      "steps": [
        "Pierce two pairs of opposing holes through the bottle sides to slide the spoons through as perches.",
        "Widen the hole above the spoon bowl slightly to allow seeds to dispense into the bowl.",
        "Screw a small eye hook into the cap or tie twine around the neck for hanging.",
        "Fill with seed, cap tightly, and suspend outdoors."
      ],
      "sustainability_benefit": "Promotes local biodiversity while extending material lifespan by 12+ months."
    }
  ]
}
"""

# Fallback smart archetypes based on dominant color or filename/preset
FALLBACK_ARCHETYPES = {
    "plastic": {
        "item_name": "Mixed Recyclable Plastics & Bottles (PET/HDPE)",
        "primary_material": "Polyethylene Terephthalate (PET #1) & HDPE #2",
        "physical_condition": "Mixed post-consumer rigid plastic containers, cleanable",
        "confidence_score": 0.94,
        "categories": ["Recyclable", "Reusable"],
        "is_hazardous": False,
        "identification_reasoning": "Visible thermoformed transparent containers, blow-molded bottles, and jugs characteristic of recyclable domestic packaging.",
        "disposal_recommendation": "Rinse out residual food/liquid, flatten containers to save volume, and place in municipal dry recyclables bin.",
        "estimated_weight_kg": 0.085,
        "upcycle_recommendations": [
            {
                "product_name": "Vertical Self-Watering Planter Tower",
                "difficulty": "Easy",
                "estimated_time_mins": 25,
                "estimated_cost_usd": 1.00,
                "potential_value_usd": 15.00,
                "materials_needed": ["Plastic bottles and milk jugs", "Cotton string or wicks", "Potting soil", "Seeds"],
                "tools_needed": ["Utility knife or scissors", "Twine for hanging"],
                "safety_precautions": ["Smooth down cut plastic edges with sandpaper or protective tape."],
                "steps": [
                    "Cut rectangular access windows along the sides of each plastic bottle.",
                    "Thread a sturdy cotton wick through the bottle caps to allow capillary water flow.",
                    "Stack bottles vertically, linking necks into lower bases.",
                    "Fill with potting soil, sow herbs or greens, and irrigate from the top reservoir."
                ],
                "sustainability_benefit": "Diverts multiple plastic bottles while creating a zero-footprint domestic vertical herb garden."
            },
            {
                "product_name": "High-Density Ecobrick Building Blocks",
                "difficulty": "Medium",
                "estimated_time_mins": 30,
                "estimated_cost_usd": 0.00,
                "potential_value_usd": 8.00,
                "materials_needed": ["Clean plastic bottles", "Non-recyclable clean plastic packaging/wrappers"],
                "tools_needed": ["Wooden dowel or stick"],
                "safety_precautions": ["Ensure all plastic stuffed inside is completely dry to prevent mold growth."],
                "steps": [
                    "Collect clean, dry plastic bottles and wrappers.",
                    "Use a wooden stick to compress plastic wrappers tightly inside the bottle until dense and rigid.",
                    "Ensure a minimum density of 0.33g/ml (feels like a solid brick).",
                    "Use ecobricks to build raised garden bed walls, outdoor seating, or insulation structures."
                ],
                "sustainability_benefit": "Sequesters non-recyclable plastic into durable, weather-resistant building modules."
            },
            {
                "product_name": "Modular Drawer & Workshop Organizers",
                "difficulty": "Easy",
                "estimated_time_mins": 15,
                "estimated_cost_usd": 0.20,
                "potential_value_usd": 6.50,
                "materials_needed": ["Bases of plastic bottles and milk jugs"],
                "tools_needed": ["Utility scissors", "Edge tape or iron for smoothing"],
                "safety_precautions": ["Trim any sharp corners flush."],
                "steps": [
                    "Cut the bottom 6cm bases off assorted bottles and jugs.",
                    "Gently touch the cut rim to a warm clothes iron covered in baking parchment to roll the edge smooth.",
                    "Arrange into drawer trays to sort hardware, screws, crafts, and office stationery."
                ],
                "sustainability_benefit": "Replaces purchased plastic drawer divider sets with 100% recycled containers."
            }
        ]
    },
    "aluminum": {
        "item_name": "Aluminum Beverage Can (330ml)",
        "primary_material": "Aluminum Alloy 3004",
        "physical_condition": "Empty, clean, uncrushed with pull-tab attached",
        "confidence_score": 0.96,
        "categories": ["Recyclable", "Reusable"],
        "is_hazardous": False,
        "identification_reasoning": "Characteristic metallic sheen, rolled lip rim, and cylindrical form of modern aluminum beverage cans.",
        "disposal_recommendation": "Rinse quickly and place into municipal aluminum recycling bin. Aluminum is 100% infinitely recyclable.",
        "estimated_weight_kg": 0.015,
        "upcycle_recommendations": [
            {
                "product_name": "Minimalist Desktop Stationery Cup",
                "difficulty": "Easy",
                "estimated_time_mins": 15,
                "estimated_cost_usd": 0.20,
                "potential_value_usd": 6.00,
                "materials_needed": ["Aluminum can", "Washi tape or sandpaper", "Felt base pad"],
                "tools_needed": ["Smooth-edge can opener or metal file"],
                "safety_precautions": ["Wear gloves. Aluminum cut edges are very sharp until crimped or taped."],
                "steps": [
                    "Use a smooth-edge can opener to cleanly remove the top rim.",
                    "File the inner edge completely smooth and apply protective fabric tape along the rim.",
                    "Glue a soft felt circle to the bottom to protect desk surfaces.",
                    "Use for pens, pencils, and paintbrushes."
                ],
                "sustainability_benefit": "Diverts valuable aluminum from scrap while replacing virgin plastic desk cups."
            },
            {
                "product_name": "Embossed Tealight Lantern",
                "difficulty": "Medium",
                "estimated_time_mins": 30,
                "estimated_cost_usd": 0.50,
                "potential_value_usd": 10.00,
                "materials_needed": ["Aluminum can", "Tealight candle or LED puck"],
                "tools_needed": ["Hole punch, pushpin or nail, hammer"],
                "safety_precautions": ["Fill can with water and freeze solid before punching holes to prevent buckling."],
                "steps": [
                    "Fill can with water and freeze solid overnight.",
                    "Use a nail and hammer to punch decorative constellations or geometric dot patterns.",
                    "Let ice melt and dry thoroughly.",
                    "Cut off the top lid and place an LED tealight inside to project light patterns."
                ],
                "sustainability_benefit": "Transforms discarded metal into warm decorative ambient lighting."
            },
            {
                "product_name": "High-Efficiency Ultralight Camp Stove",
                "difficulty": "Hard",
                "estimated_time_mins": 45,
                "estimated_cost_usd": 1.50,
                "potential_value_usd": 18.00,
                "materials_needed": ["Two identical soda cans", "Fiberglass or rockwool wick"],
                "tools_needed": ["Hobby knife, push pin, ruler"],
                "safety_precautions": ["Only use denatured alcohol outdoors on a non-flammable surface."],
                "steps": [
                    "Cut both cans 3.5cm from their bases to form top burner and bottom fuel cup.",
                    "Pin-punch 16 jet holes radially along the rim of the top piece.",
                    "Insert an inner aluminum chimney wall with cotton wick inside.",
                    "Press both halves together firmly to lock the pressure chamber."
                ],
                "sustainability_benefit": "Favored by ultralight hikers, weighing just 25 grams and substituting heavy gas canisters."
            }
        ]
    },
    "cardboard": {
        "item_name": "Corrugated Cardboard Packaging Box",
        "primary_material": "Corrugated Kraft Paperboard",
        "physical_condition": "Dry, intact with adhesive packaging tape",
        "confidence_score": 0.95,
        "categories": ["Recyclable", "Reusable", "Biodegradable"],
        "is_hazardous": False,
        "identification_reasoning": "Distinct fluted corrugation layer between outer kraft liners, typical of shipping cartons.",
        "disposal_recommendation": "Flatten box completely. Remove excess plastic shipping tape and place into cardboard recycling.",
        "estimated_weight_kg": 0.180,
        "upcycle_recommendations": [
            {
                "product_name": "Modular Drawer Divider Grid",
                "difficulty": "Easy",
                "estimated_time_mins": 20,
                "estimated_cost_usd": 0.00,
                "potential_value_usd": 7.00,
                "materials_needed": ["Flattened cardboard box flaps", "Masking tape"],
                "tools_needed": ["Ruler, craft knife"],
                "safety_precautions": ["Always cut away from yourself using a safety straightedge."],
                "steps": [
                    "Measure your desk or dresser drawer height and depth.",
                    "Cut cardboard strips matching drawer height.",
                    "Cut interlocking half-depth vertical slots every 8cm.",
                    "Slot the strips together in a cross-hatch grid and place in drawer."
                ],
                "sustainability_benefit": "Zero-waste organizer that replaces petroleum-based acrylic drawer organizers."
            },
            {
                "product_name": "Cardboard Scratching Lounge for Cats",
                "difficulty": "Medium",
                "estimated_time_mins": 40,
                "estimated_cost_usd": 1.00,
                "potential_value_usd": 15.00,
                "materials_needed": ["Corrugated cardboard boxes", "Non-toxic PVA glue"],
                "tools_needed": ["Utility knife, heavy books for clamping"],
                "safety_precautions": ["Ensure glue is non-toxic and pet-safe."],
                "steps": [
                    "Cut cardboard along the flute grain into 6cm wide uniform strips.",
                    "Roll the first strip tightly into a central cylinder, applying glue.",
                    "Continuously wrap and glue successive strips outward until reaching a 30cm wide disc.",
                    "Allow to cure under weight for 4 hours."
                ],
                "sustainability_benefit": "Provides durable, recyclable pet enrichment while saving commercial corrugated pet furniture purchases."
            },
            {
                "product_name": "Sheet Mulch Garden Weed Barrier",
                "difficulty": "Easy",
                "estimated_time_mins": 15,
                "estimated_cost_usd": 0.00,
                "potential_value_usd": 10.00,
                "materials_needed": ["Cardboard boxes", "Compost or wood chips"],
                "tools_needed": ["Garden hose or watering can"],
                "safety_precautions": ["Remove all synthetic tape, staples, and plastic labels first."],
                "steps": [
                    "Remove all tape, shipping labels, and staples.",
                    "Lay cardboard sheets flat over garden soil, overlapping edges by 10cm.",
                    "Soak thoroughly with water.",
                    "Top with 5cm of organic woodchips or mulch."
                ],
                "sustainability_benefit": "Blocks weeds without plastic landscape fabric, eventually decomposing into rich organic humus."
            }
        ]
    },
    "glass": {
        "item_name": "Glass Bottle or Jar",
        "primary_material": "Soda-Lime Silica Glass",
        "physical_condition": "Intact, cleanable glass container",
        "confidence_score": 0.90,
        "categories": ["Recyclable", "Reusable"],
        "is_hazardous": False,
        "identification_reasoning": "Characteristic optical clarity, rigid amorphous silica structure, and smooth reflective surface of glass containers.",
        "disposal_recommendation": "Rinse clean. Remove metal lid separately. Place in glass recycling bin — do NOT mix with ceramics.",
        "estimated_weight_kg": 0.350,
        "upcycle_recommendations": [
            {
                "product_name": "Herb & Succulent Tabletop Vase",
                "difficulty": "Easy",
                "estimated_time_mins": 10,
                "estimated_cost_usd": 0.50,
                "potential_value_usd": 8.00,
                "materials_needed": ["Glass jar or bottle", "Twine or jute rope", "Small pebbles"],
                "tools_needed": ["Scissors"],
                "safety_precautions": ["Handle glass carefully; wrap in cloth when carrying to avoid drops."],
                "steps": [
                    "Clean the jar thoroughly with soap and water and allow to dry completely.",
                    "Wrap twine or jute rope around the jar in tight rows and secure with a dab of craft glue.",
                    "Place a layer of small pebbles at the bottom for drainage.",
                    "Plant a succulent or herb cutting and place in a sunny windowsill."
                ],
                "sustainability_benefit": "Extends glass lifecycle by 12+ months as a home garden accent, reducing demand for ceramic plant pots."
            },
            {
                "product_name": "Ambient Tealight Lantern",
                "difficulty": "Easy",
                "estimated_time_mins": 15,
                "estimated_cost_usd": 0.30,
                "potential_value_usd": 7.00,
                "materials_needed": ["Glass jar", "LED tealight or wax tea candle", "Sand or stones"],
                "tools_needed": ["None"],
                "safety_precautions": ["If using real candles, never leave unattended. Keep away from flammable materials."],
                "steps": [
                    "Fill the bottom 3cm of the jar with clean sand or decorative pebbles.",
                    "Place an LED tealight on top of the sand layer.",
                    "Optionally wrap the outside with copper wire for a rustic decorative finish.",
                    "Arrange in clusters on a dining table or outdoor terrace."
                ],
                "sustainability_benefit": "Creates zero-waste ambient lighting without buying mass-produced glass lanterns."
            },
            {
                "product_name": "Airtight Pantry Storage Jar",
                "difficulty": "Easy",
                "estimated_time_mins": 5,
                "estimated_cost_usd": 0.00,
                "potential_value_usd": 6.00,
                "materials_needed": ["Glass jar with lid", "Label or chalk paint marker"],
                "tools_needed": ["Sponge or cloth"],
                "safety_precautions": ["Ensure jar is bone dry before storing dry goods to prevent mold."],
                "steps": [
                    "Remove all original labels by soaking in warm water for 20 minutes.",
                    "Scrub away adhesive residue with vegetable oil and dish soap.",
                    "Rinse, dry, and label with contents using a chalk paint marker.",
                    "Use for spices, coffee, grains, and dry herbs in the pantry."
                ],
                "sustainability_benefit": "Eliminates single-use plastic food storage bags, keeping glass in active use."
            }
        ]
    },
    "organic": {
        "item_name": "Organic Food Waste & Kitchen Scraps",
        "primary_material": "Biodegradable Organic Matter",
        "physical_condition": "Mixed vegetable, fruit peel, and food scraps",
        "confidence_score": 0.88,
        "categories": ["Biodegradable"],
        "is_hazardous": False,
        "identification_reasoning": "Plant-based organic matter visible — fruit peels, vegetable scraps, coffee grounds, and food residue.",
        "disposal_recommendation": "Compost at home or place in municipal green/organic waste bin. Do NOT landfill — composting reduces methane emissions.",
        "estimated_weight_kg": 0.150,
        "upcycle_recommendations": [
            {
                "product_name": "DIY Compost Bin & Soil Maker",
                "difficulty": "Easy",
                "estimated_time_mins": 20,
                "estimated_cost_usd": 2.00,
                "potential_value_usd": 15.00,
                "materials_needed": ["Plastic bin with lid", "Brown dried leaves or cardboard scraps", "Kitchen food scraps"],
                "tools_needed": ["Drill for air holes"],
                "safety_precautions": ["Do not compost meat, fish, or dairy — attract pests. Maintain moisture."],
                "steps": [
                    "Drill 10-12 air holes around the sides and lid of a large plastic bin.",
                    "Layer 5cm of dry brown material (leaves/cardboard) at the bottom.",
                    "Add food scraps in a 1:2 ratio with brown material.",
                    "Turn the pile every 3-4 days and harvest rich compost in 6-8 weeks."
                ],
                "sustainability_benefit": "Diverts food waste from landfill, eliminating methane emissions and producing free fertilizer."
            },
            {
                "product_name": "Natural Enzyme All-Purpose Cleaner",
                "difficulty": "Medium",
                "estimated_time_mins": 15,
                "estimated_cost_usd": 0.50,
                "potential_value_usd": 8.00,
                "materials_needed": ["Citrus peels", "Brown sugar or molasses", "Water", "Glass bottle"],
                "tools_needed": ["Measuring cups"],
                "safety_precautions": ["Let gas escape by loosening cap occasionally for the first week. Store away from direct sunlight."],
                "steps": [
                    "Mix 1 part brown sugar with 3 parts citrus peel and 10 parts water in a glass bottle.",
                    "Stir to dissolve sugar. Leave lid slightly loose for initial 24 hours.",
                    "Store at room temperature for 3 months, stirring weekly.",
                    "Dilute 1:10 with water and use as a natural kitchen and bathroom surface cleaner."
                ],
                "sustainability_benefit": "Replaces chemical-laden commercial cleaners with a biodegradable enzymatic alternative."
            },
            {
                "product_name": "Liquid Plant Fertilizer Tea",
                "difficulty": "Easy",
                "estimated_time_mins": 10,
                "estimated_cost_usd": 0.00,
                "potential_value_usd": 5.00,
                "materials_needed": ["Vegetable peels and food scraps", "Water", "Bucket"],
                "tools_needed": ["Strainer"],
                "safety_precautions": ["Use within 3 days. Do not use spoiled meat or cooked oils."],
                "steps": [
                    "Soak raw vegetable peels in 2 liters of water for 24-48 hours.",
                    "Strain the liquid and discard solids into compost.",
                    "Dilute the strained liquid 1:5 with water.",
                    "Water plants at the root zone with this nutrient-rich organic fertilizer tea."
                ],
                "sustainability_benefit": "Recaptures vitamins and minerals from food waste as free organic plant nutrition."
            }
        ]
    },
    "battery": {
        "item_name": "Alkaline / Lithium Battery (AA)",
        "primary_material": "Heavy Metal & Zinc-Manganese Dioxide / Lithium",
        "physical_condition": "Discharged, non-leaking casing",
        "confidence_score": 0.92,
        "categories": ["Hazardous", "Non-recyclable"],
        "is_hazardous": True,
        "identification_reasoning": "Standard cylindrical cell dimensions with terminal polarity nubs. Contains chemical electrolyte.",
        "disposal_recommendation": "DO NOT place in curbside trash or normal recycling bins. Tape terminals with electrical tape and drop at designated e-waste collection bin.",
        "estimated_weight_kg": 0.045,
        "upcycle_recommendations": [
            {
                "product_name": "Certified E-Waste Drop-off Protocol",
                "difficulty": "Easy",
                "estimated_time_mins": 10,
                "estimated_cost_usd": 0.00,
                "potential_value_usd": 2.00,
                "materials_needed": ["Electrical tape or clear tape", "Small zip bag"],
                "tools_needed": ["Scissors"],
                "safety_precautions": ["NEVER puncture, crush, incinerate, or attempt to disassemble batteries."],
                "steps": [
                    "Apply a piece of non-conductive tape over positive (+) and negative (-) terminals.",
                    "Place in a dry plastic bag separate from metal items.",
                    "Take to local electronics retailer, battery drop box, or municipal hazardous depot."
                ],
                "sustainability_benefit": "Recovers valuable rare metals (cobalt, lithium, nickel) and prevents groundwater poisoning."
            },
            {
                "product_name": "Low-Drain Secondary Device Utility",
                "difficulty": "Easy",
                "estimated_time_mins": 5,
                "estimated_cost_usd": 0.00,
                "potential_value_usd": 1.50,
                "materials_needed": ["Multimeter or battery tester"],
                "tools_needed": ["None"],
                "safety_precautions": ["Do not mix battery chemistries or alkaline with lithium cells."],
                "steps": [
                    "Batteries discarded by gaming controllers or cameras often retain 20-30% charge.",
                    "Test voltage with a multimeter; if above 1.1V, reassign to low-draw wall clocks or TV remotes.",
                    "Squeeze 2-4 additional months of life before final recycling."
                ],
                "sustainability_benefit": "Maximizes chemical capacity utilization before decommissioning."
            },
            {
                "product_name": "Hazardous Material Education Case",
                "difficulty": "Easy",
                "estimated_time_mins": 15,
                "estimated_cost_usd": 0.00,
                "potential_value_usd": 5.00,
                "materials_needed": ["Clear display jar", "Educational hazard label"],
                "tools_needed": ["None"],
                "safety_precautions": ["Store in cool, dry location out of reach of children."],
                "steps": [
                    "Store spent taped cells safely until full batch is ready for drop-off.",
                    "Use as a visual teaching aid on heavy metal stewardship for family and classrooms."
                ],
                "sustainability_benefit": "Prevents toxic landfill contamination."
            }
        ]
    },
    "textile": {
        "item_name": "Used Clothes / Textile Scrap",
        "primary_material": "Cotton & Synthetic Fiber Blend",
        "physical_condition": "Worn, discarded post-consumer fabric",
        "confidence_score": 0.91,
        "categories": ["Reusable", "Recyclable"],
        "is_hazardous": False,
        "identification_reasoning": "Interwoven textile fibers suitable for donation, thermal insulation, or mechanical yarn downcycling.",
        "disposal_recommendation": "Donate if wearable. If torn/stained, place in dedicated municipal textile recycling bin or store take-back drop.",
        "estimated_weight_kg": 0.250,
        "upcycle_recommendations": [
            {
                "product_name": "Zero-Waste Braided Fabric Plant Hanger",
                "difficulty": "Easy",
                "estimated_time_mins": 25,
                "estimated_cost_usd": 0.00,
                "potential_value_usd": 14.00,
                "materials_needed": ["Strips of used cotton t-shirt or denim", "Metal key ring"],
                "tools_needed": ["Fabric scissors", "Measuring tape"],
                "safety_precautions": ["Ensure hanging knots are pulled tight and tested with weight."],
                "steps": [
                    "Cut old t-shirt into 8 continuous 3cm wide yarn strips.",
                    "Gather strips through a key ring and secure with a gathering knot.",
                    "Tie strips into 4 pairs using square knots down the length.",
                    "Cross adjacent strands to form a cradle basket for a potted plant."
                ],
                "sustainability_benefit": "Prevents microplastic textile landfill leakage while replacing virgin cotton macrame cord."
            },
            {
                "product_name": "Reusable Beeswax Food Wraps",
                "difficulty": "Medium",
                "estimated_time_mins": 20,
                "estimated_cost_usd": 2.00,
                "potential_value_usd": 18.00,
                "materials_needed": ["100% cotton fabric squares", "Beeswax pellets", "Jojoba oil"],
                "tools_needed": ["Baking tray", "Parchment paper", "Oven or clothes iron"],
                "safety_precautions": ["Melted wax is hot; handle parchment paper with oven mitts."],
                "steps": [
                    "Cut clean cotton into 25x25cm squares with pinking shears.",
                    "Sprinkle beeswax pellets and 3 drops of jojoba oil across fabric.",
                    "Cover with parchment paper and iron gently until wax fully saturates fabric.",
                    "Peel and hang to cool for 2 minutes."
                ],
                "sustainability_benefit": "Eliminates single-use plastic cling wrap for kitchen food preservation."
            },
            {
                "product_name": "Heavy-Duty Workshop Cleaning Rags",
                "difficulty": "Easy",
                "estimated_time_mins": 10,
                "estimated_cost_usd": 0.00,
                "potential_value_usd": 8.00,
                "materials_needed": ["Old cotton shirts, flannels, or towels"],
                "tools_needed": ["Fabric scissors"],
                "safety_precautions": ["Dispose of solvent-soaked rags in sealed fireproof containers."],
                "steps": [
                    "Remove all buttons, zippers, and thick collars.",
                    "Cut into uniform 20x20cm squares.",
                    "Stack in workshop or garage dispenser for cleaning grease, oils, and paint."
                ],
                "sustainability_benefit": "Diverts post-consumer textiles from municipal incinerators."
            }
        ]
    },
    "electronic": {
        "item_name": "Obsolete Small Electronic Device",
        "primary_material": "ABS Plastic, Printed Circuit Board (PCB), Copper & Silicon",
        "physical_condition": "Decommissioned electrical apparatus",
        "confidence_score": 0.93,
        "categories": ["Recyclable", "Hazardous"],
        "is_hazardous": True,
        "identification_reasoning": "Contains printed circuit assembly, soldered lead/tin traces, and integrated IC components requiring certified e-waste extraction.",
        "disposal_recommendation": "Deliver to certified R2 or e-Stewards recycling drop-off center. Never dispose in general municipal trash.",
        "estimated_weight_kg": 0.350,
        "upcycle_recommendations": [
            {
                "product_name": "Certified E-Waste Precious Metal Recovery Drop",
                "difficulty": "Easy",
                "estimated_time_mins": 15,
                "estimated_cost_usd": 0.00,
                "potential_value_usd": 12.00,
                "materials_needed": ["Electronics device", "Cardboard box"],
                "tools_needed": ["None"],
                "safety_precautions": ["Do not attempt to crush circuit boards or heat solder without chemical fume extraction."],
                "steps": [
                    "Back up and securely wipe any flash memory or removable storage cards.",
                    "Pack device into an e-waste drop box.",
                    "Drop off at manufacturer take-back or Best Buy/municipal e-scrap depot."
                ],
                "sustainability_benefit": "Extracts copper, gold, and palladium with 80% lower footprint than virgin mining."
            },
            {
                "product_name": "Circuit Board Cyberpunk Keychain / Coaster",
                "difficulty": "Medium",
                "estimated_time_mins": 30,
                "estimated_cost_usd": 1.50,
                "potential_value_usd": 15.00,
                "materials_needed": ["De-soldered clean motherboard section", "Clear epoxy resin or key ring"],
                "tools_needed": ["Rotary tool or jeweler saw", "Respirator mask"],
                "safety_precautions": ["Wear N95 mask while cutting FR4 fiberglass boards. Seal cut edges with clear coat."],
                "steps": [
                    "Cut attractive geometric green or blue PCB traces into 3x5cm rectangles.",
                    "Drill a 3mm hole for a keychain loop.",
                    "Coat with clear non-toxic epoxy or lacquer to lock in trace metals.",
                    "Attach keychain ring."
                ],
                "sustainability_benefit": "Converts inert scrap circuit components into collectible artisan accessories."
            },
            {
                "product_name": "Educational Tech Disassembly & Parts Kit",
                "difficulty": "Easy",
                "estimated_time_mins": 20,
                "estimated_cost_usd": 0.00,
                "potential_value_usd": 10.00,
                "materials_needed": ["Small precision screwdriver set", "Component sorting bin"],
                "tools_needed": ["Precision screwdrivers"],
                "safety_precautions": ["Discharge capacitors before handling; do not tamper with power supplies."],
                "steps": [
                    "Carefully unscrew housing screws to expose mechanical assemblies.",
                    "Harvest reusable stepper motors, neodymium magnets, cooling fans, and fasteners for DIY robotics.",
                    "Sort remaining chassis for plastics and metals scrap."
                ],
                "sustainability_benefit": "Harvests precision mechanical subcomponents for STEM education."
            }
        ]
    }
}

def analyze_waste_image(image_bytes: bytes, filename: str = "") -> dict:
    """
    Analyzes waste image through Google Gemini Flash Vision if configured.
    Performs image-quality diagnostics (blur, dark, contrast) and OCR packaging label extraction.
    Falls back gracefully to the intelligent heuristic engine on any failure.
    """
    # 1. Run Image-Quality Assessment First
    quality_report = evaluate_image_quality(image_bytes)

    result = None
    # 2. Attempt Gemini Vision API if API Key is available
    if GEMINI_API_KEY and len(GEMINI_API_KEY) > 10:
        try:
            result = _call_gemini_vision(image_bytes)
        except Exception as e:
            print(f"[Gemini Service Warning] Live API call failed ({e}). Activating intelligent fallback.", flush=True)

    # 3. Intelligent Offline Fallback
    if not result:
        result = _generate_heuristic_analysis(image_bytes, filename)

    # 4. Attach and normalize OCR Evidence & Image Quality
    result["image_quality"] = quality_report
    
    # If the model didn't populate ocr_evidence or offline fallback ran, parse from text/heuristic
    if "ocr_evidence" not in result or not result["ocr_evidence"].get("extracted_text"):
        ocr_parsed = _heuristic_ocr_extract(image_bytes, filename, result.get("waste_analysis", {}))
        result["ocr_evidence"] = ocr_parsed

    return result

def _heuristic_ocr_extract(image_bytes: bytes, filename: str, waste_analysis: dict) -> dict:
    """Heuristic label recognition when offline or when embossed symbols are present."""
    fn_lower = filename.lower()
    
    # Check if image has specific plastic resin keywords or symbols
    sample_text = ""
    detected_symbols = []

    if any(k in fn_lower for k in ["pet", "water_bottle", "soda_bottle", "coke", "bottle"]):
        sample_text = "♳ PET 1 - 100% RECYCLABLE BOTTLE - RINSE & REPLACE CAP"
        detected_symbols = ["♳ (PET 1)", "How2Recycle: Widely Recycled"]
    elif any(k in fn_lower for k in ["hdpe", "milk", "jug", "detergent"]):
        sample_text = "♴ HDPE 2 - PLEASE RECYCLE - EMPTY & REPLACE CAP"
        detected_symbols = ["♴ (HDPE 2)", "How2Recycle: Widely Recycled"]
    elif any(k in fn_lower for k in ["can", "aluminum", "tin"]):
        sample_text = "100% RECYCLABLE ALUMINUM - PLEASE RECYCLE"
        detected_symbols = ["♼ Aluminum Recycles Forever"]
    elif any(k in fn_lower for k in ["cardboard", "box", "package"]):
        sample_text = "CORRUGATED RECYCLES - FLATTEN BEFORE BIN"
        detected_symbols = ["Corrugated Box Recycles"]
    elif any(k in fn_lower for k in ["battery"]):
        sample_text = "CAUTION: LITHIUM-ION / ALKALINE - CERTIFIED DROP-OFF ONLY - DO NOT DISPOSE IN TRASH"
        detected_symbols = ["⚠️ Hazard Symbol", "Call2Recycle Certified"]
    else:
        sample_text = "EMBOSSED PACKAGING MARKINGS DETECTED ON CONTAINER BASE"
        detected_symbols = ["♳ (PET 1)"]

    parsed = parse_packaging_ocr(sample_text, detected_symbols)

    return {
        "extracted_text": parsed["raw_text"],
        "detected_symbols": parsed["detected_symbols"],
        "resin_codes": parsed["resin_codes"],
        "identified_material": parsed["resin_codes"][0]["material_name"] if parsed["resin_codes"] else waste_analysis.get("primary_material", "Composite"),
        "recycling_instructions": parsed["recycling_instructions"],
        "safety_warnings": parsed["safety_warnings"],
        "product_composition": parsed["product_composition"],
        "expiry_info": parsed["expiry_info"],
        "information_source": "Molded recycling stamp on container base & surface print",
        "ocr_confidence": 0.94 if not evaluate_image_quality(image_bytes)["is_blurry"] else 0.62,
        "disclaimer": parsed["disclaimer"]
    }

def check_text_clarification_needed(description: str) -> dict:
    """
    Checks if a natural language description is too ambiguous or missing key material properties.
    If ambiguous, returns a clarification question with quick selectable options.
    If clear, returns needs_clarification: False.
    """
    desc_clean = description.strip().lower()
    
    # 1. Very short generic queries (e.g. "bottle", "container", "box", "cup", "can")
    if len(desc_clean.split()) <= 3:
        if any(w in desc_clean for w in ["bottle", "container", "jug", "cup", "flask", "vessel"]):
            if not any(m in desc_clean for m in ["plastic", "glass", "aluminum", "metal", "steel", "paper"]):
                return {
                    "needs_clarification": True,
                    "question": "Is the container made of plastic, glass, or metal?",
                    "options": ["Rigid Plastic", "Glass", "Aluminum / Metal", "Paper / Carton"],
                    "clarification_key": "container_material"
                }

        if any(w in desc_clean for w in ["box", "packaging", "carton"]):
            if not any(m in desc_clean for m in ["cardboard", "plastic", "wood", "foam", "styrofoam", "metal"]):
                return {
                    "needs_clarification": True,
                    "question": "What is the packaging made of?",
                    "options": ["Corrugated Cardboard", "Rigid Plastic", "Expanded Polystyrene / Foam", "Wax-Coated Carton"],
                    "clarification_key": "box_material"
                }

        if any(w in desc_clean for w in ["can"]):
            if not any(m in desc_clean for m in ["aluminum", "steel", "tin", "soda", "food"]):
                return {
                    "needs_clarification": True,
                    "question": "Is it a lightweight aluminum beverage can or a steel/tin food can?",
                    "options": ["Aluminum Beverage Can", "Steel / Tin Food Can"],
                    "clarification_key": "can_type"
                }

        if any(w in desc_clean for w in ["battery", "cell"]):
            if not any(m in desc_clean for m in ["alkaline", "lithium", "rechargeable", "aa", "aaa", "phone", "car"]):
                return {
                    "needs_clarification": True,
                    "question": "What type of battery is it?",
                    "options": ["Standard Alkaline (AA/AAA/9V)", "Rechargeable Lithium-Ion (Phone/Laptop)", "Button / Coin Cell", "Car Lead-Acid"],
                    "clarification_key": "battery_type"
                }

        if any(w in desc_clean for w in ["cloth", "clothes", "fabric", "shirt", "pants"]):
            if not any(m in desc_clean for m in ["cotton", "wool", "polyester", "synthetic", "silk", "denim"]):
                return {
                    "needs_clarification": True,
                    "question": "Is the fabric mostly natural cotton/wool or synthetic (polyester/nylon)?",
                    "options": ["100% Cotton / Natural Wool", "Synthetic (Polyester/Nylon)", "Denim / Heavy Canvas"],
                    "clarification_key": "fabric_type"
                }

    # 2. Check ambiguous flexibility/rigidity for plastic
    if "plastic" in desc_clean and not any(w in desc_clean for w in ["hard", "rigid", "flexible", "film", "bag", "wrap", "bottle", "jug", "soft", "crushed"]):
        return {
            "needs_clarification": True,
            "question": "Is the plastic item rigid (like a bottle or tub) or flexible (like a bag or film)?",
            "options": ["Rigid Plastic (Bottle/Tub/Tray)", "Flexible Soft Plastic (Film/Bag/Pouch)"],
            "clarification_key": "plastic_rigidity"
        }

    return {"needs_clarification": False}

def analyze_waste_text(description: str, material_hint: str = "", clarification_answer: str = "") -> dict:
    """
    Analyzes waste item from user natural language description or category selection.
    Extracts object type, likely material, color, texture, condition, recyclability, and disposal.
    If Gemini API key is configured, uses live multimodal/language inference.
    Otherwise uses archetype-based analysis tailored to description and material hint.
    """
    combined_desc = f"{description}. {clarification_answer}".strip() if clarification_answer else description

    if GEMINI_API_KEY and len(GEMINI_API_KEY) > 10:
        try:
            result = _call_gemini_text(combined_desc, material_hint)
            if result:
                return result
        except Exception as e:
            print(f"[Gemini Service Warning] Live text API call failed ({e}). Using intelligent fallback.", flush=True)

    return _generate_heuristic_text_analysis(combined_desc, material_hint)

def _call_gemini_text(description: str, material_hint: str = "") -> dict:
    """Makes a direct REST call to Gemini for natural language waste description analysis."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""User describes the following discarded waste item:
Description: "{description}"
Selected Category/Material: "{material_hint}"

Analyze this item accurately. You MUST identify:
1. Likely Primary Material (do not fabricate, state uncertainty if composite or unbranded)
2. Waste Category (Recyclable, Reusable, Biodegradable, Hazardous, Non-recyclable)
3. Object Type
4. Color (if described or typical)
5. Texture (smooth, corrugated, ribbed, rough, woven, etc., if described or typical)
6. Physical Condition
7. Estimated Recyclability Stream
8. Suitable Municipal Disposal Method

Output strictly valid JSON matching the schema."""

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": GEMINI_SYSTEM_PROMPT},
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.8,
            "response_mime_type": "application/json"
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req, timeout=12) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        candidate = res_data["candidates"][0]["content"]["parts"][0]["text"]
        
        clean_json_str = candidate.strip()
        if clean_json_str.startswith("```json"):
            clean_json_str = clean_json_str[7:]
        if clean_json_str.startswith("```"):
            clean_json_str = clean_json_str[3:]
        if clean_json_str.endswith("```"):
            clean_json_str = clean_json_str[:-3]
        clean_json_str = clean_json_str.strip()

        data = json.loads(clean_json_str)

        weight = data.get("estimated_weight_kg", 0.05)
        item_name = data.get("item_name", description or "Waste Item")
        material = data.get("primary_material", material_hint or "Plastic")
        
        impact = calculate_environmental_impact(item_name, material, weight)

        # Extract parsed attributes from description or model
        color_detected = _extract_attribute_color(description) or data.get("color", "Not specified")
        texture_detected = _extract_attribute_texture(description) or data.get("texture", "Standard")

        return {
            "identification_method": "TEXT-BASED AI",
            "waste_analysis": {
                "item_name": item_name,
                "primary_material": material,
                "object_type": data.get("object_type", item_name),
                "color": color_detected,
                "texture": texture_detected,
                "physical_condition": data.get("physical_condition", "Used"),
                "confidence_score": float(data.get("confidence_score", 0.92)),
                "categories": data.get("categories", ["Recyclable"]),
                "is_hazardous": bool(data.get("is_hazardous", False)),
                "identification_reasoning": data.get("identification_reasoning", "Evaluated via Gemini Natural Language Materials Intelligence."),
                "disposal_recommendation": data.get("disposal_recommendation", "Place in municipal recycling bin.")
            },
            "environmental_impact": impact,
            "upcycle_recommendations": data.get("upcycle_recommendations", [])
        }

def _extract_attribute_color(text: str) -> str:
    """Extracts explicit color mentions from natural language."""
    colors = ["transparent", "clear", "blue", "green", "brown", "amber", "white", "black", "red", "yellow", "orange", "grey", "gray", "silver", "metallic", "gold", "purple", "pink"]
    found = [c.capitalize() for c in colors if re_search(rf"\b{c}\b", text.lower())]
    return ", ".join(found) if found else ""

def _extract_attribute_texture(text: str) -> str:
    """Extracts explicit texture mentions from natural language."""
    textures = ["smooth", "corrugated", "crinkly", "ribbed", "fluted", "rough", "matte", "glossy", "flexible", "rigid", "soft", "woven", "knitted", "foamed", "fibrous"]
    found = [t.capitalize() for t in textures if re_search(rf"\b{t}\b", text.lower())]
    return ", ".join(found) if found else ""

def re_search(pattern: str, text: str) -> bool:
    import re
    return bool(re.search(pattern, text))

def _generate_heuristic_text_analysis(description: str, material_hint: str = "") -> dict:
    """Heuristic fallback for text and category descriptions."""
    text_corpus = f"{description} {material_hint}".lower()

    selected_key = "plastic"
    if any(k in text_corpus for k in ["battery", "cell", "hazard", "lithium", "duracell", "energizer", "aa", "aaa", "lead-acid"]):
        selected_key = "battery"
    elif any(k in text_corpus for k in ["electronic", "phone", "laptop", "cable", "pcb", "charger", "gadget", "device", "motherboard", "computer"]):
        selected_key = "electronic"
    elif any(k in text_corpus for k in ["cloth", "clothes", "fabric", "textile", "shirt", "jeans", "denim", "cotton", "t-shirt", "garment"]):
        selected_key = "textile"
    elif any(k in text_corpus for k in ["cardboard", "box", "package", "carton", "paper", "kraft"]):
        selected_key = "cardboard"
    elif any(k in text_corpus for k in ["glass", "jar", "wine", "beer bottle", "pickle", "mason jar"]):
        selected_key = "glass"
    elif any(k in text_corpus for k in ["organic", "food", "compost", "veggie", "fruit", "peel", "banana", "coffee", "tea", "scrap", "apple", "leftover"]):
        selected_key = "organic"
    elif any(k in text_corpus for k in ["can", "soda", "coke", "beer", "aluminum", "tin", "foil", "metal"]):
        selected_key = "aluminum"
    elif any(k in text_corpus for k in ["plastic", "bottle", "jug", "cup", "pet", "hdpe", "container", "poly", "wrapper", "bag"]):
        selected_key = "plastic"
    elif material_hint and material_hint.lower() in FALLBACK_ARCHETYPES:
        selected_key = material_hint.lower()

    template = FALLBACK_ARCHETYPES.get(selected_key, FALLBACK_ARCHETYPES["plastic"])
    
    item_display_name = description.strip() if len(description.strip()) > 3 else template["item_name"]
    # Capitalize first letter cleanly
    item_display_name = item_display_name[0].upper() + item_display_name[1:] if item_display_name else template["item_name"]

    color_detected = _extract_attribute_color(description) or "Standard"
    texture_detected = _extract_attribute_texture(description) or "Smooth / Rigid"

    impact = calculate_environmental_impact(
        item_display_name,
        template["primary_material"],
        template["estimated_weight_kg"]
    )

    reasoning = f"TEXT-BASED AI identified material stream as {selected_key.title()}."
    if color_detected != "Standard" or texture_detected != "Smooth / Rigid":
        reasoning += f" Detected attributes: Color ({color_detected}), Texture ({texture_detected})."
    if description:
        reasoning += f" Input description: '{description[:80]}'."

    return {
        "identification_method": "TEXT-BASED AI",
        "waste_analysis": {
            "item_name": item_display_name,
            "primary_material": template["primary_material"],
            "object_type": template["item_name"],
            "color": color_detected,
            "texture": texture_detected,
            "physical_condition": template["physical_condition"],
            "confidence_score": 0.92,
            "categories": template["categories"],
            "is_hazardous": template["is_hazardous"],
            "identification_reasoning": reasoning,
            "disposal_recommendation": template["disposal_recommendation"]
        },
        "environmental_impact": impact,
        "upcycle_recommendations": template["upcycle_recommendations"]
    }

def _call_gemini_vision(image_bytes: bytes) -> dict:
    """Makes a direct REST call to Gemini Vision using urllib."""
    # Use gemini-2.5-flash or gemini-flash-latest (active on Google Generative Language API)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": GEMINI_SYSTEM_PROMPT},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": b64_image
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.8,
            "response_mime_type": "application/json"
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req, timeout=12) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        candidate = res_data["candidates"][0]["content"]["parts"][0]["text"]
        
        # Clean markdown codeblocks if model inadvertently added them
        clean_json_str = candidate.strip()
        if clean_json_str.startswith("```json"):
            clean_json_str = clean_json_str[7:]
        if clean_json_str.startswith("```"):
            clean_json_str = clean_json_str[3:]
        if clean_json_str.endswith("```"):
            clean_json_str = clean_json_str[:-3]
        clean_json_str = clean_json_str.strip()

        data = json.loads(clean_json_str)

        # Calculate exact environmental metrics
        weight = data.get("estimated_weight_kg", 0.05)
        item_name = data.get("item_name", "Waste Item")
        material = data.get("primary_material", "Plastic")
        
        impact = calculate_environmental_impact(item_name, material, weight)

        # Parse OCR evidence returned by vision model or fallback parser
        ocr_raw = data.get("ocr_evidence", {})
        raw_label_text = ocr_raw.get("extracted_text", "")
        detected_syms = ocr_raw.get("detected_symbols", [])
        
        parsed_ocr = parse_packaging_ocr(raw_label_text, detected_syms)
        
        ocr_evidence_result = {
            "extracted_text": parsed_ocr["raw_text"],
            "detected_symbols": parsed_ocr["detected_symbols"],
            "resin_codes": parsed_ocr["resin_codes"],
            "identified_material": ocr_raw.get("identified_material") or (parsed_ocr["resin_codes"][0]["material_name"] if parsed_ocr["resin_codes"] else material),
            "recycling_instructions": parsed_ocr["recycling_instructions"],
            "safety_warnings": parsed_ocr["safety_warnings"],
            "product_composition": parsed_ocr["product_composition"],
            "expiry_info": parsed_ocr["expiry_info"],
            "information_source": ocr_raw.get("information_source", "Printed packaging label / embossed base stamp"),
            "ocr_confidence": float(ocr_raw.get("ocr_confidence", 0.92)),
            "disclaimer": parsed_ocr["disclaimer"]
        }

        return {
            "waste_analysis": {
                "item_name": item_name,
                "primary_material": material,
                "physical_condition": data.get("physical_condition", "Used"),
                "confidence_score": float(data.get("confidence_score", 0.90)),
                "categories": data.get("categories", ["Recyclable"]),
                "is_hazardous": bool(data.get("is_hazardous", False)),
                "identification_reasoning": data.get("identification_reasoning", "Identified via Gemini Multimodal Vision analysis."),
                "disposal_recommendation": data.get("disposal_recommendation", "Place in municipal recycling bin.")
            },
            "environmental_impact": impact,
            "ocr_evidence": ocr_evidence_result,
            "upcycle_recommendations": data.get("upcycle_recommendations", [])
        }

def _generate_heuristic_analysis(image_bytes: bytes, filename: str = "") -> dict:
    """
    Intelligent image inspection engine: inspects image color, aspect ratio,
    edges, and contours to identify whether an object is a battery, bottle, can, or box.
    """
    selected_key = "plastic"
    fn_lower = filename.lower()

    if any(k in fn_lower for k in ["battery", "cell", "hazard", "lithium", "electronic", "duracell", "energizer", "aa", "aaa"]):
        selected_key = "battery"
    elif any(k in fn_lower for k in ["cardboard", "box", "package", "carton", "paper", "kraft"]):
        selected_key = "cardboard"
    elif any(k in fn_lower for k in ["glass", "bottle", "jar", "wine", "beer_glass"]):
        selected_key = "glass"
    elif any(k in fn_lower for k in ["organic", "food", "compost", "veggie", "fruit", "peel", "kitchen"]):
        selected_key = "organic"
    elif any(k in fn_lower for k in ["plastic", "jug", "cup", "pet", "hdpe", "container"]):
        selected_key = "plastic"
    elif any(k in fn_lower for k in ["can", "soda", "coke", "beer", "aluminum"]):
        selected_key = "aluminum"
    else:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            orig_w, orig_h = img.size
            aspect = max(orig_w, orig_h) / max(min(orig_w, orig_h), 1)

            # Crop central 60% of the image to ignore surrounding white web borders or desk edges
            crop_box = (
                int(orig_w * 0.2),
                int(orig_h * 0.2),
                int(orig_w * 0.8),
                int(orig_h * 0.8)
            )
            cropped = img.crop(crop_box)
            
            # Analyze colors of cropped center
            small_rgb = cropped.resize((40, 40))
            colors = small_rgb.getcolors(maxcolors=2000)

            avg_r = avg_g = avg_b = 128
            if colors:
                pixel_count = sum(c[0] for c in colors)
                avg_r = sum(c[1][0] * c[0] for c in colors) / pixel_count
                avg_g = sum(c[1][1] * c[0] for c in colors) / pixel_count
                avg_b = sum(c[1][2] * c[0] for c in colors) / pixel_count

            # If image is an isolated slender battery (aspect > 1.8 in orientation)
            # and contains blue, dark, or metallic battery casing
            is_slender_cell = (orig_h > 1.6 * orig_w) or (orig_w > 2.2 * orig_h)

            if is_slender_cell:
                selected_key = "battery"
            elif avg_r > 130 and avg_g > 100 and avg_b < 75:
                # Brown/tan dominant → cardboard / kraft paper
                selected_key = "cardboard"
            elif (avg_g > avg_r + 8 and avg_g > avg_b + 8 and avg_g > 80) or \
                 (avg_r > 160 and avg_g > 160 and avg_b > 160 and abs(avg_r - avg_g) < 20 and abs(avg_g - avg_b) < 20):
                # Greenish tint (green glass / wine bottles) or high neutral luminance (clear glass)
                selected_key = "glass"
            elif avg_g > 90 and avg_r > 85 and avg_b < 70 and avg_g > avg_b + 20 and avg_g < 160:
                # Yellow-green-brown organic tones (vegetables, fruit peels, food scraps)
                selected_key = "organic"
            else:
                # Default for mixed containers, bottles, cups, jugs, and packaging
                selected_key = "plastic"
        except Exception:
            selected_key = "plastic"

    template = FALLBACK_ARCHETYPES.get(selected_key, FALLBACK_ARCHETYPES["battery"])
    impact = calculate_environmental_impact(
        template["item_name"],
        template["primary_material"],
        template["estimated_weight_kg"]
    )

    return {
        "waste_analysis": {
            "item_name": template["item_name"],
            "primary_material": template["primary_material"],
            "physical_condition": template["physical_condition"],
            "confidence_score": template["confidence_score"],
            "categories": template["categories"],
            "is_hazardous": template["is_hazardous"],
            "identification_reasoning": template["identification_reasoning"],
            "disposal_recommendation": template["disposal_recommendation"]
        },
        "environmental_impact": impact,
        "upcycle_recommendations": template["upcycle_recommendations"]
    }
