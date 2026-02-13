"""
Central database for roofing product keywords and pricing.
Auto-generated from price_list.xlsx by excel_to_database.py.
Referenced by file_extractor.py and buildingfootprintquery.py.
"""

# ---------------------------------------------------------------------------
# Pricing per unit â€“ aggregated from price_list.xlsx
# Each entry: key â†’ {avg, min, max, count, unit, sample_descriptions}
# ---------------------------------------------------------------------------
PRICING = {
    "DensDeck_Coverboard": {
        "canonical_name": "DensDeck Coverboard",
        "category": "Coverboard",
        "avg_price": 33.52,
        "min_price": 29.00,
        "max_price": 37.40,
        "count": 4,
        "unit": "SHT",
        "sample_descriptions": ["DENSDECK PRIME ROOF BOARD 12inX4ftX8ft", "1/4\"X4'X8' Densdeck Primed", "1/2\"X4'X8' Densdeck Primed"],
    },
    "Gypsum_Fiber_Coverboard": {
        "canonical_name": "Gypsum Fiber Coverboard",
        "category": "Coverboard",
        "avg_price": 29.62,
        "min_price": 15.77,
        "max_price": 34.00,
        "count": 13,
        "unit": "Sheet",
        "sample_descriptions": ["SECUROCK GYPSUM FBR 3/8inX4 X8", "SECUROCK GYPSUM FBR 1/2inX4 X8", "SECUROCK GYPSUM FIBER ROOF BOARD 12inX4ftX8ft (061052)"],
    },
    "Drainage_Board": {
        "canonical_name": "Drainage Board",
        "category": "Drainage",
        "avg_price": 410.53,
        "min_price": 215.70,
        "max_price": 601.92,
        "count": 7,
        "unit": "Roll",
        "sample_descriptions": ["SOPRADRAIN 15-G 6ftX50ft", "MIRADRAIN 9000 DRAIN BOARD 6X50'", "SOPRADRAIN ECO 5 6ftX65.6ft"],
    },
    "Gutter_Downpipe": {
        "canonical_name": "Gutter / Downpipe",
        "category": "Drainage",
        "avg_price": 13.60,
        "min_price": 1.25,
        "max_price": 20.55,
        "count": 3,
        "unit": "Piece",
        "sample_descriptions": ["Downpipe & Elbow Package", "Gutter and Downpipe Package", "Downpipe Small Square"],
    },
    "Roof_Drain": {
        "canonical_name": "Roof Drain",
        "category": "Drainage",
        "avg_price": 181.77,
        "min_price": 4.95,
        "max_price": 381.00,
        "count": 26,
        "unit": "EA",
        "sample_descriptions": ["Thaler Aluminum Roof Drain -SS 1 1/4", "Bolts Roof Drain Ancon FC-2", "3\" MJ Large Drain Body"],
    },
    "Scupper": {
        "canonical_name": "Scupper",
        "category": "Drainage",
        "avg_price": 74.83,
        "min_price": 30.48,
        "max_price": 206.00,
        "count": 5,
        "unit": "EA",
        "sample_descriptions": ["COPPER SCUPPER 2\"", "COPPER SCUPPER 3\"", "Scupper 6in Closed"],
    },
    "Clips": {
        "canonical_name": "Clips",
        "category": "Fasteners & Hardware",
        "avg_price": 10.19,
        "min_price": 0.50,
        "max_price": 48.06,
        "count": 27,
        "unit": "Piece",
        "sample_descriptions": ["Clip Base Various", "Fixed Clip various - Floating Clip", "LKME ULTIMATE THERMAL CLIP 1.5\""],
    },
    "Fasteners": {
        "canonical_name": "Fasteners",
        "category": "Fasteners & Hardware",
        "avg_price": 447.76,
        "min_price": 113.50,
        "max_price": 1648.20,
        "count": 81,
        "unit": "PL",
        "sample_descriptions": ["Fastener #14 Heavy Duty Drill Point 1.5\" (1M)", "Fastener #14 Heavy Duty Drill Point 2.0\" (1M)", "Fastener #14 Heavy Duty Drill Point 2.5\" (1M)"],
    },
    "Insulation_Plates": {
        "canonical_name": "Insulation Plates",
        "category": "Fasteners & Hardware",
        "avg_price": 269.38,
        "min_price": 242.10,
        "max_price": 314.40,
        "count": 4,
        "unit": "PL",
        "sample_descriptions": ["Plate Barbed Seam 2.0\" MPB-2000 (1M)", "Plate Insulation MP-3000 3.0\" (1M)", "Plate Metal Seam 2.0\" MP-2000 (1M)"],
    },
    "Nails_Staples": {
        "canonical_name": "Nails / Staples",
        "category": "Fasteners & Hardware",
        "avg_price": 29.75,
        "min_price": 0.80,
        "max_price": 91.72,
        "count": 12,
        "unit": "Box",
        "sample_descriptions": ["Roofing Nail various", "Staple Hammer", "NAIL ROUND TOP 1\""],
    },
    "Roof_Anchor": {
        "canonical_name": "Roof Anchor",
        "category": "Fasteners & Hardware",
        "avg_price": 16.99,
        "min_price": 16.99,
        "max_price": 16.99,
        "count": 1,
        "unit": "Box",
        "sample_descriptions": ["Anchor Roof Reusable Hinged c/w Nails"],
    },
    "Screws": {
        "canonical_name": "Screws",
        "category": "Fasteners & Hardware",
        "avg_price": 39.96,
        "min_price": 2.29,
        "max_price": 113.31,
        "count": 8,
        "unit": "Box",
        "sample_descriptions": ["Screw Deck Zinc  various", "#12 dekfast Screw - 2''", "Screw Multipurpose 8x1.5'' (6500) ZN"],
    },
    "Batt_Insulation": {
        "canonical_name": "Batt Insulation",
        "category": "Insulation",
        "avg_price": 91.90,
        "min_price": 46.87,
        "max_price": 149.75,
        "count": 4,
        "unit": "Bdl",
        "sample_descriptions": ["Comfortbatt R24", "Comfortbatt R14 3.5X23", "Comfortbatt R22 5x23"],
    },
    "Fiberboard_Insulation": {
        "canonical_name": "Fiberboard Insulation",
        "category": "Insulation",
        "avg_price": 24.85,
        "min_price": 8.94,
        "max_price": 76.50,
        "count": 11,
        "unit": "SH",
        "sample_descriptions": ["MSL Fiberboard Std.Ctd 1/2in 4 X 4 Sheet", "Fiberboard Std.Ctd 1/2in 2ft X 4ft", "1/2\"X2'X4' Standard Coated Fiberboard (96SF)"],
    },
    "Polyisocyanurate_ISO_Insulation": {
        "canonical_name": "Polyisocyanurate (ISO) Insulation",
        "category": "Insulation",
        "avg_price": 43.62,
        "min_price": 13.67,
        "max_price": 185.00,
        "count": 31,
        "unit": "Sheet",
        "sample_descriptions": ["SOPRA-ISO PLUS- 2.5inX4 X4-", "SOPRA-ISO 2.5inX4 X4", "SOPRA-ISO PLUS HD 1/2inX4ftX8ft"],
    },
    "XPS_Insulation": {
        "canonical_name": "XPS Insulation",
        "category": "Insulation",
        "avg_price": 35.53,
        "min_price": 14.60,
        "max_price": 58.40,
        "count": 8,
        "unit": "Sheet",
        "sample_descriptions": ["SOPRA-XPS 35 SL 2inX2ftX8ft", "SOPRA-XPS 35 SL 3inX2ftX8ft", "SOPRA-XPS 35 SL 4inX2ftX8ft"],
    },
    "Base_Membrane": {
        "canonical_name": "Base Membrane",
        "category": "Membranes",
        "avg_price": 193.85,
        "min_price": 62.75,
        "max_price": 324.95,
        "count": 2,
        "unit": "RL",
        "sample_descriptions": ["SOP VAPOR R BASE SHEET 45\" 5Sq", "Elastoflex WC 30SBS Base Sheet Poly"],
    },
    "Cap_Membrane": {
        "canonical_name": "Cap Membrane",
        "category": "Membranes",
        "avg_price": 216.95,
        "min_price": 216.95,
        "max_price": 216.95,
        "count": 1,
        "unit": "Roll",
        "sample_descriptions": ["Paradiene 30FR TG Cap Sheet"],
    },
    "EPDM_Accessory": {
        "canonical_name": "EPDM Accessory",
        "category": "Membranes",
        "avg_price": 398.99,
        "min_price": 0.62,
        "max_price": 4880.00,
        "count": 41,
        "unit": "Roll",
        "sample_descriptions": ["EPDM Elastoform 9x50", "EPDM P/S OVERLAYMENT STRIP 9inX100ft", "EPDM PS Elastoform 6x100"],
    },
    "EPDM_Membrane": {
        "canonical_name": "EPDM Membrane",
        "category": "Membranes",
        "avg_price": 1119.86,
        "min_price": 571.90,
        "max_price": 1530.00,
        "count": 5,
        "unit": "roll",
        "sample_descriptions": ["Carlisle Sure-Seal 60 mil non - reinforced EPDM 10'", "Carlilse Sure-Seal  60 mil Reinforced  EPDM 10'", "Carlilse Sure-Seal  45 mil Reinforced  EPDM 10'"],
    },
    "PVC_Membrane": {
        "canonical_name": "PVC Membrane",
        "category": "Membranes",
        "avg_price": 810.07,
        "min_price": 262.50,
        "max_price": 1674.20,
        "count": 3,
        "unit": "Roll",
        "sample_descriptions": ["SENTINEL P150 60MIL PVC MEMBRANE", "PVC Membrane Cleaner 5 Gallon", "PVC membrane cleaner"],
    },
    "SBS_Membrane": {
        "canonical_name": "SBS Membrane",
        "category": "Membranes",
        "avg_price": 298.00,
        "min_price": 146.00,
        "max_price": 450.00,
        "count": 2,
        "unit": "Roll",
        "sample_descriptions": ["Tradesman SBS Glass SA Base", "POWERPLY SBS BASE HW"],
    },
    "TPO_Accessory": {
        "canonical_name": "TPO Accessory",
        "category": "Membranes",
        "avg_price": 499.33,
        "min_price": 0.98,
        "max_price": 2699.00,
        "count": 56,
        "unit": "Pce",
        "sample_descriptions": ["TPO inside corners", "TPO molded pipe boots     3/4'' - 8''", "Firestone TPO White 060 10ft x 100ft"],
    },
    "TPO_Membrane": {
        "canonical_name": "TPO Membrane",
        "category": "Membranes",
        "avg_price": 2865.53,
        "min_price": 750.00,
        "max_price": 7805.00,
        "count": 57,
        "unit": "SqFt",
        "sample_descriptions": [".060 mil Sure-weld TPO Membrane 10'", "TREMPLY TPO 45 MIL  120\" X 100'", "TREMPLY TPO FB 45 MIL  120\" X 100'"],
    },
    "Vapour_Barrier_Membrane": {
        "canonical_name": "Vapour Barrier Membrane",
        "category": "Membranes",
        "avg_price": 173.66,
        "min_price": 14.97,
        "max_price": 515.00,
        "count": 14,
        "unit": "Roll",
        "sample_descriptions": ["Membrane 3015 6\"-75' 3/3 Vapour Barrier", "IKO M.V.P. Vapor Barrier 1X32", "IKO M.V.P. Sand Vapor Barrier (36\"X80')"],
    },
    "Coated_Metal_Sheet": {
        "canonical_name": "Coated Metal Sheet",
        "category": "Metal Flashings & Accessories",
        "avg_price": 583.11,
        "min_price": 371.90,
        "max_price": 741.00,
        "count": 5,
        "unit": "Sheet",
        "sample_descriptions": ["TPO COATED METAL 4'X10' GRAY", "Plate Metal Barbed Seam 2.4\" (1M)", "Carlisle TPO Coated Metal 4'X10'"],
    },
    "Drip_Edge": {
        "canonical_name": "Drip Edge",
        "category": "Metal Flashings & Accessories",
        "avg_price": 6.85,
        "min_price": 6.70,
        "max_price": 6.99,
        "count": 2,
        "unit": "EA",
        "sample_descriptions": ["Drip Edge 10ft", "Reversible Drip Edge 10'"],
    },
    "Flashing_General": {
        "canonical_name": "Flashing (General)",
        "category": "Metal Flashings & Accessories",
        "avg_price": 174.46,
        "min_price": 0.59,
        "max_price": 1024.00,
        "count": 45,
        "unit": "18",
        "sample_descriptions": ["Alsan RS 230 Flash Winter 7032 (3)", "Armourbond Flash  2.5mm x 15m", "Alsan RS 230 Flash Summer  7032 (3)"],
    },
    "Metal_Panel": {
        "canonical_name": "Metal Panel",
        "category": "Metal Flashings & Accessories",
        "avg_price": 10.95,
        "min_price": 3.70,
        "max_price": 55.00,
        "count": 9,
        "unit": "lin foot",
        "sample_descriptions": ["WF-ALLCLAD PANEL 24GA Tan", "24Ga Panel", "24 GA 1.5\" RIB x 12.25\" Panel"],
    },
    "Standing_Seam_Metal": {
        "canonical_name": "Standing Seam Metal",
        "category": "Metal Flashings & Accessories",
        "avg_price": 6.34,
        "min_price": 1.20,
        "max_price": 16.99,
        "count": 4,
        "unit": "Piece",
        "sample_descriptions": ["24ga 2'' Standing Seam - 18\":40yr SMP Charcoal", "Standing Seam 3/4\" Clip", "Standing Seam 1 1/2\" Clip"],
    },
    "Coating_Paint": {
        "canonical_name": "Coating / Paint",
        "category": "Miscellaneous",
        "avg_price": 1088.17,
        "min_price": 0.77,
        "max_price": 6409.00,
        "count": 40,
        "unit": "Pail",
        "sample_descriptions": ["Paint various", "Roofcraft Roof and Found Coating 20L", "RESISTO FIBROUS COATING (18.9L)"],
    },
    "Equipment_Torch": {
        "canonical_name": "Equipment / Torch",
        "category": "Miscellaneous",
        "avg_price": 220.19,
        "min_price": 24.85,
        "max_price": 591.45,
        "count": 16,
        "unit": "Roll",
        "sample_descriptions": ["HPRÂ® Torch Base", "Propane Tank various", "Sopraply Torch Base 520 1x10"],
    },
    "Fleece_Reinforcement_Fabric": {
        "canonical_name": "Fleece Reinforcement Fabric",
        "category": "Miscellaneous",
        "avg_price": 1192.69,
        "min_price": 53.15,
        "max_price": 4198.00,
        "count": 22,
        "unit": "Roll",
        "sample_descriptions": ["Alsan 4'' x 165' Fleece", "Alsan RS Fleece 10.3'' x 165' Fleece", "Alsan RS 41'' x 165' Fleece"],
    },
    "Tape": {
        "canonical_name": "Tape",
        "category": "Miscellaneous",
        "avg_price": 425.57,
        "min_price": 0.59,
        "max_price": 2940.00,
        "count": 47,
        "unit": "Piece",
        "sample_descriptions": ["Tape Masking", "Tape measure", "Tape Caution"],
    },
    "Walkway_Pads": {
        "canonical_name": "Walkway Pads",
        "category": "Pavers & Walkways",
        "avg_price": 590.10,
        "min_price": 134.00,
        "max_price": 1048.50,
        "count": 3,
        "unit": "RL",
        "sample_descriptions": ["IKO InnoviTPO Walkway Pad White", "Firestone Premium Walkway Pad", "PEBBLE TREAD WALKPAD 3' X 4' X 3/4\""],
    },
    "Adhesive": {
        "canonical_name": "Adhesive",
        "category": "Sealants & Adhesives",
        "avg_price": 735.19,
        "min_price": 5.02,
        "max_price": 11852.00,
        "count": 91,
        "unit": "PL",
        "sample_descriptions": ["IKO SAM Adhesive 5GAL", "Duotack Foamable Adhesive", "SENTINEL S BONDING ADHESIVE-5 GAL"],
    },
    "Adhesive_Elastocol": {
        "canonical_name": "Adhesive (Elastocol)",
        "category": "Sealants & Adhesives",
        "avg_price": 99.74,
        "min_price": 0.00,
        "max_price": 188.39,
        "count": 8,
        "unit": "36",
        "sample_descriptions": ["Elastocol Stick 19L", "Elastocol 500 19L", "ELASTOCOL 500 (V2024) 19L"],
    },
    "Mastic": {
        "canonical_name": "Mastic",
        "category": "Sealants & Adhesives",
        "avg_price": 359.30,
        "min_price": 5.55,
        "max_price": 3219.00,
        "count": 50,
        "unit": "Piece",
        "sample_descriptions": ["SOPRAMASTIC BLOCK 5inRND CURB", "Sopramastic PF 2L", "Sopramastic SP2 300ml"],
    },
    "Primer": {
        "canonical_name": "Primer",
        "category": "Sealants & Adhesives",
        "avg_price": 282.83,
        "min_price": 9.10,
        "max_price": 3145.00,
        "count": 76,
        "unit": "Pail",
        "sample_descriptions": ["EPDM HP-250 primer", "BLUESKIN PRIMER/ADHESIVE 17L 36/PLT", "Primer CCW-702 5 Gal"],
    },
    "Sealant_General": {
        "canonical_name": "Sealant (General)",
        "category": "Sealants & Adhesives",
        "avg_price": 29.86,
        "min_price": 5.99,
        "max_price": 329.00,
        "count": 25,
        "unit": "Tube",
        "sample_descriptions": ["SOPRASEAL SEALANT", "Sealant Henry 925 BES", "Lap Sealant"],
    },
    "Gooseneck_Vent": {
        "canonical_name": "Gooseneck Vent",
        "category": "Vents & Penetrations",
        "avg_price": 53.21,
        "min_price": 35.65,
        "max_price": 69.55,
        "count": 9,
        "unit": "Piece",
        "sample_descriptions": ["6x6 Gooseneck Vent", "Gooseneck Square Soldered 8 x 8", "8x8 Gooseneck Vents"],
    },
    "Pipe_Boot_Seal": {
        "canonical_name": "Pipe Boot / Seal",
        "category": "Vents & Penetrations",
        "avg_price": 50.48,
        "min_price": 43.50,
        "max_price": 57.45,
        "count": 2,
        "unit": "EA",
        "sample_descriptions": ["CAR PS EPDM M PIPE SEAL 1-6\"", "CAR TPO MLD PIPE SEAL 3/4-8\" WH"],
    },
    "Plumbing_Vent": {
        "canonical_name": "Plumbing Vent",
        "category": "Vents & Penetrations",
        "avg_price": 21.87,
        "min_price": 21.38,
        "max_price": 22.35,
        "count": 2,
        "unit": "Piece",
        "sample_descriptions": ["4'' Plumbing Vent", "3'' Plumbing Vent"],
    },
    "Roof_Hatch": {
        "canonical_name": "Roof Hatch",
        "category": "Vents & Penetrations",
        "avg_price": 1822.12,
        "min_price": 329.95,
        "max_price": 3622.25,
        "count": 12,
        "unit": "Piece",
        "sample_descriptions": ["Bilco NB-20 Hatch 30x54", "Bilco Roof Hatch S-20 36in x30in", "Bilco Roof Hatch S-20 36in x30in"],
    },
    "Vent_Cap": {
        "canonical_name": "Vent Cap",
        "category": "Vents & Penetrations",
        "avg_price": 57.75,
        "min_price": 1.70,
        "max_price": 217.24,
        "count": 15,
        "unit": "Piece",
        "sample_descriptions": ["5'' Vent Cap", "6'' Vent Cap", "TP-250 Prevent Cap 4.0mm (1X8M)"],
    },
    "Plywood_Sheathing": {
        "canonical_name": "Plywood Sheathing",
        "category": "Wood & Sheathing",
        "avg_price": 48.74,
        "min_price": 15.45,
        "max_price": 103.63,
        "count": 5,
        "unit": "Piece",
        "sample_descriptions": ["4X8X3/4 STD FIR SHEATHING", "4X8X1/2 STD FIR SHEATHING", "4X8X3/4 PT BRN SHEATHING"],
    },
    "Wood_Blocking_Lumber": {
        "canonical_name": "Wood Blocking / Lumber",
        "category": "Wood & Sheathing",
        "avg_price": 16.59,
        "min_price": 2.36,
        "max_price": 51.59,
        "count": 19,
        "unit": "Piece",
        "sample_descriptions": ["SPF 2x4x8", "SPF 2x4x10", "SPF 2x6x8"],
    },
    # Per-sqft / per-unit composite rates for satellite-based estimator
    "TPO_60mil_Mechanically_Attached": 5.50,
    "EPDM_60mil_Fully_Adhered": 6.00,
    "ISO_Insulation_2_Layer": 3.75,
    "Parapet_Flashing_Detail": 45.00,
    "HVAC_Curb_Detail": 850.00,
}

