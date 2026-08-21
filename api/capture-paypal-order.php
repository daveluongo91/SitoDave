<?php
declare(strict_types=1);

require __DIR__.'/common.php';

try {
    $body = post_json();
    $id = text($body['orderId'] ?? '', 64);
    $existing = store(fn(array &$data) => $data['bookings'][$id] ?? null);

    if (!$existing) {
        out(['status' => 'error', 'message' => 'Prenotazione non trovata'], 404);
    }
    if (($existing['status'] ?? '') === 'paid') {
        out([
            'status' => 'already_paid',
            'bookingId' => $id,
            'extraDay' => (bool)($existing['extraDay'] ?? false),
        ]);
    }

    $paypalCapture = paypal('POST', '/v2/checkout/orders/'.rawurlencode($id).'/capture');
    $capture = $paypalCapture['purchase_units'][0]['payments']['captures'][0] ?? [];
    if (($capture['status'] ?? '') !== 'COMPLETED' || ($capture['amount']['currency_code'] ?? '') !== 'EUR') {
        throw new RuntimeException();
    }

    $booking = paid($id, (string)$capture['id'], (string)$capture['amount']['value']);
    $extraDayLabel = !empty($booking['extraDay'])
        ? "Sì, da venerdì 9 ottobre (+€100)"
        : 'No, da sabato 10 ottobre';
    $total = (string)($booking['totalAmount'] ?? $booking['amount']);

    mail_site(
        $booking['email'],
        'Prenotazione confermata — Workshop Friuli 2026',
        "Ciao {$booking['first']},\n\n".
        'Pagamento confermato per '.WORKSHOP_NAME.".\n".
        "Formula: {$booking['formula']}\n".
        "Opzione venerdì: {$extraDayLabel}\n".
        "Importo pagato: €{$booking['amount']}\n".
        "Totale workshop: €{$total}\n\n".
        "Davide Luongo\ninfo@davideluongo.it"
    );

    out([
        'status' => 'paid',
        'bookingId' => $id,
        'captureId' => $capture['id'],
        'extraDay' => (bool)($booking['extraDay'] ?? false),
        'totalAmount' => $total,
    ]);
} catch (Throwable) {
    out(['status' => 'error', 'message' => 'Conferma pagamento non riuscita. Contatta Davide.'], 500);
}
