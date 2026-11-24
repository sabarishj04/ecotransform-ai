/**
 * EcoTransform AI - Bilingual Translations (English & Tamil / தமிழ்)
 * Fully supports toggling between English and Tamil with live DOM updates.
 */

const TRANSLATIONS = {
  en: {
    // Navigation
    brand_title: "EcoTransform AI",
    nav_scanner: "Waste Scanner",
    nav_dashboard: "Dashboard",
    nav_centres: "Recycling Centres",
    nav_history: "Scan History",

    // Header & Tagline
    hero_title: "AI-Powered Circular Waste Intelligence",
    hero_subtitle: "Identify materials, comply with Indian SWM 2016 segregation rules, and discover verified recycling centres.",
    
    // Scanner Tabs
    tab_camera: "Live Camera",
    tab_upload: "Image Upload",
    tab_barcode: "Barcode / QR",
    tab_text: "Describe Waste",
    tab_manual: "Select Category",

    // Scanner Placeholders
    desc_placeholder: "Describe the item in natural language (e.g. 'Transparent plastic water bottle with blue cap, 500ml')",
    barcode_placeholder: "Enter 12/13-digit EAN/UPC barcode number",
    btn_analyze: "Analyze Waste Material",
    btn_clear: "Clear / Reset",
    btn_sample: "Try Sample Barcode",

    // SWM 2016 Streams
    stream_dry: "Dry Waste (Blue Bin)",
    stream_wet: "Wet Waste (Green Bin)",
    stream_sanitary: "Sanitary Waste (Red Wrap)",
    stream_special: "Special-Care / E-Waste",

    // Results View
    results_title: "Waste Analysis & Impact",
    card_swm_header: "Indian SWM 2016 Segregation Stream",
    card_swm_notice: "Mandatory municipal segregation guideline for India",
    card_calculator_header: "Customizable Weight & Pathway",
    card_calculator_subtitle: "Edit weight in grams (g) or kilograms (kg) to recalculate live Indian impact",
    weight_label: "Material Weight",
    pathway_label: "Diversion Pathway",
    btn_recalculate: "Recalculate",
    how_we_calculate: "How We Calculate Your Impact",

    // Impact Metric Labels
    metric_co2: "CO₂e Avoided",
    metric_landfill: "Waste Diverted",
    metric_water: "Water Saved",
    metric_energy: "Energy Saved",
    metric_weight: "Material Weight",
    metric_scrap: "Scrap Value",

    // Upcycling Blueprints
    blueprints_title: "Waste-to-Wealth Transformation Blueprints",
    blueprints_subtitle: "Curated upcycling recipes designed to create economic and utilitarian value from this item.",

    // Dashboard
    dash_title: "Sustainability & Wealth Dashboard",
    dash_subtitle: "Live tracking of real stored waste data, ecological diversion, and circular economic potential.",
    dash_demo_mode: "Viewing Demo Data",
    dash_user_mode: "Viewing Your Actual Activity",
    dash_toggle_btn: "Switch to My Actual Activity",
    dash_empty_title: "No Personal Scans Logged Yet",
    dash_empty_desc: "Your activity dashboard updates with real stored records whenever you scan or describe an item.",
    btn_start_scan: "Scan Your First Waste Item",

    // KPI Cards
    kpi_scans: "Total Waste Identified",
    kpi_weight: "Total Material Weight",
    kpi_co2: "CO₂e Prevented",
    kpi_scrap: "Estimated Scrap Value",
    kpi_blueprints: "Upcycling Projects",

    // Centres
    centres_title: "Verified Indian Recycling & Recovery Centres",
    centres_subtitle: "Discover authorized municipal dry waste centers (DWCC / MRF), e-waste dismantlers, and composting facilities across Indian cities.",
    filter_city: "Filter by City",
    filter_stream: "Filter by Waste Stream",
    search_centres: "Search by center name, material, or locality...",
    call_centre: "Contact / Call",
    visit_centre: "Official Website"
  },

  ta: {
    // Navigation
    brand_title: "ஈகோ-டிரான்ஸ்பார்ம் AI",
    nav_scanner: "கழிவு ஸ்கேனர்",
    nav_dashboard: "மதிப்பீட்டு பலகை",
    nav_centres: "மறுசுழற்சி மையங்கள்",
    nav_history: "ஸ்கேன் வரலாறு",

    // Header & Tagline
    hero_title: "AI கழிவு நுண்ணறிவு & மறுசுழற்சி வழிகாட்டி",
    hero_subtitle: "கழிவுப் பொருட்களை அடையாளம் கண்டு, இந்திய SWM 2016 விதிகளின்படி பிரித்து, உள்ளூர் மறுசுழற்சி மையங்களை கண்டறியுங்கள்.",
    
    // Scanner Tabs
    tab_camera: "நேரடி கேமரா",
    tab_upload: "புகைப்படம் பதிவேற்று",
    tab_barcode: "பார்கோடு / QR",
    tab_text: "விவரித்து கூறுங்கள்",
    tab_manual: "பிரிவை தேர்ந்தெடு",

    // Scanner Placeholders
    desc_placeholder: "பொருளை விவரிக்கவும் (எ.கா: 'நீல மூடியுடன் கூடிய 500ml பிளாஸ்டிக் தண்ணீர் பாட்டில்')",
    barcode_placeholder: "12 அல்லது 13 இலக்க பார்கோடு எண்ணை உள்ளிடவும்",
    btn_analyze: "கழிவை பகுப்பாய்வு செய்",
    btn_clear: "அழி / மீட்டமை",
    btn_sample: "மாதிரி பார்கோடு முயற்சி செய்",

    // SWM 2016 Streams
    stream_dry: "உலர் கழிவு (நீல தொட்டி)",
    stream_wet: "ஈரக் கழிவு (பச்சை தொட்டி)",
    stream_sanitary: "சுகாதாரக் கழிவு (சிவப்பு பை)",
    stream_special: "சிறப்புக் கழிவு / மின்-கழிவு",

    // Results View
    results_title: "கழிவு பகுப்பாய்வு & தாக்கம்",
    card_swm_header: "இந்திய SWM 2016 கழிவு பிரிப்பு முறை",
    card_swm_notice: "இந்திய நகராட்சி கட்டாய கழிவு பிரிப்பு வழிகாட்டுதல்",
    card_calculator_header: "எடை மற்றும் மறுசுழற்சி முறை மாற்றம்",
    card_calculator_subtitle: "கிராம் (g) அல்லது கிலோகிராமில் (kg) எடையை மாற்றி மறுபகுப்பாய்வு செய்யுங்கள்",
    weight_label: "பொருளின் எடை",
    pathway_label: "பயன்பாட்டு முறை",
    btn_recalculate: "மறுபரிசீலனை செய்",
    how_we_calculate: "நாங்கள் எவ்வாறு கணக்கிடுகிறோம்",

    // Impact Metric Labels
    metric_co2: "தவிர்க்கப்பட்ட CO₂e",
    metric_landfill: "தடுக்கப்பட்ட கழிவு",
    metric_water: "சேமிக்கப்பட்ட நீர்",
    metric_energy: "சேமிக்கப்பட்ட மின்சாரம்",
    metric_weight: "பொருளின் எடை",
    metric_scrap: "பழைய இரும்பு விலை",

    // Upcycling Blueprints
    blueprints_title: "மறுஉருவாக்க (Upcycling) செய்முறைகள்",
    blueprints_subtitle: "இந்த கழிவுப் பொருளில் இருந்து பயனுள்ள கைவினைப் பொருட்கள் தயாரிக்கும் எளிய வழிகாட்டிகள்.",

    // Dashboard
    dash_title: "நிலைத்தன்மை & பொருளாதார பலகை",
    dash_subtitle: "உண்மையான சேமிக்கப்பட்ட கழிவுத் தரவு மற்றும் இந்திய பொருளாதார மதிப்பீடுகள்.",
    dash_demo_mode: "மாதிரித் தரவு (Demo Mode)",
    dash_user_mode: "உங்கள் நேரடி பயனர் செயல்பாடு",
    dash_toggle_btn: "எனது நேரடி செயல்பாட்டிற்கு மாறு",
    dash_empty_title: "இதுவரை ஸ்கேன்கள் எதுவும் பதிவு செய்யப்படவில்லை",
    dash_empty_desc: "நீங்கள் புதிய கழிவுப் பொருட்களை ஸ்கேன் செய்யும் போது உங்கள் நேரடித் தரவு இங்கே தானாக புதுப்பிக்கப்படும்.",
    btn_start_scan: "முதல் பொருளை ஸ்கேன் செய்யுங்கள்",

    // KPI Cards
    kpi_scans: "அடையாளம் காணப்பட்ட கழிவுகள்",
    kpi_weight: "மொத்த கழிவு எடை",
    kpi_co2: "தவிர்க்கப்பட்ட கார்பன்",
    kpi_scrap: "மதிப்பிடப்பட்ட பழைய விலை",
    kpi_blueprints: "உருவாக்கப்பட்ட திட்டங்கள்",

    // Centres
    centres_title: "அங்கீகரிக்கப்பட்ட இந்திய மறுசுழற்சி மையங்கள்",
    centres_subtitle: "நகராட்சி உலர் கழிவு மையங்கள் (DWCC / MRF), மின்-கழிவு பிரிப்பாளர்கள் மற்றும் உரம் தயாரிக்கும் நிலையங்கள்.",
    filter_city: "நகரத்தை தேர்ந்தெடு",
    filter_stream: "கழிவு வகையை தேர்ந்தெடு",
    search_centres: "மையத்தின் பெயர், பொருள் அல்லது பகுதி கொண்டு தேடவும்...",
    call_centre: "தொடர்பு கொள்ள",
    visit_centre: "அதிகாரப்பூர்வ தளம்"
  }
};