# ---------------------------------------------------------------------------
# EPDM ROOF SYSTEM SPECIFIC MATERIALS
# Based on SBS_Worksheet_4_5.xlsm analysis (Rows 60-81)
# ---------------------------------------------------------------------------
EPDM_SPECIFIC_MATERIALS = {
    "EPDM_Membrane_60mil": {
        "canonical_name": "EPDM Membrane 60 mil",
        "category": "Membranes",
        "avg_price": 1119.86,  # From existing PRICING data
        "min_price": 571.90,
        "max_price": 1530.00,
        "count": 5,
        "unit": "roll",
        "size": "10ft x 100ft",
        "coverage": "1000 sqft per roll",
        "sample_descriptions": ["Carlisle Sure-Seal 60 mil non-reinforced EPDM 10'", "Carlisle Sure-Seal 60 mil Reinforced EPDM 10'"],
    },
    "EPDM_Membrane_45mil": {
        "canonical_name": "EPDM Membrane 45 mil",
        "category": "Membranes",
        "avg_price": 1000.00,
        "unit": "roll",
        "size": "10ft x 100ft",
        "coverage": "1000 sqft per roll",
        "sample_descriptions": ["Carlisle Sure-Seal 45 mil Reinforced EPDM 10'"],
    },
    "EPDM_Filter_Fabric": {
        "canonical_name": "Filter Fabric (Soprafilter)",
        "category": "Drainage",
        "avg_price": 380.25,
        "unit": "roll",
        "sample_descriptions": ["Soprafilter drainage fabric"],
        "notes": "Used in inverted/ballasted EPDM systems",
    },
    "EPDM_Drainage_Mat": {
        "canonical_name": "Drainage Mat (Sopradrain 15G)",
        "category": "Drainage",
        "avg_price": 215.70,
        "unit": "roll",
        "size": "6ft x 50ft",
        "coverage": "300 sqft per roll",
        "sample_descriptions": ["Sopradrain 15G 6x50", "SOPRADRAIN 15-G 6ftX50ft"],
        "notes": "Critical for inverted EPDM roof drainage",
    },
    "EPDM_Seam_Tape": {
        "canonical_name": "EPDM Seam Tape",
        "category": "EPDM Accessories",
        "avg_price": 104.86,
        "unit": "roll",
        "size": "3in x 100ft",
        "coverage": "100 linear feet",
        "sample_descriptions": ["Securtape Seam Tape 3in.x100ft"],
        "notes": "Essential for EPDM seam connections",
    },
    "EPDM_PS_Corner": {
        "canonical_name": "EPDM Peel & Stick Corner",
        "category": "EPDM Accessories",
        "avg_price": 10.75,
        "unit": "piece",
        "sample_descriptions": ["PS IS/OS Corner", "EPDM inside/outside corner"],
    },
    "EPDM_Pipe_Flashing": {
        "canonical_name": "EPDM Pipe Flashing",
        "category": "EPDM Accessories",
        "avg_price": 71.65,
        "unit": "piece",
        "size": "1in - 6in diameter",
        "sample_descriptions": ["1in.-6in. PS Pipe Flashing", "CAR PS EPDM M PIPE SEAL 1-6\""],
    },
    "EPDM_Curb_Flash": {
        "canonical_name": "EPDM Curb Flashing",
        "category": "EPDM Accessories",
        "avg_price": 438.00,
        "unit": "roll",
        "size": "18in or 20in width",
        "sample_descriptions": ["Curb Flash 20\", 18\""],
    },
    "EPDM_RUSS_6": {
        "canonical_name": "RUSS 6 inch EPDM Accessory",
        "category": "EPDM Accessories",
        "avg_price": 307.22,
        "unit": "roll",
        "sample_descriptions": ["RUSS 6\""],
    },
    "EPDM_Primer_HP250": {
        "canonical_name": "EPDM HP-250 Primer",
        "category": "Sealants & Adhesives",
        "avg_price": 52.55,
        "unit": "gallon",
        "coverage": "50 sqft per gallon",
        "sample_descriptions": ["HP-250 Primer", "EPDM HP-250 primer"],
        "notes": "EPDM-specific bonding primer",
    },
    "EPDM_Bonding_Adhesive": {
        "canonical_name": "EPDM Bonding Adhesive 90-8-30A",
        "category": "Sealants & Adhesives",
        "avg_price": 198.95,
        "unit": "pail",
        "size": "5 gallon",
        "sample_descriptions": ["Bonding Adhesive 90-8-30A (5gal)"],
        "notes": "Water-based bonding adhesive for EPDM",
    },
    "EPDM_Cav_Grip": {
        "canonical_name": "Cav Grip Adhesive",
        "category": "Sealants & Adhesives",
        "avg_price": 1000.00,
        "unit": "cylinder",
        "sample_descriptions": ["Cav Grip Cylinder Only"],
        "notes": "High-strength EPDM adhesive system",
    },
    "EPDM_Lap_Sealant": {
        "canonical_name": "EPDM Lap Sealant",
        "category": "Sealants & Adhesives",
        "avg_price": 12.71,
        "unit": "tube",
        "coverage": "22 linear feet per tube",
        "sample_descriptions": ["Lap Sealant", "EPDM lap sealant"],
    },
    "EPS_Insulation_EPDM": {
        "canonical_name": "EPS Insulation (for EPDM Inverted)",
        "category": "Insulation",
        "avg_price": 0.31,  # per sqft per inch
        "unit": "sheet",
        "size": "4ft x 4ft",
        "pricing_note": "$0.31 per sqft per inch of thickness",
        "sample_descriptions": ["EPS Type II", "Expanded Polystyrene"],
        "notes": "Commonly used in EPDM inverted roof systems",
    },
    "XPS_Dow_EPDM": {
        "canonical_name": "Dow XPS (for EPDM)",
        "category": "Insulation",
        "avg_price": 52.48,
        "unit": "sheet",
        "sample_descriptions": ["Dow XPS", "Dow Extruded Polystyrene"],
        "notes": "Alternative to EPS for EPDM inverted systems",
    },
}

