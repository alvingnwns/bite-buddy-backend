from app.services.food_data_service import get_food_data_service


def test_tkpi_resolves_indonesian_and_english_food_names():
    service = get_food_data_service()

    ice_cream = service.resolve_by_name("ice cream")
    spinach = service.resolve_by_name("bayam")

    assert ice_cream is not None
    assert ice_cream["tkpiCode"] == "JP001"
    assert ice_cream["dataSource"] == "TKPI 2020"
    assert float(ice_cream["sugar_g"]) > 0
    assert ice_cream["sugarEstimated"] is True
    assert spinach is not None
    assert float(spinach["fiber_g"]) > 0


def test_tkpi_nutrition_scales_with_portion():
    service = get_food_data_service()
    base = service.calculate_nutrition_for_meal([
        {"tkpiCode": "DR008", "ingredient": "bayam", "weight_g": 100},
    ])
    doubled = service.calculate_nutrition_for_meal([
        {"tkpiCode": "DR008", "ingredient": "bayam", "weight_g": 200},
    ])

    assert base["fiber_g"] == 0.7
    assert doubled["fiber_g"] == 1.4
    assert doubled["kcal"] == base["kcal"] * 2


def test_ai_estimate_is_used_only_without_ground_truth():
    service = get_food_data_service()
    nutrition = service.calculate_nutrition_for_meal([{
        "ingredient": "unknown visible vegetable",
        "weight_g": 150,
        "nutrition_per_100g": {
            "kcal": 30, "carbs_g": 5, "sugar_g": 2,
            "protein_g": 2, "fat_g": 0.5, "fiber_g": 3,
        },
    }])

    assert nutrition["fiber_g"] == 4.5
    assert nutrition["sugar_g"] == 3.0
