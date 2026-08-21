<?php
declare(strict_types=1);

require __DIR__.'/common.php';

try {
    $body = post_json();
    $name = text($body['name'] ?? '', 120);
    $email = email($body['email'] ?? '');
    $phone = text($body['phone'] ?? '', 40);
    $subjectRaw = text($body['subject'] ?? 'Informazioni Generali', 160);
    $message = text($body['message'] ?? '', 3000);

    if ($name === '' || $email === '' || $message === '') {
        out(['status' => 'error', 'message' => 'Tutti i campi obbligatori devono essere compilati'], 400);
    }

    $tagSubject = str_starts_with($subjectRaw, 'Richiesta info per') ? $subjectRaw : "Richiesta info per {$subjectRaw}";
    $mailSubject = "[RICHIESTA INFO] {$tagSubject}";

    $content = "=== NUOVA RICHIESTA DI INFORMAZIONI DAL SITO ===\n\n";
    $content .= "Nome: {$name}\n";
    $content .= "Email: {$email}\n";
    $content .= "Telefono: {$phone}\n";
    $content .= "Tag/Oggetto: {$tagSubject}\n\n";
    $content .= "--- MESSAGGIO ---\n{$message}\n\n";
    $content .= "Inviato il: " . date('d/m/Y H:i:s') . "\n";
    $content .= "IP: " . ($_SERVER['REMOTE_ADDR'] ?? 'n/a') . "\n";

    $dest = 'info@davideluongo.it';
    $sent = mail_site($dest, $mailSubject, $content);

    if (!$sent) {
        throw new RuntimeException("Errore invio mail SMTP");
    }

    out([
        'status' => 'ok',
        'message' => 'Messaggio inviato con successo a info@davideluongo.it',
        'tag' => $tagSubject
    ]);
} catch (Throwable $e) {
    out([
        'status' => 'error',
        'message' => 'Invio non riuscito. Scrivi direttamente a info@davideluongo.it'
    ], 500);
}