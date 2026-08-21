<?php
declare(strict_types=1);

const WORKSHOP_ID='dardagna-2026';
const WORKSHOP_NAME='Workshop Dardagna: Cascate dell’Appennino';
const DEPOSIT_CENTS=5000;
const FULL_PRICE_CENTS=35000;
const PUBLIC_PATH='/Dardagna_2026/';

function config():array{static $c;if(isset($c))return $c;$p=dirname(__DIR__).'/private/production.env';if(!is_file($p))throw new RuntimeException('Config mancante');$c=[];foreach(file($p,FILE_IGNORE_NEW_LINES|FILE_SKIP_EMPTY_LINES)?:[] as $l){$l=trim($l);if($l===''||$l[0]==='#'||!str_contains($l,'='))continue;[$k,$v]=explode('=',$l,2);$c[trim($k)]=trim($v);}return $c;}
function cfg(string $k):string{$v=config()[$k]??'';if($v==='')throw new RuntimeException('Config incompleta');return $v;}
function headers_secure():void{header('X-Content-Type-Options: nosniff');header('X-Frame-Options: SAMEORIGIN');header('Referrer-Policy: strict-origin-when-cross-origin');header('Cache-Control: no-store');}
function out(array $p,int $s=200):never{headers_secure();http_response_code($s);header('Content-Type: application/json; charset=utf-8');echo json_encode($p,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);exit;}
function post_json():array{if(($_SERVER['REQUEST_METHOD']??'')!=='POST')out(['status'=>'error','message'=>'Metodo non consentito'],405);$o=$_SERVER['HTTP_ORIGIN']??'';if($o!==''&&!in_array($o,['https://www.davideluongo.it','https://davideluongo.it'],true))out(['status'=>'error','message'=>'Origine non consentita'],403);$r=file_get_contents('php://input');if($r===false||strlen($r)>20000)out(['status'=>'error','message'=>'Richiesta non valida'],400);$b=json_decode($r,true);if(!is_array($b))out(['status'=>'error','message'=>'JSON non valido'],400);return $b;}
function text(mixed $v,int $n):string{return mb_substr(trim(preg_replace('/[\x00-\x1F\x7F]/u','',(string)$v)??''),0,$n);}
function email(mixed $v):string{$e=strtolower(trim((string)$v));if(!filter_var($e,FILTER_VALIDATE_EMAIL))out(['status'=>'error','message'=>'Email non valida'],400);return $e;}
function public_url():string{return rtrim(cfg('SITE_PUBLIC_URL'),'/').PUBLIC_PATH;}
function store(callable $fn):mixed{$p=dirname(__DIR__).'/private/data.json';$h=fopen($p,'c+');if(!$h||!flock($h,LOCK_EX))throw new RuntimeException('Archivio non disponibile');try{rewind($h);$d=json_decode(stream_get_contents($h)?:'',true);if(!is_array($d))$d=['availableSeats'=>8,'bookings'=>[],'subscribers'=>[]];$r=$fn($d);rewind($h);ftruncate($h,0);fwrite($h,json_encode($d,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES));fflush($h);return $r;}finally{flock($h,LOCK_UN);fclose($h);}}
function paypal(string $method,string $path,?array $payload=null):array{$auth=base64_encode(cfg('PAYPAL_LIVE_CLIENT_ID').':'.cfg('PAYPAL_LIVE_CLIENT_SECRET'));$t=curl_init('https://api-m.paypal.com/v1/oauth2/token');curl_setopt_array($t,[CURLOPT_POST=>true,CURLOPT_POSTFIELDS=>'grant_type=client_credentials',CURLOPT_RETURNTRANSFER=>true,CURLOPT_TIMEOUT=>20,CURLOPT_HTTPHEADER=>['Authorization: Basic '.$auth,'Content-Type: application/x-www-form-urlencoded']]);$tr=curl_exec($t);$ts=(int)curl_getinfo($t,CURLINFO_HTTP_CODE);curl_close($t);$tb=json_decode((string)$tr,true);if($ts!==200||empty($tb['access_token']))throw new RuntimeException('PayPal auth');$c=curl_init('https://api-m.paypal.com'.$path);$opts=[CURLOPT_CUSTOMREQUEST=>$method,CURLOPT_RETURNTRANSFER=>true,CURLOPT_TIMEOUT=>25,CURLOPT_HTTPHEADER=>['Authorization: Bearer '.$tb['access_token'],'Content-Type: application/json','PayPal-Request-Id: '.bin2hex(random_bytes(16))]];if($payload!==null)$opts[CURLOPT_POSTFIELDS]=json_encode($payload);curl_setopt_array($c,$opts);$raw=curl_exec($c);$status=(int)curl_getinfo($c,CURLINFO_HTTP_CODE);curl_close($c);$body=json_decode((string)$raw,true);if($status<200||$status>=300||!is_array($body))throw new RuntimeException('PayPal request');return $body;}
function smtp_read($s,array $ok):void{$r='';do{$l=fgets($s,515);if($l===false)throw new RuntimeException('SMTP');$r.=$l;}while(isset($l[3])&&$l[3]==='-');if(!in_array((int)substr($r,0,3),$ok,true))throw new RuntimeException('SMTP');}
function smtp_cmd($s,string $c,array $ok):void{fwrite($s,$c."\r\n");smtp_read($s,$ok);}
function mail_site(string $to,string $subject,string $body):bool{
    $from=cfg('SMTP_FROM');
    $encoded='=?UTF-8?B?'.base64_encode($subject).'?=';
    $headers="From: Davide Luongo <{$from}>\r\nMIME-Version: 1.0\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: 8bit";
    $s=@stream_socket_client('ssl://'.cfg('SMTP_HOST').':'.cfg('SMTP_PORT'),$e,$es,8,STREAM_CLIENT_CONNECT);
    if($s){
        try{
            stream_set_timeout($s,8);
            smtp_read($s,[220]);
            smtp_cmd($s,'EHLO davideluongo.it',[250]);
            smtp_cmd($s,'AUTH LOGIN',[334]);
            smtp_cmd($s,base64_encode(cfg('SMTP_USERNAME')),[334]);
            smtp_cmd($s,base64_encode(cfg('SMTP_PASSWORD')),[235]);
            smtp_cmd($s,'MAIL FROM:<'.$from.'>',[250]);
            smtp_cmd($s,'RCPT TO:<'.$to.'>',[250,251]);
            smtp_cmd($s,'DATA',[354]);
            $smtpHeaders="From: Davide Luongo <{$from}>\r\nTo: <{$to}>\r\nSubject: {$encoded}\r\nMIME-Version: 1.0\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: 8bit\r\n";
            $normalized=preg_replace('/\r?\n/',"\r\n",$body)??$body;
            $normalized=preg_replace('/(^|\r\n)\./','$1..',$normalized)??$normalized;
            fwrite($s,$smtpHeaders."\r\n".$normalized."\r\n.\r\n");
            smtp_read($s,[250]);
            smtp_cmd($s,'QUIT',[221]);
            return true;
        }catch(Throwable){
            // L'hosting puo bloccare o interrompere l'SMTP in uscita: usa il mailer locale.
        }finally{
            fclose($s);
        }
    }
    return @mail($to,$encoded,$body,$headers);
}
function alerts(array &$d):void{$n=(int)($d['availableSeats']??0);if(!in_array($n,[1,2],true))return;$f=$n===2?'notifiedTwo':'notifiedOne';foreach($d['subscribers'] as &$x){if(empty($x['active'])||!empty($x[$f]))continue;$label=$n===1?'1 solo posto':'soltanto 2 posti';$u=rtrim(public_url(),'/').'/api/unsubscribe.php?token='.rawurlencode($x['token']);$m="Ciao {$x['name']},\n\nPer ".WORKSHOP_NAME." restano {$label}.\n\nPrenota qui: ".public_url()."\n\nDisiscrizione: {$u}";if(mail_site($x['email'],"[DARDAGNA 2026] Restano {$label}",$m))$x[$f]=gmdate('c');}unset($x);}
function paid(string $order,string $capture,string $value):array{return store(function(array &$d)use($order,$capture,$value){if(empty($d['bookings'][$order]))throw new RuntimeException('Booking');$b=&$d['bookings'][$order];if(($b['status']??'')==='paid')return $b;if(!hash_equals($b['amount'],$value))throw new RuntimeException('Amount');$b['status']='paid';$b['captureId']=$capture;$b['paidAt']=gmdate('c');$d['availableSeats']=max(0,(int)$d['availableSeats']-1);alerts($d);return $b;});}
