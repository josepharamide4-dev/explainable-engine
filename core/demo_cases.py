def get_discount():
    return None


def checkout():
    base_price = 100
    discount = get_discount()

    if discount is None:
        final_price = base_price * discount
    else:
        final_price = base_price - discount

    return final_price


def checkout_context():
    return {
        "base_price": 100,
        "discount": None,
        "final_price": None,
    }


def checkout_related_functions():
    return [get_discount]


def _cases():
    return {
        "checkout": {
            "func": checkout,
            "variable_details": checkout_context(),
            "related_functions": checkout_related_functions(),
        }
    }


def get_demo_case(case_name: str):
    return _cases().get(case_name)


def list_demo_cases():
    return list(_cases().keys())