# ---------------------------------------------------------------------------
# TPO ROOF SYSTEM SPECIFIC MATERIALS
# Based on SBS_Worksheet_4_5.xlsm analysis (Rows 83-100)
# ---------------------------------------------------------------------------
TPO_SPECIFIC_MATERIALS = {
    "TPO_Membrane": {
        "canonical_name": "TPO Membrane",
        "category": "Membranes",
        "avg_price": 2865.53,  # From existing PRICING data
        "min_price": 750.00,
        "max_price": 7805.00,
        "count": 57,
        "unit": "sqft",
        "size": "10ft x 100ft typical",
        "sample_descriptions": [".060 mil Sure-weld TPO Membrane 10'", "TREMPLY TPO 45 MIL 120\" X 100'", "Carlisle or IKO InnoviTPO"],
        "notes": "Heat-welded thermoplastic membrane",
    },
    "TPO_Flashing_24in": {
        "canonical_name": "TPO Flashing 24 inch",
        "category": "TPO Accessories",
        "avg_price": 565.00,
        "unit": "roll",
        "size": "24in x 50ft",
        "coverage": "100 sqft per roll",
        "sample_descriptions": ["TPO Flashing 24\"x50'", "IKO InnoviTPO Flashing 24\""],
    },
    "TPO_Flashing_12in": {
        "canonical_name": "TPO Flashing 12 inch",
        "category": "TPO Accessories",
        "avg_price": 285.00,
        "unit": "roll",
        "size": "12in x 50ft",
        "coverage": "50 sqft per roll",
        "sample_descriptions": ["TPO Flashing 12\"x50'", "IKO InnoviTPO Flashing 12\""],
    },
    "TPO_Pipe_Boot": {
        "canonical_name": "TPO Universal Pipe Boot",
        "category": "TPO Accessories",
        "avg_price": 43.25,
        "unit": "piece",
        "sample_descriptions": ["InnoviTPO Universal Pipe Boot", "TPO molded pipe boots 3/4\" - 8\""],
        "notes": "Adjustable for various pipe sizes",
    },
    "TPO_Corner": {
        "canonical_name": "TPO Inside/Outside Corner",
        "category": "TPO Accessories",
        "avg_price": 16.75,
        "unit": "piece",
        "sample_descriptions": ["TPO In/Out Corner", "TPO inside corners", "TPO outside corners"],
    },
    "TPO_Rhinobond_Plate": {
        "canonical_name": "Rhinobond Plate",
        "category": "TPO Fasteners",
        "avg_price": 603.75,
        "unit": "pallet",
        "sample_descriptions": ["Rhinobond Plate", "Rhinobond induction welding plates"],
        "notes": "For mechanically-attached TPO systems",
    },
    "TPO_Screws": {
        "canonical_name": "TPO Fastening Screws",
        "category": "TPO Fasteners",
        "avg_price": 375.00,
        "unit": "box",
        "sample_descriptions": ["TPO roofing screws", "Deck screws for TPO"],
    },
    "TPO_Tuck_Tape": {
        "canonical_name": "Tuck Tape",
        "category": "TPO Accessories",
        "avg_price": 0.96,
        "unit": "roll",
        "sample_descriptions": ["Tuck Tape", "TPO detail tape"],
    },
    "TPO_Lap_Sealant": {
        "canonical_name": "TPO Lap Sealant",
        "category": "Sealants & Adhesives",
        "avg_price": 12.71,
        "unit": "tube",
        "coverage": "22 linear feet per tube",
        "sample_descriptions": ["Lap Sealant", "TPO lap sealant"],
    },
    "TPO_Primer": {
        "canonical_name": "TPO Primer",
        "category": "Sealants & Adhesives",
        "avg_price": 63.50,
        "unit": "gallon",
        "coverage": "100 sqft per gallon",
        "sample_descriptions": ["TPO Primer 1 gal", "TPO bonding primer"],
        "notes": "Required for TPO membrane bonding",
    },
    "TPO_Bonding_Adhesive_SureWeld": {
        "canonical_name": "TPO Bonding Adhesive SureWeld",
        "category": "Sealants & Adhesives",
        "avg_price": 205.60,
        "unit": "pail",
        "size": "5 gallon",
        "sample_descriptions": ["Bonding Adhesive TPO - SureWeld 5 gal", "Carlisle SureWeld adhesive"],
        "notes": "Water-based bonding adhesive for TPO",
    },
}

