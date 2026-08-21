<?php
declare(strict_types=1);
require __DIR__.'/common.php';
headers_secure();
header('Content-Type: application/javascript; charset=utf-8');
$u = 'https://www.paypal.com/sdk/js?client-id=' . rawurlencode(cfg('PAYPAL_LIVE_CLIENT_ID'))
   . '&currency=EUR&locale=it_IT&intent=capture&enable-funding=paylater';
echo '(() => { const s = document.createElement("script"); s.src = ' . json_encode($u) . '; document.head.appendChild(s); })();';

