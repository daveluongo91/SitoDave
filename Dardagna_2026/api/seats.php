<?php
declare(strict_types=1);

require __DIR__.'/common.php';

try {
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'GET') {
        out(['status' => 'error', 'message' => 'Metodo non consentito'], 405);
    }
    $available = store(fn(array &$data) => max(0, (int)($data['availableSeats'] ?? 0)));
    out([
        'availableSeats' => $available,
        'status' => $available > 0 ? 'active' : 'soldout',
    ]);
} catch (Throwable) {
    out(['status' => 'error', 'message' => 'Disponibilità non raggiungibile'], 500);
}