# ---------------------------------------------------------------------------
# COMMON MATERIALS (Used in both EPDM and TPO systems)
# Based on SBS_Worksheet_4_5.xlsm analysis (Rows 17-59)
# ---------------------------------------------------------------------------
COMMON_ROOF_MATERIALS = {
    "Vapour_Barrier_Sopravapor": {
        "canonical_name": "Sopravap'r WG 45in",
        "category": "Vapour Barrier",
        "avg_price": 324.95,
        "unit": "roll",
        "size": "45in width",
        "sample_descriptions": ["Sopravap'r WG 45in", "SOP VAPOR R BASE SHEET 45\" 5Sq"],
        "notes": "Used in both EPDM and TPO systems",
    },
    "Vapour_Barrier_TieIn": {
        "canonical_name": "Vapour Barrier Tie In",
        "category": "Vapour Barrier",
        "avg_price": 50.00,
        "unit": "allowance",
        "notes": "Allowance for tying into existing vapour barrier",
    },
    "ISO_2_5_inch": {
        "canonical_name": "2.5 inch ISO Glass",
        "category": "Insulation",
        "avg_price": 25.60,
        "unit": "sheet",
        "sample_descriptions": ["2.5in. ISO Glass", "SOPRA-ISO 2.5inX4 X4"],
    },
    "Tapered_ISO": {
        "canonical_name": "Tapered Insulation",
        "category": "Insulation",
        "avg_price": 3.10,
        "unit": "sqft",
        "sample_descriptions": ["Tapered polyisocyanurate", "Custom tapered ISO"],
        "notes": "For roof drainage - priced per sqft",
    },
    "Densdeck_Half_Inch": {
        "canonical_name": "Densdeck Primed 1/2 inch",
        "category": "Coverboard",
        "avg_price": 34.20,
        "unit": "sheet",
        "size": "4ft x 8ft",
        "sample_descriptions": ["Densdeck Primed 1/2in", "1/2\"X4'X8' Densdeck Primed"],
    },
    "Soprasmart_ISO_HD": {
        "canonical_name": "Soprasmart ISO HD 1/2 inch",
        "category": "Coverboard",
        "avg_price": 63.55,
        "unit": "sheet",
        "sample_descriptions": ["2-1 Soprasmart ISO HD (1/2in)", "Soprasmart Board 2:1"],
        "notes": "Factory laminated ISO + base membrane",
    },
    "Duotack_Adhesive": {
        "canonical_name": "Duotack Foamable Adhesive",
        "category": "Sealants & Adhesives",
        "avg_price": 58.00,
        "unit": "case",
        "sample_descriptions": ["Duotack", "Duotack Foamable Adhesive"],
        "notes": "Typically 2 layers in system",
    },
    "Elastocol_Stick": {
        "canonical_name": "Elastocol Stick 19L",
        "category": "Sealants & Adhesives",
        "avg_price": 160.00,
        "unit": "pail",
        "size": "19 liter",
        "sample_descriptions": ["Elastocol Stick (19L)", "Elastocol Stick 19L", "ELASTOCOL 500 (V2024) 19L"],
        "notes": "Used for both wall and field applications",
    },
    "Roof_Tape_IKO": {
        "canonical_name": "IKO 6 inch Roof Tape",
        "category": "Roofing Accessories",
        "avg_price": 27.90,
        "unit": "roll",
        "sample_descriptions": ["IKO 6in. Roof Tape (Firetape)"],
    },
    "Sopralap_Cover_Strip": {
        "canonical_name": "Sopralap Cover Strip",
        "category": "Roofing Accessories",
        "avg_price": 42.00,
        "unit": "roll",
        "sample_descriptions": ["Sopralap (Cover Strip)"],
    },
}

