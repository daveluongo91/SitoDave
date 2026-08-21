<?php
declare(strict_types=1);

require __DIR__.'/common.php';

try {
    $body = post_json();
    $workshopId = (string)($body['workshopId'] ?? '');
    
    $first = text($body['firstName'] ?? '', 80);
    $last = text($body['lastName'] ?? '', 80);
    $phone = text($body['phone'] ?? '', 40);
    $email = email($body['email'] ?? '');
    if ($first === '' || $last === '') {
        out(['status' => 'error', 'message' => 'Nome obbligatorio'], 400);
    }

    if ($workshopId === 'one-to-one' || ($body['formula'] ?? '') === 'one-to-one') {
        $hours = (int)($body['hours'] ?? $body['participants'] ?? 1);
        if ($hours < 1 || $hours > 5) {
            out(['status' => 'error', 'message' => 'Le ore devono essere comprese tra 1 e 5'], 400);
        }
        $discounts = [1 => 0, 2 => 10, 3 => 20, 4 => 30, 5 => 40];
        $discountPct = $discounts[$hours];
        $listCents = 8000 * $hours;
        $cents = (int)($listCents * (100 - $discountPct) / 100);
        $amount = number_format($cents / 100, 2, '.', '');
        $totalAmount = $amount;
        $formula = 'one-to-one';
        $extraDay = false;
        $extraDayAmount = '0.00';
        $description = "Corso One to One ({$hours} " . ($hours === 1 ? 'ora' : 'ore') . ")";

        $paypalOrder = paypal('POST', '/v2/checkout/orders', [
            'intent' => 'CAPTURE',
            'purchase_units' => [[
                'reference_id' => 'one-to-one',
                'description' => $description,
                'amount' => ['currency_code' => 'EUR', 'value' => $amount],
                'custom_id' => "one-to-one|hours={$hours}|{$email}",
            ]],
            'application_context' => [
                'brand_name' => 'Davide Luongo Photography',
                'locale' => 'it-IT',
                'user_action' => 'PAY_NOW',
            ],
        ]);

        $id = (string)$paypalOrder['id'];
        store(function (array &$data) use ($id, $first, $last, $phone, $email, $formula, $amount, $totalAmount, $hours): void {
            $data['bookings'][$id] = compact(
                'id',
                'first',
                'last',
                'phone',
                'email',
                'formula',
                'amount',
                'totalAmount',
                'hours'
            ) + ['status' => 'pending', 'workshopId' => 'one-to-one', 'createdAt' => gmdate('c')];
        });

        out([
            'status' => 'success',
            'orderId' => $id,
            'amountDue' => $amount,
            'totalAmount' => $totalAmount,
            'formula' => $formula,
            'hours' => $hours,
        ], 201);
    }

    // Workshop standard
    if ($workshopId !== WORKSHOP_ID) {
        out(['status' => 'error', 'message' => 'Workshop non valido'], 400);
    }

    $formula = ($body['formula'] ?? '') === 'saldo' ? 'saldo' : 'caparra';
    $extraDay = ($body['extraDay'] ?? false) === true;
    $totalCents = FULL_PRICE_CENTS + ($extraDay ? EXTRA_DAY_CENTS : 0);
    $cents = $formula === 'saldo' ? $totalCents : DEPOSIT_CENTS;
    $amount = number_format($cents / 100, 2, '.', '');
    $totalAmount = number_format($totalCents / 100, 2, '.', '');
    $extraDayAmount = number_format(($extraDay ? EXTRA_DAY_CENTS : 0) / 100, 2, '.', '');

    if (store(fn(array &$data) => (int)$data['availableSeats']) < 1) {
        out(['status' => 'error', 'message' => 'Workshop esaurito'], 409);
    }

    $description = WORKSHOP_NAME.($extraDay ? ' + venerdì 9 ottobre' : '');
    $paypalOrder = paypal('POST', '/v2/checkout/orders', [
        'intent' => 'CAPTURE',
        'purchase_units' => [[
            'reference_id' => WORKSHOP_ID,
            'description' => $description,
            'amount' => ['currency_code' => 'EUR', 'value' => $amount],
        ]],
        'application_context' => [
            'brand_name' => 'Davide Luongo Photography',
            'locale' => 'it-IT',
            'user_action' => 'PAY_NOW',
        ],
    ]);

    $id = (string)$paypalOrder['id'];
    store(function (array &$data) use ($id, $first, $last, $phone, $email, $formula, $amount, $totalAmount, $extraDay, $extraDayAmount): void {
        $data['bookings'][$id] = compact(
            'id',
            'first',
            'last',
            'phone',
            'email',
            'formula',
            'amount',
            'totalAmount',
            'extraDay',
            'extraDayAmount'
        ) + ['status' => 'pending', 'createdAt' => gmdate('c')];
    });

    out([
        'status' => 'success',
        'orderId' => $id,
        'amountDue' => $amount,
        'totalAmount' => $totalAmount,
        'formula' => $formula,
        'extraDay' => $extraDay,
        'extraDayAmount' => $extraDayAmount,
    ], 201);
} catch (Throwable) {
    out(['status' => 'error', 'message' => 'Impossibile preparare il pagamento'], 500);
}