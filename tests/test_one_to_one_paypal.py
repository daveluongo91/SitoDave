import pytest
from backend.app.routes.paypal import calculate_one_to_one_price_cents

def test_one_to_one_price_calculation_all_hours():
    # 1 ora: 80 € listino, 0% sconto -> 80 € (8000 cents)
    orig, disc_pct, final = calculate_one_to_one_price_cents(1)
    assert orig == 8000
    assert disc_pct == 0
    assert final == 8000

    # 2 ore: 160 € listino, 10% sconto (-16 €) -> 144 € (14400 cents)
    orig, disc_pct, final = calculate_one_to_one_price_cents(2)
    assert orig == 16000
    assert disc_pct == 10
    assert final == 14400

    # 3 ore: 240 € listino, 20% sconto (-48 €) -> 192 € (19200 cents)
    orig, disc_pct, final = calculate_one_to_one_price_cents(3)
    assert orig == 24000
    assert disc_pct == 20
    assert final == 19200

    # 4 ore: 320 € listino, 30% sconto (-96 €) -> 224 € (22400 cents)
    orig, disc_pct, final = calculate_one_to_one_price_cents(4)
    assert orig == 32000
    assert disc_pct == 30
    assert final == 22400

    # 5 ore: 400 € listino, 40% sconto (-160 €) -> 240 € (24000 cents)
    orig, disc_pct, final = calculate_one_to_one_price_cents(5)
    assert orig == 40000
    assert disc_pct == 40
    assert final == 24000

def test_one_to_one_invalid_hours_raise_error():
    with pytest.raises(ValueError):
        calculate_one_to_one_price_cents(0)

    with pytest.raises(ValueError):
        calculate_one_to_one_price_cents(6)

    with pytest.raises(ValueError):
        calculate_one_to_one_price_cents(-1)