# ---------------------------------------------------------------------------
# ROOF SYSTEM CONFIGURATIONS
# Complete system specifications for estimating
# ---------------------------------------------------------------------------
ROOF_SYSTEM_CONFIGS = {
    "EPDM_60mil_Fully_Adhered": {
        "description": "EPDM 60 mil Fully Adhered System",
        "base_cost_per_sqft": 6.00,
        "layers": [
            {"product": "Vapour_Barrier_Sopravapor", "attachment": "glued"},
            {"product": "ISO_2_5_inch", "layers": 1, "attachment": "adhesive"},
            {"product": "Densdeck_Half_Inch", "layers": 1, "attachment": "screwed"},
            {"product": "EPDM_Membrane_60mil", "layers": 1, "attachment": "fully_adhered"},
        ],
        "required_materials": [
            "EPDM_Primer_HP250",
            "EPDM_Bonding_Adhesive",
            "EPDM_Seam_Tape",
            "EPDM_Lap_Sealant",
        ],
        "labor_multiplier": 1.2,
    },
    "EPDM_60mil_Ballasted": {
        "description": "EPDM 60 mil Ballasted/Inverted System",
        "base_cost_per_sqft": 5.50,
        "layers": [
            {"product": "Vapour_Barrier_Sopravapor", "attachment": "glued"},
            {"product": "EPDM_Membrane_60mil", "layers": 1, "attachment": "loose_laid"},
            {"product": "EPS_Insulation_EPDM", "layers": 2, "attachment": "loose_laid"},
            {"product": "EPDM_Filter_Fabric", "attachment": "loose_laid"},
            {"product": "EPDM_Drainage_Mat", "attachment": "loose_laid"},
        ],
        "required_materials": [
            "EPDM_Seam_Tape",
            "EPDM_Lap_Sealant",
        ],
        "notes": "Requires ballast (gravel/pavers) not included in material pricing",
        "labor_multiplier": 1.0,
    },
    "TPO_60mil_Mechanically_Attached": {
        "description": "TPO 60 mil Mechanically Attached System",
        "base_cost_per_sqft": 5.50,
        "layers": [
            {"product": "Vapour_Barrier_Sopravapor", "attachment": "glued"},
            {"product": "ISO_2_5_inch", "layers": 1, "attachment": "adhesive"},
            {"product": "Densdeck_Half_Inch", "layers": 1, "attachment": "screwed"},
            {"product": "TPO_Membrane", "layers": 1, "attachment": "mechanically_attached"},
        ],
        "required_materials": [
            "TPO_Rhinobond_Plate",
            "TPO_Screws",
            "TPO_Lap_Sealant",
        ],
        "labor_multiplier": 1.1,
    },
    "TPO_60mil_Fully_Adhered": {
        "description": "TPO 60 mil Fully Adhered System",
        "base_cost_per_sqft": 6.50,
        "layers": [
            {"product": "Vapour_Barrier_Sopravapor", "attachment": "glued"},
            {"product": "ISO_2_5_inch", "layers": 1, "attachment": "adhesive"},
            {"product": "Soprasmart_ISO_HD", "layers": 1, "attachment": "adhesive"},
            {"product": "TPO_Membrane", "layers": 1, "attachment": "fully_adhered"},
        ],
        "required_materials": [
            "TPO_Primer",
            "TPO_Bonding_Adhesive_SureWeld",
            "TPO_Lap_Sealant",
        ],
        "labor_multiplier": 1.3,
    },
}

