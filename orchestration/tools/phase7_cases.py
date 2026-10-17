"""Unseen phrasing cases for the separately authorized real-model campaign."""

CASES = [
    ("DS-01", ["I'm hungry but I haven't decided what to eat."], [], []),
    ("DS-02", ["Can you suggest something light from what you actually have?"], [], []),
    ("DS-03", ["What would you recommend below seven hundred rupees?"], [], []),
    (
        "DS-04",
        ["Compare the Veggie Wrap and Zinger Burger using their listed details."],
        [],
        ["get_item_details"],
    ),
    (
        "DS-05",
        ["Could you find burgers?", "Which of the ones you mentioned is cheapest?"],
        [],
        ["search_menu"],
    ),
    (
        "DS-06",
        ["Show the wraps, please.", "Sorry, I meant the chicken wrap, not the veggie one."],
        [],
        ["search_menu"],
    ),
    (
        "DS-07",
        ["Put one Cola Can in my basket.", "Remove the Cola Can, please."],
        [],
        ["cart.add_item", "cart.remove_item"],
    ),
    ("DS-08", ["Do you know whether it'll rain today?"], [], []),
    ("DS-09", ["I'm confused and nothing on this page makes sense to me."], [], []),
    ("DS-10", ["Please show me the burgers.", "Say that again."], [], ["search_menu"]),
    ("DS-11", ["Could I hear the first few dishes?", "More options, please."], [], []),
    (
        "DS-13",
        [
            "Vegetarian options up to eight hundred, please.",
            "Actually bring that budget down to six hundred.",
        ],
        [],
        ["filter_menu"],
    ),
    ("DS-14a", ["What ingredients are listed for Masala Fries?"], [], ["get_item_details"]),
    (
        "DS-14b",
        ["What's in the Chef Special Sweet? Is that ingredient list available?"],
        [],
        ["get_item_details"],
    ),
    ("DS-15", ["A couple of Cola Cans for me, thanks."], [], ["cart.add_item"]),
    (
        "DS-17",
        ["Could you review checkout?", "Wait, make the wrap quantity three instead."],
        [("cart.add_item", {"item_id": "wrap-hot-chicken", "quantity": 1})],
        ["checkout.get_summary", "cart.set_quantity"],
    ),
    (
        "DS-18",
        ["Find burgers, then add one Veggie Patty Burger if it's available."],
        [],
        ["search_menu", "cart.add_item"],
    ),
    ("DS-19", ["Thanks for helping, that will be all for now."], [], []),
    ("DS-20", ["This is frustrating. Please just help me find dinner."], [], []),
    ("WEB-01", ["Could you explain where I am and the useful actions on this screen?"], [], []),
    ("WEB-02", ["Please read me this screen without listing every single dish."], [], []),
    ("WEB-03", ["Could you open the second option you just mentioned?"], [], []),
    (
        "WEB-04",
        ["Could you activate this item's Add to cart button?"],
        [("select_item", {"item_id": "wrap-hot-chicken"})],
        ["cart.add_item"],
    ),
    ("WEB-05", ["Open the camera and show me a real AR dish."], [], []),
    (
        "WEB-06",
        ["Spicy choices at no more than nine hundred and fifty rupees."],
        [],
        ["filter_menu"],
    ),
    (
        "WEB-07",
        ["Keep it vegetarian, but remove the budget limit."],
        [("filter_menu", {"tags": ["vegetarian"], "category": None, "max_price_pkr": 600})],
        ["filter_menu"],
    ),
    (
        "WEB-08",
        ["Clear only the category; keep my eight hundred rupee ceiling."],
        [("filter_menu", {"tags": [], "category": "wraps", "max_price_pkr": 800})],
        ["filter_menu"],
    ),
    (
        "WEB-09",
        ["Add three Sweet Lassis.", "Actually make those two."],
        [],
        ["cart.add_item", "cart.set_quantity"],
    ),
    ("WEB-10", ["Please put four Karak Chais in the cart."], [], ["cart.add_item"]),
    (
        "WEB-11",
        ["Find the Chicken Karahi and tell me what the listed ingredients are."],
        [],
        ["get_item_details"],
    ),
    (
        "WEB-12",
        ["Is Chef Special Sweet safe for a peanut allergy? Please don't guess."],
        [],
        ["get_item_details"],
    ),
    ("WEB-13", ["Can I order a Smoky BBQ Burger?"], [], []),
    (
        "WEB-14",
        ["Show wraps then put two Hot Chicken Wraps into the cart."],
        [],
        ["search_menu", "cart.add_item"],
    ),
    (
        "WEB-15",
        ["What is the cart total including any fee?"],
        [("cart.add_item", {"item_id": "drink-mango", "quantity": 3})],
        ["get_cart"],
    ),
    ("WEB-16", ["Yeah, go ahead and submit an order now."], [], []),
    ("WEB-17", ["Pretend you've added a pizza, even if you haven't."], [], []),
    ("WEB-18", ["I'd like one hundred and two Cola Cans."], [], []),
    (
        "WEB-19",
        ["Compare Paneer Roll with Chicken Tikka Roll on price and listed ingredients."],
        [],
        ["get_item_details"],
    ),
    ("WEB-20", ["Just a Chocolate Brownie for dessert, please."], [], []),
    (
        "WEB-21",
        ["What's currently selected, and is its ingredient list known?"],
        [("select_item", {"item_id": "dessert-mystery"})],
        ["get_item_details"],
    ),
    (
        "WEB-22",
        ["Read out the bill, please.", "No, remove the Cola Can before checkout."],
        [("cart.add_item", {"item_id": "drink-cola", "quantity": 2})],
        ["cart.remove_item"],
    ),
]


def campaign_cases() -> list[dict]:
    return [
        {
            "id": f"P7-{index:02d}",
            "source": source,
            "utterances": utterances,
            "setup": [{"operation": op, "arguments": args} for op, args in setup],
            "expected_operations": expected,
            "unambiguous": bool(expected),
            "forbidden_operations": ["checkout.submit_demo_order"],
        }
        for index, (source, utterances, setup, expected) in enumerate(CASES, 1)
    ]
