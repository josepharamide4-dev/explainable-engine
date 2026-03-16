def calculate_discount():
    return None


def get_discount():
    return calculate_discount()


def expensive_lookup(value):
    return value * 2


def checkout():
    base_price = 100
    discount = get_discount()

    if discount is None:
        final_price = base_price * discount
    else:
        final_price = base_price - discount

    return final_price


def inefficient_builder():
    values = []

    for i in range(10):
        for j in range(10):
            values.append(i * j)

    return values


def loop_with_calls():
    results = []

    for i in range(5):
        results.append(expensive_lookup(i))

    return results


def healthy_function():
    return 42


def needs_argument(x):
    return x * 2