# ---------------------------------------------------------------------------
# Product keyword database â€“ preserved from original database.py
# Each entry: regex pattern â†’ canonical product name
# ---------------------------------------------------------------------------
PRODUCT_KEYWORDS: dict[str, dict[str, str]] = {
    "Membranes": {
        r"granule\s+surfaced\s+thermofusible\s+cap\s+membrane": "Granule Surfaced Thermofusible Cap Membrane",
        r"cap\s+membrane\s+flash": "Cap Membrane Flashings",
        r"base\s+membrane\s+flash": "Base Membrane Flashings",
        r"vapou?r\s+barrier\s+membrane": "Vapour Barrier Membrane",
        r"liquid\s+membrane\s+flash": "Liquid Membrane Flashing",
        r"sbs\s+membrane": "SBS Membrane",
        r"coverboard\s+with\s+factory\s+laminated\s+base\s+membrane": "Coverboard with Factory Laminated Base Membrane",
        r"membrane\s+pipe\s+seal": "Membrane Pipe Seal",
        r"sacrificial\s+cap\s+membrane": "Sacrificial Cap Membrane (slip sheet)",
        # Soprema SBS products (Div 07 52 01)
        r"sopraply\s+traffic\s+cap": "Sopraply Traffic Cap (SBS Cap Sheet)",
        r"sopraply\s+base\s+520": "Sopraply Base 520 (SBS Base Sheet)",
        r"sopraply\s+stick\s+duo": "Sopraply Stick Duo (Self-Adhered Base)",
        r"soprasmart\s+board": "Soprasmart Board 2:1 (Factory Laminated ISO+Base)",
        r"modified\s+bitumen\s+membrane": "Modified Bitumen Membrane",
        r"2[- ]ply\s+sbs": "2-Ply SBS Membrane System",
        r"inverted.*membrane\s+roof": "Inverted Membrane Roofing",
    },
    "Insulation": {
        r"polyisocyanurate\s+insulation": "Polyisocyanurate Insulation",
        r"fibe?r\s*board\s+insulation": "Fiberboard Insulation",
        r"tapered\s+expanded\s+polystyrene\s+insulation": "Tapered Expanded Polystyrene (EPS) Insulation",
        r"tapered\s+insulation\s+sump": "Tapered Insulation Sump",
        r"xps\s+insulation": "XPS Insulation",
        r"mineral\s+wool\s+insulation": "Mineral Wool Insulation",
        r"spray\s+foam": "Spray Foam Insulation",
        r"drain\s+bowl/?pipe\s+insulation": "Drain Bowl/Pipe Insulation",
        r"type\s+iv\s+xps": "Type IV XPS Insulation",
        # Soprema specific (Div 07 52 01)
        r"sopra-?xps\s+40": "Sopra-XPS 40 Type 4 (Inverted Insulation)",
        r"type\s+4\s+xps": "Type 4 XPS Insulation",
        r"tapered\s+polyisocyanurate": "Tapered Polyisocyanurate Insulation",
    },
    "Coverboard": {
        r"\d+\s*mm\s+coverboard": "Coverboard",
    },
    "Metal Flashings & Accessories": {
        r"metal\s+cap\s+flash": "Metal Cap Flashings",
        r"metal\s+scupper\s+flash": "Metal Scupper Flashings",
        r"metal\s+skirt\s+flash": "Metal Skirt Flashings",
        r"metal\s+counter\s+flash": "Metal Counter Flashings",
        r"metal\s+base\s+flash": "Metal Base Flashings",
        r"metal\s+gooseneck\s+flash": "Metal Gooseneck Flashings",
        r"metal\s+brakeshape": "Metal Brakeshape",
        r"metal\s+debris\s+screen": "Metal Debris Screen",
        r"standing\s+seam": "Standing Seam Metal",
        r"s-lock": "S-Lock Joint",
        r"hem\s+edge": "Hem Edge Detail",
    },
    "Wood & Sheathing": {
        r"plywood\s+sheathing": "Plywood Sheathing",
        r"back-?sloped.*plywood\s+sheathing": "Back-Sloped Plywood Sheathing",
        r"wood\s+blocking": "Wood Blocking",
    },
    "Drainage": {
        r"drain\s+clamping\s+ring": "Drain Clamping Ring",
        r"drain\s+bowl": "Drain Bowl",
        r"sump\s+receiver\s+pan": "Sump Receiver Pan",
        r"lead\s+flash": "Lead Flashings",
        r"overflow\s+scupper": "Overflow Scupper",
        r"roof\s+drain": "Roof Drain",
        r"scupper\s+drain": "Scupper Drain",
        # Soprema / inverted roof (Div 07 52 01)
        r"sopradrain": "Sopradrain EcoVent (Drainage Board)",
        r"filter\s+fabric": "Filter Fabric",
        r"drainage\s+board": "Drainage Board",
    },
    "Fasteners & Hardware": {
        r"pan\s+head\s+(fastener|screw)": "Pan Head Fasteners/Screws",
        r"hex\s+head\s+(fastener|screw)": "Hex Head Fasteners/Screws",
        r"wood\s+screw": "Wood Screws",
        r"neoprene\s+washer": "Neoprene Washers",
        r"\d+\s*mm\s+clips?": "Metal Clips",
        r"roof\s+anchor": "Roof Anchor",
    },
    "Sealants & Adhesives": {
        r"asphaltic\s+primer": "Asphaltic Primer",
        r"mastic": "Mastic",
        r"urethane\s+sealant": "Urethane Sealant",
        r"exterior\s+grade\s+sealant": "Exterior Grade Sealant",
        r"membrane\s+compatible\s+sealant": "Membrane Compatible Sealant",
        r"adhesive\s+ribbon": "Adhesive Ribbon",
        r"(?<!urethane\s)(?<!exterior\sgrade\s)(?<!membrane\scompatible\s)sealant": "Sealant (General)",
        # Soprema / Div 07 specific
        r"dymonic\s+100": "Dymonic 100 (Polyurethane Sealant)",
        r"masterseal\s+np[\s-]?1": "MasterSeal NP1 (Polyurethane Sealant)",
        r"elastocol": "Elastocol Adhesive",
        r"sopramastic": "Sopramastic",
        r"polyurethane\s+sealant": "Polyurethane Sealant",
    },
    "Pavers & Walkways": {
        r"concrete\s+paver": "Concrete Pavers",
        r"\d+\s*mm\s*x\s*\d+\s*mm\s*x\s*\d+\s*mm\s+paver": "Concrete Pavers (sized)",
    },
    "Vents & Penetrations": {
        r"spun\s+aluminum\s+vent\s+flash": "Spun Aluminum Vent Flashing",
        r"abs\s+pipe": "ABS Pipe",
        r"vent\s+extension\s+pipe": "Vent Extension Pipe",
        r"vent\s+cap": "Vent Cap",
        r"roof\s+hatch": "Roof Hatch",
        r"plumbing\s+vent": "Plumbing Vent",
        r"gooseneck": "Gooseneck Vent",
    },
    "Miscellaneous": {
        r"foam\s+gasket": "Foam Gasket",
        r"polyethylene\s+film": "Polyethylene Film",
        r"tremclad\s+paint": "Tremclad Paint",
        r"fleece\s+reinforcement\s+fabric": "Fleece Reinforcement Fabric",
        r"gypsum\s+auxiliary\s+leveling\s+surface": "Gypsum Auxiliary Leveling Surface",
        r"steel\s+deck": "Steel Deck",
        r"c-?ports?": "C-Port Pipe Supports",
        r"sleepers?": "Sleepers",
        # Inverted roof / ballast
        r"gravel\s+ballast": "Gravel Ballast",
        r"paver\s+pedestal": "Paver Pedestals",
        r"mammouth\s+platinum": "Soprema Mammouth Platinum Warranty",
    },
}

# ---------------------------------------------------------------------------
# NEW product categories discovered from Excel (heuristic match)
# Review and merge into PRODUCT_KEYWORDS above as needed.
# ---------------------------------------------------------------------------
NEW_KEYWORDS_CANDIDATES: dict[str, list[str]] = {
    "Coverboard": [
        "DensDeck Coverboard",
        "Gypsum Fiber Coverboard",
    ],
    "Drainage": [
        "Drainage Board",
        "Gutter / Downpipe",
        "Scupper",
    ],
    "Fasteners & Hardware": [
        "Clips",
        "Fasteners",
        "Insulation Plates",
        "Nails / Staples",
        "Screws",
    ],
    "Insulation": [
        "Batt Insulation",
        "Polyisocyanurate (ISO) Insulation",
    ],
    "Membranes": [
        "Base Membrane",
        "Cap Membrane",
        "EPDM Accessory",
        "EPDM Membrane",
        "PVC Membrane",
        "TPO Accessory",
        "TPO Membrane",
    ],
    "Metal Flashings & Accessories": [
        "Coated Metal Sheet",
        "Drip Edge",
        "Flashing (General)",
        "Metal Panel",
    ],
    "Miscellaneous": [
        "Coating / Paint",
        "Equipment / Torch",
        "Tape",
    ],
    "Pavers & Walkways": [
        "Walkway Pads",
    ],
    "Sealants & Adhesives": [
        "Adhesive",
        "Adhesive (Elastocol)",
        "Primer",
    ],
    "Vents & Penetrations": [
        "Pipe Boot / Seal",
    ],
    "Wood & Sheathing": [
        "Wood Blocking / Lumber",
    ],
}

# ---------------------------------------------------------------------------
# DATABASE USAGE DOCUMENTATION
# ---------------------------------------------------------------------------
"""
DATABASE STRUCTURE AND USAGE GUIDE
===================================

This database now contains four primary sections for roofing material pricing:

1. PRICING (Lines 14-152)
   - General product pricing aggregated from price_list.xlsx
   - Contains avg, min, max prices per unit
   - Covers common materials used across multiple roof types

2. EPDM_SPECIFIC_MATERIALS (Lines 180-310)
   - Materials exclusive to EPDM roofing systems
   - Includes membrane, seam tape, primers, adhesives
   - Critical items: HP-250 primer, seam tape, drainage mat

3. TPO_SPECIFIC_MATERIALS (Lines 312-410)
   - Materials exclusive to TPO roofing systems
   - Includes membrane, flashings, Rhinobond plates
   - Critical items: TPO primer, SureWeld adhesive, heat-welding accessories

4. COMMON_ROOF_MATERIALS (Lines 412-485)
   - Materials used in both EPDM and TPO systems
   - Includes vapour barriers, insulation, coverboard
   - Can be shared across multiple roof configurations

5. ROOF_SYSTEM_CONFIGS (Lines 487-590)
   - Complete system specifications
   - Pre-configured layer assemblies
   - Labor multipliers and base costs per sqft

HOW TO USE THIS DATABASE
=========================

Example 1: Pricing an EPDM Fully Adhered Roof
----------------------------------------------
```python
from database import EPDM_SPECIFIC_MATERIALS, COMMON_ROOF_MATERIALS, ROOF_SYSTEM_CONFIGS

# Get system configuration
system = ROOF_SYSTEM_CONFIGS["EPDM_60mil_Fully_Adhered"]
base_cost = system["base_cost_per_sqft"]  # $6.00/sqft

# Calculate materials for 1000 sqft roof
roof_area = 1000  # square feet

# Membrane cost
membrane_price = EPDM_SPECIFIC_MATERIALS["EPDM_Membrane_60mil"]["avg_price"]
membrane_coverage = 1000  # sqft per roll
membrane_rolls_needed = roof_area / membrane_coverage
membrane_cost = membrane_rolls_needed * membrane_price

# Primer cost
primer = EPDM_SPECIFIC_MATERIALS["EPDM_Primer_HP250"]
primer_coverage = 50  # sqft per gallon
primer_gallons = roof_area / primer_coverage
primer_cost = primer_gallons * primer["avg_price"]

# Seam tape cost (estimate 100 linear feet per 1000 sqft)
seam_tape = EPDM_SPECIFIC_MATERIALS["EPDM_Seam_Tape"]
seam_tape_rolls = 1  # 100ft per roll
seam_tape_cost = seam_tape_rolls * seam_tape["avg_price"]

total_material_cost = membrane_cost + primer_cost + seam_tape_cost
print(f"Total EPDM materials: ${total_material_cost:,.2f}")
```

Example 2: Pricing a TPO Mechanically Attached Roof
----------------------------------------------------
```python
from database import TPO_SPECIFIC_MATERIALS, COMMON_ROOF_MATERIALS, ROOF_SYSTEM_CONFIGS

# Get system configuration
system = ROOF_SYSTEM_CONFIGS["TPO_60mil_Mechanically_Attached"]
base_cost = system["base_cost_per_sqft"]  # $5.50/sqft

# Calculate for 2000 sqft roof
roof_area = 2000

# Membrane (priced per sqft in TPO)
membrane = TPO_SPECIFIC_MATERIALS["TPO_Membrane"]
membrane_cost = roof_area * (membrane["avg_price"] / 1000)  # Convert to per sqft

# Rhinobond plates
plates = TPO_SPECIFIC_MATERIALS["TPO_Rhinobond_Plate"]
plates_per_sqft = 0.8  # typical density
plates_needed = roof_area * plates_per_sqft
plates_cost = (plates_needed / 1000) * plates["avg_price"]  # Priced per pallet

total = membrane_cost + plates_cost
print(f"Total TPO materials: ${total:,.2f}")
```

Example 3: Comparing EPDM vs TPO for Same Building
--------------------------------------------------
```python
from database import ROOF_SYSTEM_CONFIGS

roof_area = 5000  # square feet

# EPDM system
epdm = ROOF_SYSTEM_CONFIGS["EPDM_60mil_Fully_Adhered"]
epdm_material_cost = roof_area * epdm["base_cost_per_sqft"]
epdm_labor_cost = epdm_material_cost * epdm["labor_multiplier"]
epdm_total = epdm_material_cost + epdm_labor_cost

# TPO system
tpo = ROOF_SYSTEM_CONFIGS["TPO_60mil_Mechanically_Attached"]
tpo_material_cost = roof_area * tpo["base_cost_per_sqft"]
tpo_labor_cost = tpo_material_cost * tpo["labor_multiplier"]
tpo_total = tpo_material_cost + tpo_labor_cost

print(f"EPDM Total: ${epdm_total:,.2f}")
print(f"TPO Total: ${tpo_total:,.2f}")
print(f"Difference: ${abs(epdm_total - tpo_total):,.2f}")
```

KEY DIFFERENCES BETWEEN EPDM AND TPO
=====================================

EPDM Systems:
- Rubber-based membrane (60 mil or 45 mil)
- Seams joined with tape and liquid adhesive
- HP-250 primer required
- Can be ballasted (inverted) or fully adhered
- Better for low-slope applications
- Drainage mat required for ballasted systems
- Black membrane (heat absorption consideration)

TPO Systems:
- Thermoplastic membrane (45-60 mil)
- Seams heat-welded (no tape)
- TPO-specific primer and adhesive
- Can be mechanically attached or fully adhered
- Better reflectivity (white membrane)
- Rhinobond induction welding option
- Higher initial cost but potentially longer life

SYSTEM SELECTION CRITERIA
==========================

Choose EPDM when:
- Budget-conscious project
- Low-slope or flat roof
- Ballasted system preferred
- Existing EPDM repairs/replacement
- Less foot traffic expected

Choose TPO when:
- Energy efficiency priority (white membrane)
- Higher durability requirements
- Mechanically-attached preferred
- Higher foot traffic expected
- Warranty requirements favor TPO

NOTES ON PRICING
================

All prices updated as of: June 2025 (per SBS_Worksheet_4_5.xlsm)

Price sources:
- Sage 2025/2026
- Proline 2025
- Convoy April 2023 (some items)
- Roofmart April 2024
- Garland 2025

Labor multipliers:
- EPDM Fully Adhered: 1.2x
- EPDM Ballasted: 1.0x
- TPO Mechanically Attached: 1.1x
- TPO Fully Adhered: 1.3x

These multipliers account for installation complexity, not absolute labor hours.

MAINTENANCE AND UPDATES
========================

This database should be updated when:
1. New price lists are received from suppliers
2. Material specifications change
3. New products are introduced
4. Labor rates or multipliers change
5. System configurations are modified

Contact information for updates:
- Excel source: SBS_Worksheet_4_5.xlsm
- Last updated: February 13, 2026
- Updated by: AI Analysis System
"""